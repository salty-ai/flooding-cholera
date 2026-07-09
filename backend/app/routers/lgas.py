"""LGA (Local Government Area) endpoints."""
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

from app.database import get_db
from app.models import LGA, RiskScore, CaseReport, EnvironmentalData
from app.schemas import (
    LGAResponse, LGAWithGeometry, LGAListResponse,
    RiskScoreResponse, RiskScoreWithLGA,
    GeoJSONFeature, GeoJSONFeatureCollection,
    DashboardSummary
)
from app.rate_limiter import limiter

router = APIRouter(prefix="/api/lgas", tags=["LGAs"])


@router.get("", response_model=LGAListResponse)
@limiter.limit("60/minute")
def list_lgas(
    request: Request,
    search: Optional[str] = Query(None, description="Search by LGA name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """List all LGAs with optional search filter and pagination."""
    query = db.query(LGA)

    if search:
        query = query.filter(LGA.name.ilike(f"%{search}%"))

    # Get total count before pagination
    total = query.count()

    # Apply pagination
    lgas = query.order_by(LGA.name).offset(skip).limit(limit).all()

    return LGAListResponse(
        total=total,
        lgas=lgas,
        skip=skip,
        limit=limit
    )


@router.get("/geojson", response_model=GeoJSONFeatureCollection)
@limiter.limit("30/minute")
def get_lgas_geojson(
    request: Request,
    date_str: Optional[str] = Query(None, alias="date"),
    db: Session = Depends(get_db)
):
    """
    Get all LGAs as GeoJSON FeatureCollection with risk scores.
    If 'date' is provided (YYYY-MM-DD), returns risk scores for that specific day.
    Otherwise returns the latest available scores.
    """
    target_date = None
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")

    if target_date:
        # Get scores exactly on the target date
        scores = db.query(RiskScore).filter(RiskScore.score_date == target_date).all()

        # If no scores found for exact date, try finding nearest prior scores (up to 7 days back)
        if not scores:
            # Use subquery pattern for database compatibility (works on both PostgreSQL and SQLite)
            subquery = (
                db.query(
                    RiskScore.lga_id,
                    func.max(RiskScore.score_date).label("max_date")
                )
                .filter(
                    RiskScore.score_date <= target_date,
                    RiskScore.score_date >= target_date - timedelta(days=7)
                )
                .group_by(RiskScore.lga_id)
                .subquery()
            )

            scores = (
                db.query(RiskScore)
                .join(
                    subquery,
                    (RiskScore.lga_id == subquery.c.lga_id) &
                    (RiskScore.score_date == subquery.c.max_date)
                )
                .all()
            )
    else:
        # Get latest risk scores for each LGA
        subquery = (
            db.query(
                RiskScore.lga_id,
                func.max(RiskScore.score_date).label("max_date")
            )
            .group_by(RiskScore.lga_id)
            .subquery()
        )

        scores = (
            db.query(RiskScore)
            .join(
                subquery,
                (RiskScore.lga_id == subquery.c.lga_id) &
                (RiskScore.score_date == subquery.c.max_date)
            )
            .all()
        )

    score_map = {rs.lga_id: rs for rs in scores} # use scores variable

    # Get all LGAs
    lgas = db.query(LGA).all()

    features = []
    for lga in lgas:
        risk_score = score_map.get(lga.id)

        properties = {
            "id": lga.id,
            "name": lga.name,
            "code": lga.code,
            "population": lga.population,
            "centroid_lat": lga.centroid_lat,
            "centroid_lon": lga.centroid_lon,
            "risk_score": risk_score.score if risk_score else None,
            "risk_level": risk_score.level if risk_score else "unknown",
            "recent_cases": risk_score.recent_cases if risk_score else 0,
            "recent_deaths": risk_score.recent_deaths if risk_score else 0
        }

        # Convert PostGIS geometry to GeoJSON
        geometry = None
        if lga.geometry is not None:
            try:
                geometry = mapping(to_shape(lga.geometry))
            except Exception:
                pass

        features.append(GeoJSONFeature(
            id=lga.id,
            properties=properties,
            geometry=geometry or {"type": "Polygon", "coordinates": []}
        ))

    return GeoJSONFeatureCollection(features=features)


@router.get("/dashboard", response_model=DashboardSummary)
@limiter.limit("60/minute")
def get_dashboard_summary(
    request: Request,
    start_date: Optional[date] = Query(None, description="Window start (ISO)"),
    end_date: Optional[date] = Query(None, description="Window end (ISO)"),
    db: Session = Depends(get_db),
):
    """Get dashboard summary statistics over a date window.

    With no params, defaults to the latest-available 30-day window
    (ending at the most recent CaseReport.report_date).
    """
    # Resolve the date window (latest-available default)
    max_report_date = db.query(func.max(CaseReport.report_date)).scalar()
    if end_date is not None:
        window_end = end_date
    else:
        window_end = max_report_date  # may be None if no case data

    if start_date is not None:
        window_start = start_date
    elif window_end is not None:
        window_start = window_end - timedelta(days=30)
    else:
        window_start = None

    # Count LGAs
    total_lgas = db.query(func.count(LGA.id)).scalar()

    # Cases/deaths over the resolved window
    case_q = db.query(func.sum(CaseReport.new_cases), func.sum(CaseReport.deaths))
    if window_start is not None and window_end is not None:
        case_q = case_q.filter(
            CaseReport.report_date >= window_start,
            CaseReport.report_date <= window_end,
        )
    case_stats = case_q.first()
    total_cases = case_stats[0] or 0
    total_deaths = case_stats[1] or 0

    # Latest risk levels count (unchanged logic)
    subquery = (
        db.query(
            RiskScore.lga_id,
            func.max(RiskScore.score_date).label("max_date")
        )
        .group_by(RiskScore.lga_id)
        .subquery()
    )

    latest_scores = (
        db.query(RiskScore)
        .join(
            subquery,
            (RiskScore.lga_id == subquery.c.lga_id) &
            (RiskScore.score_date == subquery.c.max_date)
        )
        .all()
    )

    high_risk = sum(1 for rs in latest_scores if rs.level == "red")
    medium_risk = sum(1 for rs in latest_scores if rs.level == "yellow")
    low_risk = sum(1 for rs in latest_scores if rs.level == "green")

    # Average rainfall over latest-available 7d (relative to window_end, not today)
    rain_end = window_end or date.today()
    rain_start = rain_end - timedelta(days=7)
    avg_rainfall = (
        db.query(func.avg(EnvironmentalData.rainfall_mm))
        .filter(
            EnvironmentalData.observation_date >= rain_start,
            EnvironmentalData.observation_date <= rain_end,
        )
        .scalar()
        or 0.0
    )

    return DashboardSummary(
        total_lgas=total_lgas,
        total_cases=total_cases,
        total_deaths=total_deaths,
        lgas_high_risk=high_risk,
        lgas_medium_risk=medium_risk,
        lgas_low_risk=low_risk,
        avg_rainfall_7day=round(avg_rainfall, 2),
        last_updated=max_report_date,  # real max data date, not today
        active_alerts_count=0,  # filled in Task 3
        alert_level="green",    # filled in Task 3
        flood_events_count=0,   # filled in Task 3
        applied_window_start=window_start,
        applied_window_end=window_end,
        max_data_date=max_report_date,
    )


@router.get("/{lga_id}", response_model=LGAWithGeometry)
@limiter.limit("60/minute")
def get_lga(request: Request, lga_id: int, db: Session = Depends(get_db)):
    """Get single LGA by ID with geometry."""
    lga = db.query(LGA).filter(LGA.id == lga_id).first()

    if not lga:
        raise HTTPException(status_code=404, detail="LGA not found")

    response = LGAWithGeometry.model_validate(lga)

    # Convert PostGIS geometry to GeoJSON
    if lga.geometry is not None:
        try:
            response.geometry = mapping(to_shape(lga.geometry))
        except Exception:
            response.geometry = None

    return response


@router.get("/{lga_id}/risk-scores", response_model=List[RiskScoreResponse])
@limiter.limit("60/minute")
def get_lga_risk_scores(
    request: Request,
    lga_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(30, ge=1, le=365, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Get risk score history for an LGA with pagination."""
    # Verify LGA exists
    lga = db.query(LGA).filter(LGA.id == lga_id).first()
    if not lga:
        raise HTTPException(status_code=404, detail="LGA not found")

    query = db.query(RiskScore).filter(RiskScore.lga_id == lga_id)

    if start_date:
        query = query.filter(RiskScore.score_date >= start_date)
    if end_date:
        query = query.filter(RiskScore.score_date <= end_date)

    scores = query.order_by(RiskScore.score_date.desc()).offset(skip).limit(limit).all()

    return scores


@router.get("/{lga_id}/cases", response_model=List[dict])
@limiter.limit("60/minute")
def get_lga_cases(
    request: Request,
    lga_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Get case reports for an LGA with pagination."""
    # Verify LGA exists
    lga = db.query(LGA).filter(LGA.id == lga_id).first()
    if not lga:
        raise HTTPException(status_code=404, detail="LGA not found")

    query = db.query(CaseReport).filter(CaseReport.lga_id == lga_id)

    if start_date:
        query = query.filter(CaseReport.report_date >= start_date)
    if end_date:
        query = query.filter(CaseReport.report_date <= end_date)

    cases = query.order_by(CaseReport.report_date.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": c.id,
            "date": c.report_date.isoformat(),
            "new_cases": c.new_cases,
            "deaths": c.deaths,
            "suspected_cases": c.suspected_cases,
            "confirmed_cases": c.confirmed_cases,
            "cfr": c.cfr
        }
        for c in cases
    ]
