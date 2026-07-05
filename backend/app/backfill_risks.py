"""Backfill RiskScore history with algorithm v2.0 (monthly)."""
import argparse
import sys
import os
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta  # available via pandas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal
from app.models import LGA, RiskScore
from app.services.risk_calculator import RiskCalculator


def month_range(start: date, end: date):
    cur = start.replace(day=1)
    while cur <= end:
        yield cur
        cur += relativedelta(months=1)


def main():
    ap = argparse.ArgumentParser(
        description="Backfill RiskScore history with algorithm v2.0 (monthly per LGA)."
    )
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default="2025-12-01")
    args = ap.parse_args()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    db = SessionLocal()
    try:
        calc = RiskCalculator(db)
        lgas = db.query(LGA).all()
        n = 0
        for as_of in month_range(start, end):
            for lga in lgas:
                score, level, components = calc.calculate_for_lga(lga, as_of_date=as_of)
                existing = db.query(RiskScore).filter(
                    RiskScore.lga_id == lga.id, RiskScore.score_date == as_of
                ).first()
                if existing:
                    rs = existing
                else:
                    rs = RiskScore(lga_id=lga.id, score_date=as_of)
                    db.add(rs)
                rs.score = score
                rs.level = level
                rs.flood_score = components["flood_score"]
                rs.flood_event_score = components["flood_event_score"]
                rs.rainfall_score = components["rainfall_score"]
                rs.case_score = components["case_score"]
                rs.vulnerability_score = components["vulnerability_score"]
                rs.recent_flood_events = components["recent_flood_events"]
                rs.rainfall_mm = components["rainfall_mm"]
                rs.ndwi = components["ndwi"]
                rs.recent_cases = components["recent_cases"]
                rs.recent_deaths = components["recent_deaths"]
                rs.algorithm_version = "2.0"
                n += 1
            db.commit()
            print(f"backfilled through {as_of} ({n} rows)")
        print(f"done: {n} risk rows")
    finally:
        db.close()


if __name__ == "__main__":
    main()
