"""Alert endpoints for surveillance system notifications."""
import csv
import io
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database import get_db
from app.models import Alert, AlertRule, LGA
from app.schemas import (
    AlertResponse,
    AlertWithLGA,
    AlertListResponse,
    AlertAcknowledge,
    AlertRuleCreate,
    AlertRuleResponse,
)
from app.rate_limiter import limiter

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("", response_model=AlertListResponse)
@limiter.limit("60/minute")
def list_alerts(
    request: Request,
    lga_id: Optional[int] = Query(None, description="Filter by LGA ID"),
    severity: Optional[str] = Query(None, pattern="^(info|warning|critical)$", description="Filter by severity"),
    level: Optional[str] = Query(None, pattern="^(green|yellow|red)$", description="Filter by level"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    is_acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    List alerts with optional filters.

    Filters:
    - lga_id: Filter by specific LGA
    - severity: info, warning, critical
    - level: green, yellow, red
    - alert_type: Type of alert (flood_warning, case_spike, etc.)
    - is_active: Show only active/inactive alerts
    - is_acknowledged: Filter by acknowledgment status
    """
    query = db.query(Alert, LGA.name.label("lga_name")).outerjoin(
        LGA, Alert.lga_id == LGA.id
    )

    # Apply filters
    filters = []

    if lga_id is not None:
        filters.append(Alert.lga_id == lga_id)

    if severity:
        filters.append(Alert.severity == severity)

    if level:
        filters.append(Alert.level == level)

    if alert_type:
        filters.append(Alert.type == alert_type)

    if is_active is not None:
        filters.append(Alert.is_active == is_active)

    if is_acknowledged is not None:
        if is_acknowledged:
            filters.append(Alert.acknowledged_at.isnot(None))
        else:
            filters.append(Alert.acknowledged_at.is_(None))

    if filters:
        query = query.filter(and_(*filters))

    # Get total count before pagination
    total = query.count()

    # Apply pagination and ordering
    results = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()

    # Convert to response format
    alerts = []
    for alert, lga_name in results:
        alert_dict = {
            "id": alert.id,
            "lga_id": alert.lga_id,
            "level": alert.level,
            "severity": alert.severity,
            "type": alert.type,
            "title": alert.title,
            "message": alert.message,
            "triggered_by": alert.triggered_by,
            "created_at": alert.created_at,
            "acknowledged_at": alert.acknowledged_at,
            "acknowledged_by": alert.acknowledged_by,
            "resolved_at": alert.resolved_at,
            "is_active": alert.is_active,
            "lga_name": lga_name
        }
        alerts.append(AlertWithLGA(**alert_dict))

    return AlertListResponse(
        total=total,
        alerts=alerts,
        skip=skip,
        limit=limit
    )


@router.get("/rules", response_model=list[AlertRuleResponse])
@limiter.limit("60/minute")
def list_rules(request: Request, db: Session = Depends(get_db)):
    return db.query(AlertRule).order_by(AlertRule.id).all()


@router.post("/rules", response_model=AlertRuleResponse, status_code=201)
@limiter.limit("20/minute")
def create_rule(request: Request, body: AlertRuleCreate, db: Session = Depends(get_db)):
    rule = AlertRule(**body.model_dump())
    db.add(rule); db.commit(); db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
@limiter.limit("20/minute")
def update_rule(request: Request, rule_id: int, body: AlertRuleCreate,
                db: Session = Depends(get_db)):
    rule = db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    for k, v in body.model_dump().items():
        setattr(rule, k, v)
    db.commit(); db.refresh(rule)
    return rule


@router.get("/export")
@limiter.limit("20/minute")
def export_alerts(request: Request, db: Session = Depends(get_db)):
    rows = db.query(Alert, LGA.name).outerjoin(LGA, Alert.lga_id == LGA.id).all()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["id", "rule_id", "lga_id", "lga_name", "severity", "level",
                "triggered_value", "message", "is_active", "is_acknowledged", "created_at"])
    for a, name in rows:
        w.writerow([a.id, a.rule_id, a.lga_id, name, a.severity, a.level,
                    a.triggered_value, a.message, a.is_active, a.is_acknowledged, a.created_at])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=alerts.csv"})


@router.get("/{alert_id}", response_model=AlertWithLGA)
@limiter.limit("60/minute")
def get_alert(
    request: Request,
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Get a single alert by ID."""
    result = db.query(Alert, LGA.name.label("lga_name")).outerjoin(
        LGA, Alert.lga_id == LGA.id
    ).filter(Alert.id == alert_id).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found"
        )

    alert, lga_name = result

    alert_dict = {
        "id": alert.id,
        "lga_id": alert.lga_id,
        "level": alert.level,
        "severity": alert.severity,
        "type": alert.type,
        "title": alert.title,
        "message": alert.message,
        "triggered_by": alert.triggered_by,
        "created_at": alert.created_at,
        "acknowledged_at": alert.acknowledged_at,
        "acknowledged_by": alert.acknowledged_by,
        "resolved_at": alert.resolved_at,
        "is_active": alert.is_active,
        "lga_name": lga_name
    }

    return AlertWithLGA(**alert_dict)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
@limiter.limit("30/minute")
def acknowledge_alert(
    request: Request,
    alert_id: int,
    acknowledge_data: AlertAcknowledge,
    db: Session = Depends(get_db)
):
    """
    Mark an alert as acknowledged.

    This indicates that the alert has been seen and reviewed by a user.
    An alert can only be acknowledged once.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found"
        )

    if alert.acknowledged_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert has already been acknowledged"
        )

    # Acknowledge the alert
    alert.acknowledge(user_id=acknowledge_data.user_id)
    db.commit()
    db.refresh(alert)

    return alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
@limiter.limit("30/minute")
def resolve_alert(
    request: Request,
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark an alert as resolved.

    This indicates that the issue has been addressed and the alert
    can be deactivated. Resolved alerts are no longer active.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found"
        )

    if alert.resolved_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert has already been resolved"
        )

    # Resolve the alert
    alert.resolve()
    db.commit()
    db.refresh(alert)

    return alert


@router.get("/stats/summary")
@limiter.limit("60/minute")
def get_alert_stats(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get summary statistics about alerts.

    Returns counts of active alerts by severity and level.
    """
    # Count active alerts by severity
    active_alerts = db.query(Alert).filter(Alert.is_active == True).all()

    stats = {
        "total_active": len(active_alerts),
        "by_severity": {
            "critical": sum(1 for a in active_alerts if a.severity == "critical"),
            "warning": sum(1 for a in active_alerts if a.severity == "warning"),
            "info": sum(1 for a in active_alerts if a.severity == "info")
        },
        "by_level": {
            "red": sum(1 for a in active_alerts if a.level == "red"),
            "yellow": sum(1 for a in active_alerts if a.level == "yellow"),
            "green": sum(1 for a in active_alerts if a.level == "green")
        },
        "unacknowledged": sum(1 for a in active_alerts if not a.acknowledged_at),
        "acknowledged": sum(1 for a in active_alerts if a.acknowledged_at),
        "by_type": {}
    }

    # Group by type
    for alert in active_alerts:
        alert_type = alert.type
        if alert_type not in stats["by_type"]:
            stats["by_type"][alert_type] = 0
        stats["by_type"][alert_type] += 1

    return stats


@router.patch("/{alert_id}", response_model=AlertResponse)
@limiter.limit("30/minute")
def patch_acknowledge_alert(
    request: Request,
    alert_id: int,
    acknowledge_data: AlertAcknowledge,
    db: Session = Depends(get_db),
):
    """Acknowledge an alert via PATCH and deactivate it."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found",
        )
    if alert.acknowledged_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert has already been acknowledged",
        )
    alert.acknowledge(user_id=acknowledge_data.user_id)
    alert.is_active = False
    db.commit()
    db.refresh(alert)
    return alert
