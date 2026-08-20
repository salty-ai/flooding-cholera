# backend/app/services/correlation_service.py
"""Exploratory monthly lag correlation between environmental and case series.

Results are association signals only. A month lag is not an exact day lag, and
nominal Pearson p-values do not account for temporal or spatial dependence.
"""
import logging
import math
from typing import Dict, List, Tuple, Any, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from scipy.stats import pearsonr

from app.models import FloodEvent, CaseReport, EnvironmentalData, LGA

logger = logging.getLogger(__name__)

# Six overlapping months is the minimum descriptive threshold. Results below this
# threshold are explicitly marked insufficient rather than treated as statistics.
MIN_OVERLAP = 6


def _fisher_confidence_interval(r: float, n: int, z_value: float = 1.96):
    """Approximate 95% Fisher-z confidence interval for Pearson r."""
    if n <= 3 or not math.isfinite(r) or abs(r) >= 1:
        return None
    z = math.atanh(r)
    se = 1 / math.sqrt(n - 3)
    return [
        math.tanh(z - z_value * se),
        math.tanh(z + z_value * se),
    ]


def build_monthly_flood_series(db: Session, scope: Dict[str, Any], from_year: int, to_year: int):
    """Return rows of (year, month, event_count, area_sum)."""
    # 1. Query FloodEvents
    q_fe = db.query(
        func.extract("year", FloodEvent.start_date).label("y"),
        func.extract("month", FloodEvent.start_date).label("m"),
        func.count(FloodEvent.id).label("cnt"),
        func.coalesce(func.sum(FloodEvent.area_km2), 0.0).label("area"),
    ).filter(
        FloodEvent.start_date >= f"{from_year}-01-01",
        FloodEvent.start_date < f"{to_year + 1}-01-01",
    )
    if scope.get("level") == "lga" and scope.get("lga_id"):
        q_fe = q_fe.filter(FloodEvent.lga_id == scope["lga_id"])
    elif scope.get("level") == "state" and scope.get("state"):
        q_fe = q_fe.join(LGA, LGA.id == FloodEvent.lga_id).filter(LGA.state == scope["state"])
    q_fe = q_fe.group_by("y", "m")
    fe_map = {(int(r.y), int(r.m)): (int(r.cnt), float(r.area)) for r in q_fe.all()}

    # 2. Query EnvironmentalData (Rainfall & Flood extent)
    q_env = db.query(
        func.extract("year", EnvironmentalData.observation_date).label("y"),
        func.extract("month", EnvironmentalData.observation_date).label("m"),
        func.count(EnvironmentalData.id).label("cnt"),
        func.coalesce(func.sum(EnvironmentalData.rainfall_mm), 0.0).label("area"),
    ).filter(
        EnvironmentalData.observation_date >= f"{from_year}-01-01",
        EnvironmentalData.observation_date < f"{to_year + 1}-01-01",
    )
    if scope.get("level") == "lga" and scope.get("lga_id"):
        q_env = q_env.filter(EnvironmentalData.lga_id == scope["lga_id"])
    elif scope.get("level") == "state" and scope.get("state"):
        q_env = q_env.join(LGA, LGA.id == EnvironmentalData.lga_id).filter(LGA.state == scope["state"])
    q_env = q_env.group_by("y", "m")
    env_map = {(int(r.y), int(r.m)): (int(r.cnt), float(r.area)) for r in q_env.all()}

    # Merge keys
    all_ym = sorted(set(fe_map.keys()) | set(env_map.keys()))
    rows = []
    for (y, m) in all_ym:
        fe_cnt, fe_area = fe_map.get((y, m), (0, 0.0))
        env_cnt, env_area = env_map.get((y, m), (0, 0.0))
        cnt = fe_cnt + env_cnt
        area = fe_area + env_area
        rows.append((y, m, cnt, area))

    return rows


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


def series_to_monthly_map(series, value_idx) -> Dict[Tuple[int, int], float]:
    return {(r[0], r[1]): float(r[value_idx]) for r in series}


def cross_correlate(
    flood: Dict[Tuple[int, int], float],
    cases: Dict[Tuple[int, int], float],
    lags: Tuple[int, ...] = (0, 1, 2, 3, 4),
) -> List[Dict[str, Any]]:
    """Return exploratory Pearson associations for month-index lags.

    A lag of 1 means the next calendar month, not a precisely measured
    30-day delay. Nominal p-values and Fisher intervals are descriptive and
    require dependence-aware analysis before inferential claims.
    """
    results = []
    for lag in lags:
        xs, ys = [], []
        for (y, m), fv in flood.items():
            target = _shift_month(y, m, lag)
            if target in cases:
                xs.append(fv)
                ys.append(cases[target])
        n = len(xs)
        if n < MIN_OVERLAP:
            results.append({
                "lag": lag,
                "lag_unit": "months",
                "pearson_r": 0.0,
                "p_value": None,
                "confidence_interval": None,
                "n": n,
                "insufficient_data": True,
                "evidence_status": "insufficient_data",
            })
            continue
        if len(set(xs)) < 2 or len(set(ys)) < 2:
            results.append({
                "lag": lag,
                "lag_unit": "months",
                "pearson_r": 0.0,
                "p_value": None,
                "confidence_interval": None,
                "n": n,
                "insufficient_data": False,
                "evidence_status": "exploratory",
            })
            continue
        r, p = pearsonr(xs, ys)
        results.append({
            "lag": lag,
            "lag_unit": "months",
            "pearson_r": float(r) if not (r != r) else 0.0,
            "p_value": float(p) if not (p != p) else None,
            "confidence_interval": _fisher_confidence_interval(float(r), n),
            "n": n,
            "insufficient_data": False,
            "evidence_status": "exploratory",
        })
    return results


def _shift_month(y: int, m: int, lag: int) -> Tuple[int, int]:
    idx = y * 12 + (m - 1) + lag
    return idx // 12, (idx % 12) + 1


def build_correlation_report(
    db: Session, scope: Dict[str, Any], from_year: int, to_year: int
) -> Dict[str, Any]:
    flood_rows = build_monthly_flood_series(db, scope, from_year, to_year)
    case_rows = build_monthly_case_series(db, scope, from_year, to_year)
    flood = series_to_monthly_map(flood_rows, 2)  # count
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
