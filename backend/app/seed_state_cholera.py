"""Seed state_cholera_records from the verified v2 dataset.

Loads final_state_cholera_dataset_v2.csv (1,233 rows: 1,211 original + 22
recovered early-2021 bare-CFR rows; monotonic_ok flag). Wipes nothing here —
the fabricated nationwide LGA case_reports are cleared separately.

report_date is the Monday (ISO week start) of the record's epi week.
"""
import csv
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from app.database import SessionLocal
from app.models import StateCholeraRecord

logger = logging.getLogger(__name__)

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "data" / "cholera_real" / "final_state_cholera_dataset_v2.csv"


def epi_week_start(year: int, week: int) -> date:
    """Monday of ISO epi week `week` of `year` (ISO 8601 convention)."""
    return date.fromisocalendar(year, week, 1)


def _safe_int(v):
    try:
        return int(float(str(v).strip()))
    except (ValueError, TypeError):
        return None


def _safe_float(v):
    try:
        return float(str(v).strip())
    except (ValueError, TypeError):
        return None


def seed_state_cholera(csv_path=None, db=None):
    csv_path = Path(csv_path) if csv_path else DEFAULT_CSV
    own = db is None
    db = db or SessionLocal()
    inserted = updated = 0
    try:
        db.query(StateCholeraRecord).delete()
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    year = int(row["Year"])
                    week = int(row["Epi_Week"])
                except (ValueError, KeyError, TypeError):
                    continue
                rec = StateCholeraRecord(
                    state=row["State"].strip(),
                    year=year,
                    epi_week=week,
                    report_date=epi_week_start(year, week),
                    month=row.get("Month", "").strip() or None,
                    suspected_cases=_safe_int(row.get("Suspected_Cases")),
                    deaths=_safe_int(row.get("Deaths")),
                    cfr=_safe_float(row.get("CFR")),
                    confidence=row.get("Confidence", "").strip() or None,
                    monotonic_ok=str(row.get("monotonic_ok", "True")).strip().lower() != "false",
                    extraction_method=row.get("Extraction_Method", "").strip() or None,
                    source_url=row.get("Source_URL", "").strip() or None,
                )
                db.merge(rec)  # merge on PK; unique constraint dedupes
                inserted += 1
        db.commit()
        logger.info("seeded %d state cholera records from %s", inserted, csv_path)
        return {"inserted": inserted}
    finally:
        if own:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_CSV)
    print(seed_state_cholera(path))
