"""Health facility endpoints serving 46,146 FMOH registry records."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

from app.database import get_db
from app.models import HealthFacility, LGA
from app.rate_limiter import limiter

router = APIRouter(prefix="/api/facilities", tags=["Facilities"])
logger = logging.getLogger(__name__)


@router.get("/")
@limiter.limit("120/minute")
def get_facilities(
    request: Request,
    state: Optional[str] = Query(None, description="Filter by state name"),
    lga_id: Optional[int] = Query(None, description="Filter by LGA ID"),
    lga_name: Optional[str] = Query(None, description="Filter by LGA name"),
    type: Optional[str] = Query(None, description="Filter by facility type (Primary, Secondary, Tertiary)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    functional_status: Optional[str] = Query(None, description="Filter by functional status"),
    search: Optional[str] = Query(None, description="Search facility name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Get health facilities with multi-criteria filtering and pagination."""
    query = db.query(HealthFacility)

    if state:
        query = query.filter(func.lower(HealthFacility.state_name) == state.lower().strip())
    if lga_id:
        query = query.filter(HealthFacility.lga_id == lga_id)
    if lga_name:
        query = query.filter(func.lower(HealthFacility.lga_name) == lga_name.lower().strip())
    if type:
        query = query.filter(func.lower(HealthFacility.type) == type.lower().strip())
    if category:
        query = query.filter(func.lower(HealthFacility.category) == category.lower().strip())
    if functional_status:
        query = query.filter(func.lower(HealthFacility.functional_status) == functional_status.lower().strip())
    if search:
        query = query.filter(HealthFacility.name.ilike(f"%{search.strip()}%"))

    total = query.count()
    facilities = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "facilities": [
            {
                "id": fac.id,
                "global_id": fac.global_id,
                "name": fac.name,
                "type": fac.type,
                "category": fac.category,
                "functional_status": fac.functional_status,
                "state_name": fac.state_name,
                "lga_name": fac.lga_name,
                "lga_id": fac.lga_id,
                "latitude": fac.latitude,
                "longitude": fac.longitude,
            }
            for fac in facilities
        ],
    }


@router.get("/stats")
@limiter.limit("60/minute")
def get_facility_stats(
    request: Request,
    state: Optional[str] = Query(None),
    lga_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Get national and regional health facility statistics and functional breakdowns."""
    query = db.query(HealthFacility)
    if state:
        query = query.filter(func.lower(HealthFacility.state_name) == state.lower().strip())
    if lga_id:
        query = query.filter(HealthFacility.lga_id == lga_id)

    total = query.count()

    # Functional status breakdown
    status_query = (
        db.query(HealthFacility.functional_status, func.count(HealthFacility.id))
    )
    if state:
        status_query = status_query.filter(func.lower(HealthFacility.state_name) == state.lower().strip())
    if lga_id:
        status_query = status_query.filter(HealthFacility.lga_id == lga_id)
    status_counts = dict(status_query.group_by(HealthFacility.functional_status).all())

    # Type breakdown
    type_query = (
        db.query(HealthFacility.type, func.count(HealthFacility.id))
    )
    if state:
        type_query = type_query.filter(func.lower(HealthFacility.state_name) == state.lower().strip())
    if lga_id:
        type_query = type_query.filter(HealthFacility.lga_id == lga_id)
    type_counts = dict(type_query.group_by(HealthFacility.type).all())

    functional_count = status_counts.get("Functional", 0)
    functional_rate = round((functional_count / total * 100), 1) if total > 0 else 0.0

    return {
        "total_facilities": total,
        "functional_rate_pct": functional_rate,
        "functional_status_breakdown": status_counts,
        "type_breakdown": type_counts,
    }


@router.get("/geojson")
@limiter.limit("60/minute")
def get_facilities_geojson(
    request: Request,
    state: Optional[str] = Query(None),
    lga_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
    functional_status: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=46146),
    db: Session = Depends(get_db),
):
    """Get health facilities as GeoJSON FeatureCollection with optional filters."""
    query = db.query(HealthFacility)

    if state:
        query = query.filter(func.lower(HealthFacility.state_name) == state.lower().strip())
    if lga_id:
        query = query.filter(HealthFacility.lga_id == lga_id)
    if type:
        query = query.filter(func.lower(HealthFacility.type) == type.lower().strip())
    if functional_status:
        query = query.filter(func.lower(HealthFacility.functional_status) == functional_status.lower().strip())

    facilities = query.limit(limit).all()

    features = []
    for fac in facilities:
        if fac.latitude is None or fac.longitude is None:
            continue

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [fac.longitude, fac.latitude],
                },
                "properties": {
                    "id": fac.id,
                    "name": fac.name,
                    "type": fac.type,
                    "category": fac.category,
                    "functional_status": fac.functional_status,
                    "state_name": fac.state_name,
                    "lga_name": fac.lga_name,
                    "lga_id": fac.lga_id,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}
