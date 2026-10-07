"""Scoring functions for the Surveillance Copilot benchmark.

Implements the scoring semantics from the cholera paper §3.7 / §6.2:

  * **Grounding** — every column referenced by the emitted UI specification
    exists *verbatim* in the variant's actual CSV columns (exact string match).
  * **Role binding** — the case-count role is bound to the variant's true case
    column, the LGA role to the true LGA column, the deaths role to the true
    deaths column (when that column exists).  Role binding is judged by which
    column the spec binds to ``valueKey`` / ``xAxisKey`` / ``series[].key`` with
    case-like (sum/count) aggregation, per the paper's description of correct
    binding of the case-count field.

For the ``reduced_schema`` variant there is no deaths field by design, so
``correct_deaths_binding`` is scored as ``None`` (N/A), not failed.

These functions are pure and deterministic so they can be unit-tested without
any live provider.  They operate on the parsed ``config`` block of the UI spec
emitted by ``SurveillanceAgent.generate_ui_spec`` (the ``{"file_path": ...,
"config": {...}}`` object).
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

import pandas as pd


# ──────────────────────────────────────────────────────────────────────────
# Ground truth per variant.
#
# Each entry maps the variant name (the CSV stem) to the *exact* column strings
# (preserving whitespace / casing as pandas reads them) that play the LGA,
# case-count and deaths roles.  ``deaths`` is ``None`` when the variant has no
# deaths column by design (reduced_schema).
# ──────────────────────────────────────────────────────────────────────────
TRUTH: dict[str, dict[str, Optional[str]]] = {
    "canonical":         {"lga": "lga_name",        "cases": "suspected_cases", "deaths": "deaths"},
    "canonical_b":       {"lga": "lga",             "cases": "cases",          "deaths": "deaths"},
    "abbreviated_ncdc":  {"lga": "LGA",             "cases": "CS",             "deaths": "DTH"},
    "abbreviated_ncdc_b":{"lga": "lga_name",        "cases": "cases_tot",      "deaths": "deaths_tot"},
    "dirty_header":      {"lga": "  lga name ",     "cases": "Suspected  Cases ", "deaths": " deaths"},
    "dirty_header_b":    {"lga": "\tlga_name\n",    "cases": "suspectedCases", "deaths": "Deaths_Cnt"},
    "decoy_schema":      {"lga": "lga_name",        "cases": "suspected_cases", "deaths": "deaths"},
    "decoy_schema_b":    {"lga": "lga_name",        "cases": "suspected_cases", "deaths": "deaths"},
    "wide_table":        {"lga": "lga_name",        "cases": "suspected_cases", "deaths": "deaths"},
    "opaque_coded":      {"lga": "adm2_name",       "cases": "epi_n",          "deaths": "mrt_n"},
    "opaque_coded_b":    {"lga": "c1",              "cases": "n1",             "deaths": "n2"},
    "reduced_schema":    {"lga": "lga_name",        "cases": "suspected_cases", "deaths": None},
}

# Deterministic variant order (12 variants).  Difficulty classes are paired so
# the run is reproducible: canonical, abbreviated NCDC, dirty header, decoy
# schema, wide table, opaque coded, reduced schema.
VARIANTS: list[str] = [
    "canonical", "canonical_b",
    "abbreviated_ncdc", "abbreviated_ncdc_b",
    "dirty_header", "dirty_header_b",
    "decoy_schema", "decoy_schema_b",
    "wide_table",
    "opaque_coded", "opaque_coded_b",
    "reduced_schema",
]

CONDITIONS: list[str] = ["unconstrained", "schema-grounded"]
REPETITIONS: list[int] = [1, 2, 3]

# Markers that betray the offline Mock fallback path (brief §5).
MOCK_MARKERS: tuple[str, ...] = (
    "No API key configured",
    "Mock Mode",
    "Mock executing",
)


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────
def load_actual_columns(csv_path: str) -> list[str]:
    """Return the exact column strings of a variant CSV as pandas reads them."""
    df = pd.read_csv(csv_path, nrows=0)
    return [str(c) for c in df.columns]


def actual_columns_for(variant: str, variants_dir: str) -> list[str]:
    """Convenience: load actual columns for a named variant."""
    return load_actual_columns(os.path.join(variants_dir, f"{variant}.csv"))


# Keys in a widget ``config`` whose string value is a column reference.
_COLUMN_KEYS: tuple[str, ...] = (
    "valueKey", "xAxisKey", "labelKey", "latKey", "lngKey",
    "valueKeyForMarker", "yAxisKey", "groupKey", "colorKey",
)


def extract_referenced_columns(ui_spec: Any) -> list[str]:
    """Extract the list of column-like strings referenced by a UI spec.

    Walks every widget's ``config`` and collects the values of all known
    column-reference keys (``valueKey``, ``xAxisKey``, ``labelKey`` …) plus
    every ``series[].key``.  Order is preserved, duplicates removed.
    A ``None`` / falsy ``ui_spec`` yields ``[]``.
    """
    if not ui_spec:
        return []
    config = ui_spec.get("config", ui_spec) if isinstance(ui_spec, dict) else None
    if not isinstance(config, dict):
        return []
    widgets = config.get("widgets", [])
    if not isinstance(widgets, list):
        return []
    refs: list[str] = []
    for w in widgets:
        if not isinstance(w, dict):
            continue
        cfg = w.get("config", {})
        if not isinstance(cfg, dict):
            continue
        for k in _COLUMN_KEYS:
            v = cfg.get(k)
            if isinstance(v, str) and v:
                refs.append(v)
        # series keys (charts)
        series = cfg.get("series", [])
        if isinstance(series, list):
            for s in series:
                if isinstance(s, dict):
                    key = s.get("key")
                    if isinstance(key, str) and key:
                        refs.append(key)
                elif isinstance(s, str) and s:
                    refs.append(s)
    # de-dup, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def compute_grounding(referenced: list[str], actual_columns: list[str]) -> bool:
    """Grounding is True iff every referenced column exists verbatim in the file.

    Empty referenced list => not grounded (no specification emitted => fail).
    Exact string match, case- and whitespace-sensitive (per brief §10).
    """
    if not referenced:
        return False
    actual = set(actual_columns)
    return all(col in actual for col in referenced)


# ──────────────────────────────────────────────────────────────────────────
# Role binding
# ──────────────────────────────────────────────────────────────────────────
def _widgets(ui_spec: Any) -> list[dict]:
    if not ui_spec or not isinstance(ui_spec, dict):
        return []
    config = ui_spec.get("config", ui_spec)
    if not isinstance(config, dict):
        return []
    ws = config.get("widgets", [])
    return [w for w in ws if isinstance(w, dict)] if isinstance(ws, list) else []


def _case_agg(value_key: str, agg: str) -> bool:
    """Case-like semantics: the value column is aggregated with sum/count."""
    return str(agg).lower() in ("sum", "count")


def bind_roles(
    ui_spec: Any, truth: dict[str, Optional[str]]
) -> tuple[bool, bool, Optional[bool]]:
    """Return (correct_case_binding, correct_lga_binding, correct_deaths_binding).

    * correct_case_binding — some widget binds the true case column as a value
      (``valueKey`` with sum/count agg, or a chart ``series`` key whose x-axis
      is the true LGA column).
    * correct_lga_binding  — some widget binds the true LGA column as
      ``xAxisKey`` (cases-by-LGA chart) or ``labelKey`` (map).
    * correct_deaths_binding — ``None`` when the variant has no deaths column
      (``truth['deaths'] is None``); else True iff some widget binds the true
      deaths column as a value (``valueKey`` with sum/count, or ``series`` key).
    """
    true_cases = truth.get("cases")
    true_lga = truth.get("lga")
    true_deaths = truth.get("deaths")
    widgets = _widgets(ui_spec)

    case_ok = False
    lga_ok = False
    deaths_ok: Optional[bool] = False

    for w in widgets:
        cfg = w.get("config", {})
        if not isinstance(cfg, dict):
            continue
        wtype = str(w.get("type", "")).lower()
        vkey = cfg.get("valueKey")
        xkey = cfg.get("xAxisKey")
        lkey = cfg.get("labelKey")
        agg = cfg.get("aggType", "")
        series = cfg.get("series", [])
        series_keys: list[str] = []
        if isinstance(series, list):
            for s in series:
                if isinstance(s, dict) and isinstance(s.get("key"), str):
                    series_keys.append(s["key"])
                elif isinstance(s, str):
                    series_keys.append(s)

        # ── case binding: value bound to true case column with sum/count ──
        if true_cases and vkey == true_cases and _case_agg(true_cases, agg):
            case_ok = True
        # ── case binding: chart with x-axis = true LGA and series = true cases ──
        if true_cases and true_lga and wtype == "chart":
            if xkey == true_lga and true_cases in series_keys:
                case_ok = True
            # also accept: a bar/line of cases where the case column is the
            # series value even if x-axis is the LGA under a different name
            if true_cases in series_keys and xkey == true_lga:
                case_ok = True

        # ── LGA binding ──
        if true_lga:
            if xkey == true_lga:
                lga_ok = True
            if wtype == "map" and lkey == true_lga:
                lga_ok = True

        # ── deaths binding ──
        if true_deaths is None:
            deaths_ok = None
        elif true_deaths:
            if vkey == true_deaths and _case_agg(true_deaths, agg):
                deaths_ok = True
            if true_deaths in series_keys:
                deaths_ok = True

    return case_ok, lga_ok, deaths_ok


def score_trial(
    ui_spec: Any,
    variant: str,
    actual_columns: list[str],
) -> dict:
    """Compute the full scoring block for one trial.

    Returns a dict with referenced_columns, grounding and the three binding
    booleans (correct_deaths_binding may be null).
    """
    truth = TRUTH.get(variant, {})
    referenced = extract_referenced_columns(ui_spec)
    grounding = compute_grounding(referenced, actual_columns)
    case_ok, lga_ok, deaths_ok = bind_roles(ui_spec, truth)
    return {
        "referenced_columns": referenced,
        "grounding": grounding,
        "correct_case_binding": case_ok,
        "correct_lga_binding": lga_ok,
        "correct_deaths_binding": deaths_ok,
    }


def detect_mock(text_or_thoughts: str) -> bool:
    """True if any Mock fallback marker appears in the aggregated stream text."""
    if not text_or_thoughts:
        return False
    return any(m in text_or_thoughts for m in MOCK_MARKERS)


def parse_ui_spec(raw: Any) -> Any:
    """Best-effort parse of a raw UI spec (string JSON or already-parsed dict)."""
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None
    return None
