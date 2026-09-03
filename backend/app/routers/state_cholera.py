"""State-level cholera surveillance endpoints.

Backs the national state-choropleth and the national dashboard summary.
Serves VERIFIED state-level cumulative NCDC data (state_cholera_records);
deliberately no LGA redistribution.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StateCholeraRecord, LGA

router = APIRouter(prefix="/api/states", tags=["states"])


@router.get("/summary")
def state_national_summary(year: Optional[int] = None, db: Session = Depends(get_db)):
    """National burden summary derived from verified state-level records.

    Uses each state's highest-epi-week (year-end) record per year so cumulative
    records are not double counted. Only monotonic_ok rows are aggregated.
    """
    q = db.query(StateCholeraRecord).filter(StateCholeraRecord.monotonic_ok.is_(True))
    if year:
        q = q.filter(StateCholeraRecord.year == year)

    # per (state,year) take the max epi_week
    rows = q.all()
    grouped = {}
    for r in rows:
        key = (r.year, r.state)
        cur = grouped.get(key)
        if cur is None or r.epi_week > cur.epi_week:
            grouped[key] = r

    by_year = {}
    for (y, _s), rec in grouped.items():
        by_year.setdefault(y, []).append(rec)

    years_out = []
    for y in sorted(by_year):
        recs = by_year[y]
        cases = sum(r.suspected_cases or 0 for r in recs)
        deaths = sum(r.deaths or 0 for r in recs)
        states = len(recs)
        years_out.append({
            "year": y,
            "cases": cases,
            "deaths": deaths,
            "states_reporting": states,
            "cfr": round(deaths / cases * 100, 2) if cases else None,
            "note": "Cumulative year-to-date snapshots; not directly comparable across years with differing reporting windows.",
        })

    years_out.sort(key=lambda x: -x["year"])
    return {"years": years_out, "as_of": "Verified NCDC situation reports (state-level)"}


@router.get("/year/{year}")
def state_year_snapshot(year: int, db: Session = Depends(get_db)):
    """Each state's year-end (max-epi-week) cumulative figure for `year`."""
    rows = db.query(StateCholeraRecord).filter(
        StateCholeraRecord.year == year,
        StateCholeraRecord.monotonic_ok.is_(True),
    ).all()
    grouped = {}
    for r in rows:
        cur = grouped.get(r.state)
        if cur is None or r.epi_week > cur.epi_week:
            grouped[r.state] = r
    out = []
    for state, rec in grouped.items():
        out.append({
            "state": rec.state,
            "epi_week": rec.epi_week,
            "suspected_cases": rec.suspected_cases,
            "deaths": rec.deaths,
            "cfr": rec.cfr,
            "confidence": rec.confidence,
            "source_url": rec.source_url,
        })
    out.sort(key=lambda x: -(x["suspected_cases"] or 0))
    return {"year": year, "states": out, "count": len(out)}


@router.get("/timeline/{state}")
def state_timeline(state: str, year: Optional[int] = None, db: Session = Depends(get_db)):
    """Full cumulative-to-date series for one state (2021-2025)."""
    q = db.query(StateCholeraRecord).filter(
        func.lower(StateCholeraRecord.state) == state.strip().lower(),
        StateCholeraRecord.monotonic_ok.is_(True),
    )
    if year:
        q = q.filter(StateCholeraRecord.year == year)
    q = q.order_by(StateCholeraRecord.year, StateCholeraRecord.epi_week)
    return {
        "state": state,
        "records": [
            {
                "year": r.year, "epi_week": r.epi_week, "report_date": r.report_date.isoformat(),
                "suspected_cases": r.suspected_cases, "deaths": r.deaths, "cfr": r.cfr,
                "confidence": r.confidence,
            }
            for r in q.all()
        ],
    }


@router.get("/pilot-lgas")
def pilot_lgas(db: Session = Depends(get_db)):
    """The four Cross River pilot LGAs with their real observed data.

    This is the ONLY sub-national (LGA) tier -- real line-list data used for
    the Section 4 pilot. National figures are state-level (see /summary).
    """
    pilot = db.query(LGA).filter(LGA.state.ilike("%cross river%")).all()
    # The four pilot LGAs per the manuscript
    names = {"Yakurr", "Biase", "Calabar Municipal", "Bakassi"}
    matched = [l for l in pilot if l.name in names]
    return {
        "pilot_states": ["Cross River"],
        "pilot_lgas": [{"name": l.name, "state": l.state, "id": l.id} for l in matched],
        "note": "Pilot tier only; no data redistributed from state totals to LGAs.",
    }