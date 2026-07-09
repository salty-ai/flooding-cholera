"""Flood events router — exposes Groundsource flood events."""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Request
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
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List recent flood events, optionally filtered by LGA and date window."""
    q = db.query(FloodEvent, LGA.name).outerjoin(LGA, FloodEvent.lga_id == LGA.id)
    if lga_id is not None:
        q = q.filter(FloodEvent.lga_id == lga_id)
    if start_date is not None:
        q = q.filter(FloodEvent.end_date >= start_date)
    if end_date is not None:
        q = q.filter(FloodEvent.start_date <= end_date)
    rows = q.order_by(FloodEvent.start_date.desc()).limit(limit).all()

    return [
        {
            "id": fe.id,
            "uuid": fe.uuid,
            "lga_id": fe.lga_id,
            "lga_name": lga_name,
            "start_date": fe.start_date.isoformat() if fe.start_date else None,
            "end_date": fe.end_date.isoformat() if fe.end_date else None,
            "duration_days": fe.duration_days,
            "area_km2": fe.area_km2,
            "created_at": fe.created_at.isoformat() if fe.created_at else None,
        }
        for fe, lga_name in rows
    ]
