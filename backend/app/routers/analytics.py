"""Analytics endpoints for charts and time-series data."""
import csv
import io
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import LGA, RiskScore, CaseReport, EnvironmentalData
from app.schemas import LGAAnalytics, TimeSeriesPoint
from app.rate_limiter import limiter
from app.services.correlation_service import build_correlation_report

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/lga/{lga_id}", response_model=LGAAnalytics)
@limiter.limit("60/minute")
def get_lga_analytics(
    request: Request,
    lga_id: int,
    days: int = Query(90, ge=7, le=365, description="Number of days for time series"),
    db: Session = Depends(get_db)
):
    """Get comprehensive analytics for a single LGA."""
    lga = db.query(LGA).filter(LGA.id == lga_id).first()
    if not lga:
        raise HTTPException(status_code=404, detail="LGA not found")

    start_date = date.today() - timedelta(days=days)

    # Cases time series
    cases = (
        db.query(CaseReport)
        .filter(
            CaseReport.lga_id == lga_id,
            CaseReport.report_date >= start_date
        )
        .order_by(CaseReport.report_date)
        .all()
    )

    cases_ts = [
        TimeSeriesPoint(date=c.report_date, value=float(c.new_cases))
        for c in cases
    ]

    deaths_ts = [
        TimeSeriesPoint(date=c.report_date, value=float(c.deaths))
        for c in cases
    ]

    # Environmental time series
    env_data = (
        db.query(EnvironmentalData)
        .filter(
            EnvironmentalData.lga_id == lga_id,
            EnvironmentalData.observation_date >= start_date
        )
        .order_by(EnvironmentalData.observation_date)
        .all()
    )

    rainfall_ts = [
        TimeSeriesPoint(date=e.observation_date, value=e.rainfall_mm or 0)
        for e in env_data
    ]

    # Risk scores time series
    risk_scores = (
        db.query(RiskScore)
        .filter(
            RiskScore.lga_id == lga_id,
            RiskScore.score_date >= start_date
        )
        .order_by(RiskScore.score_date)
        .all()
    )

    risk_ts = [
        TimeSeriesPoint(date=rs.score_date, value=rs.score)
        for rs in risk_scores
    ]

    # Aggregate stats
    total_cases = sum(c.new_cases for c in cases)
    total_deaths = sum(c.deaths for c in cases)
    avg_risk = sum(rs.score for rs in risk_scores) / len(risk_scores) if risk_scores else 0

    # Current risk level
    current_risk = "unknown"
    if risk_scores:
        current_risk = risk_scores[-1].level

    return LGAAnalytics(
        lga_id=lga_id,
        lga_name=lga.name,
        cases_time_series=cases_ts,
        deaths_time_series=deaths_ts,
        rainfall_time_series=rainfall_ts,
        risk_time_series=risk_ts,
        total_cases=total_cases,
        total_deaths=total_deaths,
        avg_risk_score=round(avg_risk, 3),
        current_risk_level=current_risk
    )


