"""Build a deterministic evidence report for the manuscript alignment pass."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from audit_data_assets import main as audit_assets

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "docs" / "publication_evidence_report.json"


def main():
    assets = []
    # Reuse the inventory logic without scraping or inventing provenance.
    import audit_data_assets as audit
    for path in audit.ASSETS:
        item = {"path": str(path.relative_to(ROOT)), "exists": path.exists()}
        if path.exists():
            item["bytes"] = path.stat().st_size
            item["sha256"] = audit.sha256(path)
        assets.append(item)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {"country": "Nigeria", "states_including_fct": 37, "lgas_boundary_features": 774},
        "evidence_policy": {
            "correlation": "exploratory association only",
            "lag_unit": "calendar months",
            "causation_claim_supported": False,
            "prospective_forecast_validation_present": False,
            "ncdc_sormas_live_integration_verified": False,
        },
        "assets": assets,
        "claim_status": [
            {"claim": "46,146 facility records are present in the local FMOH asset", "status": "verified_inventory"},
            {"claim": "774 national LGA boundary features are present", "status": "verified_inventory"},
            {"claim": "Pearson correlation is statistically significant", "status": "not_supported_by_this_report"},
            {"claim": "Flooding provides a validated 30-day prediction window", "status": "not_supported_by_this_report"},
            {"claim": "Cross River pilot validates the national system", "status": "not_supported; sentinel_only"},
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
