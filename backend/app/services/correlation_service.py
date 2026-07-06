# backend/app/services/correlation_service.py
"""Monthly time-lag correlation between flood events and cholera cases."""
import logging
from typing import Dict, List, Tuple, Any, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from scipy.stats import pearsonr

from app.models import FloodEvent, CaseReport, LGA

logger = logging.getLogger(__name__)

MIN_OVERLAP = 6


def _scope_filter(scope: Dict[str, Any]):
    level = scope.get("level", "national")
    if level == "lga" and scope.get("lga_id"):
        return lambda f: f
    return None


def build_monthly_flood_series(db: Session, scope: Dict[str, Any], from_year: int, to_year: int):
    """Return rows of (year, month, event_count, area_sum)."""
    q = db.query(
        func.extract("year", FloodEvent.start_date).label("y"),
        func.extract("month", FloodEvent.start_date).label("m"),
        func.count(FloodEvent.id).label("cnt"),
        func.coalesce(func.sum(FloodEvent.area_km2), 0.0).label("area"),
    ).filter(
        FloodEvent.start_date >= f"{from_year}-01-01",
        FloodEvent.start_date < f"{to_year + 1}-01-01",
    )
    if scope.get("level") == "lga" and scope.get("lga_id"):
        q = q.filter(FloodEvent.lga_id == scope["lga_id"])
    elif scope.get("level") == "state" and scope.get("state"):
        q = q.join(LGA, LGA.id == FloodEvent.lga_id).filter(LGA.state == scope["state"])
    q = q.group_by("y", "m").order_by("y", "m")
    return [(int(r.y), int(r.m), int(r.cnt), float(r.area)) for r in q.all()]


def build_monthly_case_series(db: Session, scope: Dict[str, Any], from_year: int, to_year: int):
    """Return rows of (year, month, cases_sum)."""
    q = db.query(
        func.extract("year", CaseReport.report_date).label("y"),
        func.extract("month", CaseReport.report_date).label("m"),
        func.coalesce(func.sum(CaseReport.new_cases), 0.0).label("cases"),
    ).filter(
        CaseReport.report_date >= f"{from_year}-01-01",
        CaseReport.report_date < f"{to_year + 1}-01-01",
    )
    if scope.get("level") == "lga" and scope.get("lga_id"):
        q = q.filter(CaseReport.lga_id == scope["lga_id"])
    elif scope.get("level") == "state" and scope.get("state"):
        q = q.join(LGA, LGA.id == CaseReport.lga_id).filter(LGA.state == scope["state"])
    q = q.group_by("y", "m").order_by("y", "m")
    return [(int(r.y), int(r.m), int(r.cases)) for r in q.all()]


def _month_key(y, m):
    return y * 12 + (m - 1)


def series_to_monthly_map(series, value_idx) -> Dict[Tuple[int, int], float]:
    return {(r[0], r[1]): float(r[value_idx]) for r in series}


def cross_correlate(
    flood: Dict[Tuple[int, int], float],
    cases: Dict[Tuple[int, int], float],
    lags: Tuple[int, ...] = (0, 1, 2, 3, 4),
) -> List[Dict[str, Any]]:
    """Pearson r between flood[m] and cases[m+lag] over overlapping months."""
    results = []
    all_keys = sorted(set(flood) | set(cases))
    for lag in lags:
        xs, ys = [], []
        for (y, m), fv in flood.items():
            target = _shift_month(y, m, lag)
            if target in cases:
                xs.append(fv)
                ys.append(cases[target])
        n = len(xs)
        if n < MIN_OVERLAP:
            results.append({"lag": lag, "pearson_r": None, "p_value": None,
                            "n": n, "insufficient_data": True})
            continue
        if len(set(xs)) < 2 or len(set(ys)) < 2:
            results.append({"lag": lag, "pearson_r": 0.0, "p_value": None,
                            "n": n, "insufficient_data": False})
            continue
        r, p = pearsonr(xs, ys)
        results.append({"lag": lag, "pearson_r": float(r), "p_value": float(p),
                        "n": n, "insufficient_data": False})
    return results


def _shift_month(y: int, m: int, lag: int) -> Tuple[int, int]:
    idx = y * 12 + (m - 1) + lag
    return idx // 12, (idx % 12) + 1


def build_correlation_report(db: Session, scope: Dict[str, Any],
                             from_year: int, to_year: int) -> Dict[str, Any]:
    flood_rows = build_monthly_flood_series(db, scope, from_year, to_year)
    case_rows = build_monthly_case_series(db, scope, from_year, to_year)
    flood = series_to_monthly_map(flood_rows, 2)  # event_count
    cases = series_to_monthly_map(case_rows, 2)
    lags = cross_correlate(flood, cases)
    return {
        "scope": scope,
        "from_year": from_year,
        "to_year": to_year,
        "flood_series": [{"year": r[0], "month": r[1], "count": r[2], "area": r[3]} for r in flood_rows],
        "case_series": [{"year": r[0], "month": r[1], "cases": r[2]} for r in case_rows],
        "lags": lags,
        "caveat": "Correlation is a decision-support signal, not proof of causation.",
    }
