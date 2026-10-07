"""State-level cholera surveillance endpoints.

Backs the national state-choropleth and the national dashboard summary.
Serves VERIFIED state-level cumulative NCDC data (state_cholera_records);
deliberately no LGA redistribution.

Two numbers are kept strictly apart everywhere in this module:
  * `official_*`  — NCDC's published year-end national totals (app.constants).
  * `dataset_*`   — the sum of this dataset's per-state year-end snapshots.
They are not equal (our extraction stops at the last parsable report of the
year) and are never merged into a single "total".
"""
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import NATIONAL_TIER_EVIDENCE_LABEL, official_year_end
from app.database import get_db
from app.models import StateCholeraRecord, LGA
from app.services.state_names import (
    BOUNDARIES_PATH,
    boundaries_available,
    canonical_state,
    state_boundary_meta,
)

router = APIRouter(prefix="/api/states", tags=["states"])

CUMULATIVE_NOTE = (
    "Cumulative year-to-date snapshots; not directly comparable across years "
    "with differing reporting windows."
)


def _year_end_records(db: Session, year: Optional[int] = None) -> Dict[int, Dict[str, StateCholeraRecord]]:
    """{year: {state: highest-epi-week record}} over analysis-safe rows only.

    Records are cumulative year-to-date, so the year-end figure for a state is
    its latest report — never the sum of its weekly rows.
    """
    q = db.query(StateCholeraRecord).filter(StateCholeraRecord.monotonic_ok.is_(True))
    if year is not None:
        q = q.filter(StateCholeraRecord.year == year)

    grouped: Dict[int, Dict[str, StateCholeraRecord]] = {}
    for rec in q.all():
        by_state = grouped.setdefault(rec.year, {})
        current = by_state.get(rec.state)
        if current is None or rec.epi_week > current.epi_week:
            by_state[rec.state] = rec
    return grouped


def _years_available(db: Session) -> List[int]:
    """Years that have at least one analysis-safe record, most recent first."""
    rows = (
        db.query(StateCholeraRecord.year)
        .filter(StateCholeraRecord.monotonic_ok.is_(True))
        .distinct()
        .all()
    )
    return sorted({r[0] for r in rows}, reverse=True)


def _report_counts(db: Session, year: Optional[int] = None) -> Dict[tuple, int]:
    """{(year, state): number of extracted rows} — all rows, quarantined included."""
    q = db.query(
        StateCholeraRecord.year,
        StateCholeraRecord.state,
        func.count(StateCholeraRecord.id),
    )
    if year is not None:
        q = q.filter(StateCholeraRecord.year == year)
    return {(y, s): int(n) for y, s, n in q.group_by(StateCholeraRecord.year, StateCholeraRecord.state).all()}


def _year_summary(year: int, records: List[StateCholeraRecord]) -> Dict[str, object]:
    """Dataset-derived aggregate for one year, paired with the official figures."""
    cases = sum(r.suspected_cases or 0 for r in records)
    deaths = sum(r.deaths or 0 for r in records)
    last_week = max((r.epi_week for r in records), default=None)
    official = official_year_end(year)

    coverage = (
        f"Dataset snapshots taken at each state's latest parsed report "
        f"(latest epi-week in {year}: {last_week})."
        if last_week is not None
        else f"No parsed reports for {year}."
    )
    if official:
        coverage += (
            f" Official NCDC year-end total is measured at epi-week "
            f"{official['epi_week']}, so the dataset sum is a lower bound."
        )
    else:
        coverage += " No official year-end total is recorded for this year."

    return {
        "year": year,
        "dataset_sum_cases": cases,
        "dataset_sum_deaths": deaths,
        "dataset_cfr": round(deaths / cases * 100, 2) if cases else None,
        "states_reporting": len(records),
        "latest_epi_week": last_week,
        "official_cases": official["cases"] if official else None,
        "official_deaths": official["deaths"] if official else None,
        "official_cfr": official["cfr"] if official else None,
        "official_epi_week": official["epi_week"] if official else None,
        "official_citation": official["citation"] if official else None,
        "official_source_url": official["source_url"] if official else None,
        "coverage_note": coverage,
        "note": CUMULATIVE_NOTE,
    }


@router.get("/summary")
def state_national_summary(year: Optional[int] = None, db: Session = Depends(get_db)):
    """National burden summary derived from verified state-level records.

    Uses each state's highest-epi-week (year-end) record per year so cumulative
    records are not double counted. Only monotonic_ok rows are aggregated.

    Retained for backwards compatibility; /national-summary is the richer form
    that also carries the official NCDC totals.
    """
    grouped = _year_end_records(db, year)

    years_out = []
    for y in sorted(grouped, reverse=True):
        recs = list(grouped[y].values())
        cases = sum(r.suspected_cases or 0 for r in recs)
        deaths = sum(r.deaths or 0 for r in recs)
        years_out.append({
            "year": y,
            "cases": cases,
            "deaths": deaths,
            "states_reporting": len(recs),
            "cfr": round(deaths / cases * 100, 2) if cases else None,
            "note": CUMULATIVE_NOTE,
        })

    return {"years": years_out, "as_of": "Verified NCDC situation reports (state-level)"}


