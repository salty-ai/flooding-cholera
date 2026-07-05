"""Adapter for the nationwide monthly cholera surveillance CSV.

Parses the nationwide monthly cholera CSV (one row per LGA-month) into
`CaseReport` rows, fuzzy-matching the LGA by name + state via
`DataImporter._find_lga_id`, and upserting on `(lga_id, report_date)`.

Per design §2.5, epi_week/epi_year are derived from the Year+Month-derived
report_date using the ISO 8601 epidemiological-week convention
(`date.isocalendar()`). Latitude/Longitude columns are intentionally ignored —
PostGIS LGA geometry is authoritative.
"""
import csv
import logging
from datetime import date
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import CaseReport
from app.services.data_importer import DataImporter

logger = logging.getLogger(__name__)

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def month_to_date(year: int, month: str) -> Optional[date]:
    m = MONTHS.get(str(month).strip().lower())
    if not m:
        return None
    return date(int(year), m, 1)


def epi_week_of_date(d: date) -> Tuple[int, int]:
    """Return (epi_week, epi_year) using the ISO 8601 epidemiological-week convention.

    `date.isocalendar()` returns ISO year, ISO week, ISO weekday. For a
    report_date that is the 1st of a month, this is a reasonable approximation
    of the epi week containing that month's report.
    """
    iso = d.isocalendar()
    return (iso.week, iso.year)


def _safe_int(v, default: int = 0) -> int:
    try:
        return int(float(str(v).strip()))
    except (ValueError, TypeError):
        return default


def parse_cholera_row(row: Dict[str, str]) -> Dict[str, Any]:
    return {
        "state": (row.get("State") or "").strip(),
        "lga_name": (row.get("LGA") or "").strip(),
        "report_date": month_to_date(int(row["Year"]), row["Month"]),
        "suspected_cases": _safe_int(row.get("Suspected_Cases", 0)),
        "confirmed_cases": _safe_int(row.get("Confirmed_Cases", 0)),
        "deaths": _safe_int(row.get("Deaths", 0)),
        "notes": (row.get("Classification") or "").strip() or None,
    }


def import_cholera_monthly(db: Session, csv_path: str) -> Dict[str, Any]:
    importer = DataImporter(db)  # for _find_lga_id
    imported = failed = 0
    unknown = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rec = parse_cholera_row(row)
            if not rec["report_date"]:
                failed += 1
                continue
            lga_id = importer._find_lga_id(rec["lga_name"], state=rec["state"])
            if not lga_id:
                failed += 1
                key = f"{rec['state']}/{rec['lga_name']}"
                if key not in unknown:
                    unknown.append(key)
                continue
            existing = db.query(CaseReport).filter(
                CaseReport.lga_id == lga_id,
                CaseReport.report_date == rec["report_date"],
            ).first()
            epi_week, epi_year = epi_week_of_date(rec["report_date"])
            values = dict(
                new_cases=rec["suspected_cases"],
                suspected_cases=rec["suspected_cases"],
                confirmed_cases=rec["confirmed_cases"],
                deaths=rec["deaths"],
                epi_week=epi_week,
                epi_year=epi_year,
                source="uploaded",
                source_file=csv_path,
                notes=rec["notes"],
            )
            if existing:
                for k, v in values.items():
                    setattr(existing, k, v)
            else:
                db.add(CaseReport(lga_id=lga_id, report_date=rec["report_date"], **values))
            imported += 1
    db.commit()
    logger.info(
        f"Cholera import: imported={imported} failed={failed} unknown_lgas={len(unknown)}"
    )
    return {"imported": imported, "failed": failed, "unknown_lgas": unknown[:50]}
