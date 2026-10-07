"""Nigerian state name normalisation and the adm1 boundary index.

The verified NCDC dataset spells some states differently from the CGAZ/OCHA
boundary file (`data/boundaries/nigeria_states.geojson`) — most notably "FCT"
vs "Federal Capital Territory", and the "Nasarawa"/"Nassarawa" pair. Everything
that needs to join the two sources goes through `canonical_state()` here so the
normalisation lives in exactly one place.

The boundary index is parsed once and cached; the raw file is served straight
from disk by the /api/states/boundaries endpoint (see routers/state_cholera.py).
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

BOUNDARIES_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "boundaries" / "nigeria_states.geojson"
)

#: Normalised spelling variants -> the adm1_name used in the boundary file.
#: Keys are already run through `_key()`.
_ALIASES: Dict[str, str] = {
    "FCT": "Federal Capital Territory",
    "FCTABUJA": "Federal Capital Territory",
    "ABUJA": "Federal Capital Territory",
    "ABUJAFCT": "Federal Capital Territory",
    "FEDERALCAPITALTERRITORYABUJA": "Federal Capital Territory",
    "NASSARAWA": "Nasarawa",
    "AKWAIBOM": "Akwa Ibom",
    "CROSSRIVERSTATE": "Cross River",
    "ZAMFARA": "Zamfara",
}


def _key(name: str) -> str:
    """Fold a state name to a comparison key: upper case, letters/digits only."""
    return re.sub(r"[^A-Z0-9]", "", (name or "").upper())


@lru_cache(maxsize=1)
def _boundary_index() -> Dict[str, Dict[str, object]]:
    """key -> {adm1_name, adm1_pcode, center_lat, center_lon}, parsed once."""
    index: Dict[str, Dict[str, object]] = {}
    try:
        with open(BOUNDARIES_PATH, encoding="utf-8") as fh:
            geojson = json.load(fh)
    except (OSError, ValueError):
        return index

    for feature in geojson.get("features", []):
        props = feature.get("properties") or {}
        name = props.get("adm1_name")
        if not name:
            continue
        index[_key(name)] = {
            "adm1_name": name,
            "adm1_pcode": props.get("adm1_pcode"),
            "center_lat": props.get("center_lat"),
            "center_lon": props.get("center_lon"),
        }
    return index


def canonical_state(name: str) -> Optional[str]:
    """The boundary-file spelling of `name`, or None if it is not a known state."""
    key = _key(name)
    if not key:
        return None
    index = _boundary_index()
    if key in index:
        return str(index[key]["adm1_name"])
    alias = _ALIASES.get(key)
    if alias and _key(alias) in index:
        return alias
    # Boundary file unavailable (e.g. trimmed deployment): fall back to the alias
    # table so name normalisation still behaves sensibly.
    return alias


def state_boundary_meta(name: str) -> Dict[str, object]:
    """adm1 metadata for `name`; empty-ish dict when the state cannot be matched."""
    canonical = canonical_state(name)
    if canonical is None:
        return {"adm1_name": None, "adm1_pcode": None, "center_lat": None, "center_lon": None}
    return dict(
        _boundary_index().get(
            _key(canonical),
            {"adm1_name": canonical, "adm1_pcode": None, "center_lat": None, "center_lon": None},
        )
    )


def boundaries_available() -> bool:
    """True when the adm1 boundary file is present on disk."""
    return BOUNDARIES_PATH.is_file()