@router.get("/national-summary")
def national_summary(db: Session = Depends(get_db)):
    """Per-year dataset-derived burden alongside the official NCDC year-end totals.

    `dataset_sum_*` and `official_*` are deliberately separate fields: the
    dataset sum covers only the states and weeks we could parse, the official
    figure is NCDC's published national year-end total.
    """
    grouped = _year_end_records(db)
    years = [
        _year_summary(y, list(grouped[y].values()))
        for y in sorted(grouped, reverse=True)
    ]
    return {
        "years": years,
        "years_available": [y["year"] for y in years],
        "evidence_label": NATIONAL_TIER_EVIDENCE_LABEL,
        "as_of": "Verified NCDC situation reports (state-level)",
    }


@router.get("/choropleth")
def state_choropleth(
    year: Optional[int] = Query(None, description="Epi year; defaults to the latest year with data"),
    db: Session = Depends(get_db),
):
    """Per-state year-end snapshot joined to adm1 boundary codes, for the map.

    One row per state: its highest-epi-week analysis-safe record for `year`.
    States with no parsed report simply do not appear — the UI greys them out
    rather than showing a zero.
    """
    years_available = _years_available(db)
    if year is None:
        # Default to the most recent year that has an OFFICIAL NCDC year-end
        # total (so the landing view is a complete, citable year rather than a
        # partial in-progress one); fall back to the latest year with data.
        with_official = [y for y in years_available if official_year_end(y) is not None]
        year = (with_official or years_available or [None])[0]

    if year is None:
        return {
            "year": None,
            "years_available": [],
            "states": [],
            "count": 0,
            "unmatched_states": [],
            "evidence_label": NATIONAL_TIER_EVIDENCE_LABEL,
        }

    by_state = _year_end_records(db, year).get(year, {})
    counts = _report_counts(db, year)

    states = []
    unmatched = []
    for state, rec in by_state.items():
        meta = state_boundary_meta(state)
        if meta["adm1_pcode"] is None:
            unmatched.append(state)
        states.append({
            "state": rec.state,
            "adm1_name": meta["adm1_name"],
            "adm1_pcode": meta["adm1_pcode"],
            "suspected_cases": rec.suspected_cases,
            "deaths": rec.deaths,
            "cfr": rec.cfr,
            "epi_week": rec.epi_week,
            "source_url": rec.source_url,
            "confidence": rec.confidence,
            "n_reports": counts.get((year, state), 0),
        })

    states.sort(key=lambda s: -(s["suspected_cases"] or 0))
    return {
        "year": year,
        "years_available": years_available,
        "states": states,
        "count": len(states),
        "unmatched_states": sorted(unmatched),
        "evidence_label": NATIONAL_TIER_EVIDENCE_LABEL,
    }


@router.get("/boundaries")
def state_boundaries():
    """Nigeria adm1 (state) boundaries as GeoJSON, served from disk.

    Static reference geometry — cached hard by the browser so the ~1.6 MB file
    is fetched once per deploy.
    """
    if not boundaries_available():
        raise HTTPException(status_code=404, detail="State boundary file is not available")
    # No `filename=`: that would set Content-Disposition: attachment, which is
    # wrong for a layer the map fetches inline.
    return FileResponse(
        BOUNDARIES_PATH,
        media_type="application/geo+json",
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )


@router.get("/year/{year}")
def state_year_snapshot(year: int, db: Session = Depends(get_db)):
    """Each state's year-end (max-epi-week) cumulative figure for `year`."""
    by_state = _year_end_records(db, year).get(year, {})
    out = [
        {
            "state": rec.state,
            "epi_week": rec.epi_week,
            "suspected_cases": rec.suspected_cases,
            "deaths": rec.deaths,
            "cfr": rec.cfr,
            "confidence": rec.confidence,
            "source_url": rec.source_url,
        }
        for rec in by_state.values()
    ]
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


@router.get("/{state}/records")
def state_records(
    state: str,
    year: Optional[int] = Query(None, description="Restrict to a single epi year"),
    db: Session = Depends(get_db),
):
    """Every extracted record for a state — the provenance drill-down.

    Unlike the aggregate endpoints this returns quarantined rows too
    (`monotonic_ok = false`), because the point of the drill-down is to show the
    reviewer exactly what was extracted and from which PDF.
    """
    canonical = canonical_state(state)
    if canonical is None:
        raise HTTPException(status_code=404, detail=f"Unknown Nigerian state: {state}")

    # The dataset may spell the state differently from the boundary file
    # ("FCT" vs "Federal Capital Territory"), so match on canonical identity
    # rather than on the literal string the caller supplied.
    stored = {row[0] for row in db.query(StateCholeraRecord.state).distinct().all()}
    candidates = {s for s in stored if canonical_state(s) == canonical}
    candidates.add(state.strip())

    q = db.query(StateCholeraRecord).filter(
        func.lower(StateCholeraRecord.state).in_(sorted(c.lower() for c in candidates))
    )
    if year is not None:
        q = q.filter(StateCholeraRecord.year == year)
    records = q.order_by(StateCholeraRecord.year, StateCholeraRecord.epi_week).all()

    return {
        "state": canonical,
        "requested_state": state,
        "year": year,
        "count": len(records),
        "records": [
            {
                "year": r.year,
                "epi_week": r.epi_week,
                "month": r.month,
                "report_date": r.report_date.isoformat() if r.report_date else None,
                "suspected_cases": r.suspected_cases,
                "deaths": r.deaths,
                "cfr": r.cfr,
                "confidence": r.confidence,
                "extraction_method": r.extraction_method,
                "monotonic_ok": bool(r.monotonic_ok),
                "source_url": r.source_url,
            }
            for r in records
        ],
        "note": CUMULATIVE_NOTE,
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
