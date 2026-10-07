"""Flood events router — exposes Groundsource & NEMA flood disaster events."""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FloodEvent, LGA
from app.rate_limiter import limiter

router = APIRouter(prefix="/api/flood-events", tags=["flood-events"])


@router.get("", response_model=list[dict])
@limiter.limit("60/minute")
def list_flood_events(
    request: Request,
    lga_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List flood events with NEMA displacement and impact metrics."""
    q = db.query(FloodEvent, LGA.name.label("lga_db_name")).outerjoin(LGA, FloodEvent.lga_id == LGA.id)

    if lga_id is not None:
        q = q.filter(FloodEvent.lga_id == lga_id)
    if state is not None:
        q = q.filter(func.lower(FloodEvent.state_name) == state.lower().strip())
    if year is not None:
        q = q.filter(FloodEvent.year == year)
    if start_date is not None:
        q = q.filter(FloodEvent.end_date >= start_date)
    if end_date is not None:
        q = q.filter(FloodEvent.start_date <= end_date)

    rows = q.order_by(FloodEvent.year.desc(), FloodEvent.start_date.desc()).limit(limit).all()

    return [
        {
            "id": fe.id,
            "uuid": fe.uuid,
            "lga_id": fe.lga_id,
            "lga_name": fe.lga_name or lga_db_name,
            "state_name": fe.state_name,
            "year": fe.year,
            "disaster_type": fe.disaster_type,
            "start_date": fe.start_date.isoformat() if fe.start_date else None,
            "end_date": fe.end_date.isoformat() if fe.end_date else None,
            "duration_days": fe.duration_days,
            "area_km2": fe.area_km2,
            "affected_households": fe.affected_households,
            "affected_individuals": fe.affected_individuals,
            "displaced_households": fe.displaced_households,
            "displaced_individuals": fe.displaced_individuals,
            "injuries": fe.injuries,
            "data_source": fe.data_source,
            "created_at": fe.created_at.isoformat() if fe.created_at else None,
        }
        for fe, lga_db_name in rows
    ]


@router.get("/summary")
@limiter.limit("60/minute")
def get_flood_summary(
    request: Request,
    state: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Get aggregated NEMA disaster & displacement summary."""
    q = db.query(FloodEvent)

    if state:
        q = q.filter(func.lower(FloodEvent.state_name) == state.lower().strip())
    if year:
        q = q.filter(FloodEvent.year == year)

    events = q.all()

    total_affected = sum(fe.affected_individuals or 0 for fe in events)
    total_displaced = sum(fe.displaced_individuals or 0 for fe in events)
    total_injuries = sum(fe.injuries or 0 for fe in events)

    return {
        "total_events": len(events),
        "total_affected_individuals": total_affected,
        "total_displaced_individuals": total_displaced,
        "total_injuries": total_injuries,
    }