@router.get("/risk-scores", response_model=List[dict])
@limiter.limit("60/minute")
def get_all_risk_scores(
    request: Request,
    score_date: Optional[date] = Query(None, description="Get scores for specific date"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Get latest risk scores for all LGAs with pagination."""
    if score_date:
        # Get scores for specific date
        scores = (
            db.query(RiskScore, LGA.name)
            .join(LGA)
            .filter(RiskScore.score_date == score_date)
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        # Get latest scores for each LGA
        subquery = (
            db.query(
                RiskScore.lga_id,
                func.max(RiskScore.score_date).label("max_date")
            )
            .group_by(RiskScore.lga_id)
            .subquery()
        )

        scores = (
            db.query(RiskScore, LGA.name)
            .join(LGA)
            .join(
                subquery,
                (RiskScore.lga_id == subquery.c.lga_id) &
                (RiskScore.score_date == subquery.c.max_date)
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    return [
        {
            "lga_id": rs.lga_id,
            "lga_name": lga_name,
            "score": rs.score,
            "level": rs.level,
            "score_date": rs.score_date.isoformat(),
            "recent_cases": rs.recent_cases,
            "recent_deaths": rs.recent_deaths,
            "rainfall_mm": rs.rainfall_mm,
            "flood_score": rs.flood_score,
            "case_score": rs.case_score,
            "flood_event_score": rs.flood_event_score,
            "recent_flood_events": rs.recent_flood_events,
            "vulnerability_score": rs.vulnerability_score,
            "algorithm_version": rs.algorithm_version,
        }
        for rs, lga_name in scores
    ]


@router.get("/comparison")
@limiter.limit("30/minute")
def get_lga_comparison(
    request: Request,
    lga_ids: str = Query(..., description="Comma-separated LGA IDs"),
    metric: str = Query("cases", description="Metric to compare: cases, deaths, rainfall, risk"),
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db)
):
    """Compare metrics across multiple LGAs."""
    try:
        ids = [int(x.strip()) for x in lga_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid LGA IDs format")

    # Limit number of LGAs to compare
    if len(ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 LGAs can be compared at once")

    start_date = date.today() - timedelta(days=days)
    result = {}

    for lga_id in ids:
        lga = db.query(LGA).filter(LGA.id == lga_id).first()
        if not lga:
            continue

        if metric == "cases":
            data = db.query(CaseReport).filter(
                CaseReport.lga_id == lga_id,
                CaseReport.report_date >= start_date
            ).order_by(CaseReport.report_date).all()
            result[lga.name] = [
                {"date": d.report_date.isoformat(), "value": d.new_cases}
                for d in data
            ]
        elif metric == "deaths":
            data = db.query(CaseReport).filter(
                CaseReport.lga_id == lga_id,
                CaseReport.report_date >= start_date
            ).order_by(CaseReport.report_date).all()
            result[lga.name] = [
                {"date": d.report_date.isoformat(), "value": d.deaths}
                for d in data
            ]
        elif metric == "rainfall":
            data = db.query(EnvironmentalData).filter(
                EnvironmentalData.lga_id == lga_id,
                EnvironmentalData.observation_date >= start_date
            ).order_by(EnvironmentalData.observation_date).all()
            result[lga.name] = [
                {"date": d.observation_date.isoformat(), "value": d.rainfall_mm or 0}
                for d in data
            ]
        elif metric == "risk":
            data = db.query(RiskScore).filter(
                RiskScore.lga_id == lga_id,
                RiskScore.score_date >= start_date
            ).order_by(RiskScore.score_date).all()
            result[lga.name] = [
                {"date": d.score_date.isoformat(), "value": d.score}
                for d in data
            ]

    return {"metric": metric, "days": days, "data": result}


@router.get("/summary/weekly")
@limiter.limit("30/minute")
def get_weekly_summary(
    request: Request,
    weeks: int = Query(12, ge=1, le=52),
    db: Session = Depends(get_db)
):
    """Get weekly aggregated summary across all LGAs."""
    end_date = date.today()
    start_date = end_date - timedelta(weeks=weeks)

    # Aggregate cases by week
    cases = (
        db.query(
            func.date_trunc('week', CaseReport.report_date).label('week'),
            func.sum(CaseReport.new_cases).label('total_cases'),
            func.sum(CaseReport.deaths).label('total_deaths')
        )
        .filter(CaseReport.report_date >= start_date)
        .group_by(func.date_trunc('week', CaseReport.report_date))
        .order_by('week')
        .all()
    )

    # Aggregate environmental data by week
    env_data = (
        db.query(
            func.date_trunc('week', EnvironmentalData.observation_date).label('week'),
            func.avg(EnvironmentalData.flood_extent_pct).label('avg_flood_extent'),
            func.avg(EnvironmentalData.rainfall_mm).label('avg_rainfall')
        )
        .filter(EnvironmentalData.observation_date >= start_date)
        .group_by(func.date_trunc('week', EnvironmentalData.observation_date))
        .all()
    )

    # Create valid lookup for env stats
    env_map = {
        str(row.week): {"flood": row.avg_flood_extent or 0, "rain": row.avg_rainfall or 0}
        for row in env_data
    }

    return {
        "weeks": weeks,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "weekly_data": [
            {
                "week": w.isoformat() if hasattr(w, 'isoformat') else str(w),
                "cases": int(c or 0),
                "deaths": int(d or 0),
                "flood_extent": env_map.get(str(w), {}).get("flood", 0),
                "rainfall": env_map.get(str(w), {}).get("rain", 0)
            }
            for w, c, d in cases
        ]
    }


@router.get("/correlation")
@limiter.limit("30/minute")
def get_correlation(
    request: Request,
    lga_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    from_year: int = Query(2020, ge=2000, le=2100),
    to_year: int = Query(2025, ge=2000, le=2100),
    db: Session = Depends(get_db),
):
    if lga_id:
        scope = {"level": "lga", "lga_id": lga_id}
    elif state:
        scope = {"level": "state", "state": state}
    else:
        scope = {"level": "national"}
    return build_correlation_report(db, scope, from_year, to_year)


@router.get("/correlation/export")
@limiter.limit("20/minute")
def export_correlation(
    request: Request,
    lga_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    from_year: int = Query(2020, ge=2000, le=2100),
    to_year: int = Query(2025, ge=2000, le=2100),
    db: Session = Depends(get_db),
):
    if lga_id:
        scope = {"level": "lga", "lga_id": lga_id}
    elif state:
        scope = {"level": "state", "state": state}
    else:
        scope = {"level": "national"}
    report = build_correlation_report(db, scope, from_year, to_year)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["lag", "pearson_r", "p_value", "n", "insufficient_data"])
    for r in report["lags"]:
        w.writerow([r["lag"], r["pearson_r"], r["p_value"], r["n"], r["insufficient_data"]])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=correlation.csv"})
