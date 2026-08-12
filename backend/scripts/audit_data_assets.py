"""Emit a deterministic, provenance-aware inventory of local study assets."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = [
    ROOT / "data/cholera_real/nigeria_cholera_2020_2025.csv",
    ROOT / "data/external_real/fmoh_nigeriahealthfacilities.csv.csv",
    ROOT / "data/external_real/fmoh_nigeriahealthfacilities.json.json",
    ROOT / "data/groundsource_2026.parquet",
    ROOT / "data/boundaries/nigeria_lgas_774.geojson",
    ROOT / "data/boundaries/nigeria_states.geojson",
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def csv_summary(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    out = {"rows": len(rows), "columns": reader.fieldnames or []}
    for key in ("State", "state_name", "LGA", "Lga", "lga_name", "Year", "Month"):
        if key in out["columns"]:
            vals = {r.get(key, "").strip() for r in rows if r.get(key, "").strip()}
            out[f"unique_{key}"] = len(vals)
    return out

def main() -> None:
    result = {"root": str(ROOT), "assets": []}
    for path in ASSETS:
        item = {"path": str(path.relative_to(ROOT)), "exists": path.exists()}
        if path.exists():
            item["bytes"] = path.stat().st_size
            item["sha256"] = sha256(path)
            if path.suffix.lower() == ".csv":
                item["summary"] = csv_summary(path)
            elif path.suffix.lower() in {".json", ".geojson"}:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    item["summary"] = {
                        "type": data.get("type") if isinstance(data, dict) else type(data).__name__,
                        "features": len(data.get("features", [])) if isinstance(data, dict) else None,
                        "totalFeatures": data.get("totalFeatures") if isinstance(data, dict) else None,
                    }
                except Exception as exc:
                    item["error"] = f"JSON parse failed: {exc}"
            elif path.suffix.lower() == ".parquet":
                try:
                    import pyarrow.parquet as pq
                    pf = pq.ParquetFile(path)
                    item["summary"] = {"rows": pf.metadata.num_rows, "columns": pf.schema.names}
                except Exception as exc:
                    item["error"] = f"Parquet inspection failed: {exc}"
        result["assets"].append(item)
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
