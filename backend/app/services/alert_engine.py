# backend/app/services/alert_engine.py
"""Rule-based alert engine. Run daily by APScheduler after risk recompute."""
import logging
from datetime import date, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import AlertRule, Alert, RiskScore, FloodEvent, CaseReport, LGA

logger = logging.getLogger(__name__)

_OPS = {
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
}


def _applies(operator: str, threshold: float, value: float) -> bool:
    fn = _OPS.get(operator)
    if fn is None:
        return False
    return fn(value, threshold)


_SEVERITY_TO_LEVEL = {"info": "green", "warning": "yellow", "critical": "red"}


def _level_for_alert(rule: AlertRule, value: float) -> str:
    """Map a rule metric + value to a green/yellow/red alert level."""
    if rule.metric == "risk_score":
        level = RiskScore.get_level_from_score(value)
        return level.value if hasattr(level, "value") else str(level)
    return _SEVERITY_TO_LEVEL.get(rule.severity, "yellow")


def _window_start(rule: AlertRule, as_of: date) -> Optional[date]:
    if rule.window_days and rule.window_days > 0:
        return as_of - timedelta(days=rule.window_days)
    return None


def _metric_value(db: Session, rule: AlertRule, lga_id: int, as_of: date) -> Optional[float]:
    start = _window_start(rule, as_of)
    if rule.metric == "risk_score":
        q = db.query(RiskScore).filter(RiskScore.lga_id == lga_id, RiskScore.score_date <= as_of)
        if start:
            q = q.filter(RiskScore.score_date >= start)
        rs = q.order_by(RiskScore.score_date.desc()).first()
        return rs.score if rs else None
    if rule.metric == "flood_event_count":
        q = db.query(func.count(FloodEvent.id)).filter(FloodEvent.lga_id == lga_id, FloodEvent.start_date <= as_of)
        if start:
            q = q.filter(FloodEvent.start_date >= start)
        return float(q.scalar() or 0)
    if rule.metric == "new_cases":
        q = db.query(func.sum(CaseReport.new_cases)).filter(CaseReport.lga_id == lga_id, CaseReport.report_date <= as_of)
        if start:
            q = q.filter(CaseReport.report_date >= start)
        return float(q.scalar() or 0)
    if rule.metric == "cfr":
        q = db.query(func.sum(CaseReport.deaths), func.sum(CaseReport.new_cases)).filter(
            CaseReport.lga_id == lga_id, CaseReport.report_date <= as_of)
        if start:
            q = q.filter(CaseReport.report_date >= start)
        d, c = q.first()
        if not c:
            return None
        return float(d or 0) / float(c)
    return None


def evaluate_rule(db: Session, rule: AlertRule, as_of: date) -> List[Alert]:
    """Evaluate a rule for all LGAs; return new deduped alerts (not yet committed)."""
    new_alerts: List[Alert] = []
    lgas = db.query(LGA).all()
    # Active alerts for dedup: (rule_id, lga_id) -> active
    active = {
        (a.rule_id, a.lga_id)
        for a in db.query(Alert).filter(
            Alert.rule_id == rule.id, Alert.is_active == True
        ).all()
    }
    for lga in lgas:
        val = _metric_value(db, rule, lga.id, as_of)
        if val is None:
            continue
        if not _applies(rule.operator, rule.threshold, val):
            continue
        if (rule.id, lga.id) in active:
            continue
        new_alerts.append(Alert(
            rule_id=rule.id,
            lga_id=lga.id,
            type=rule.metric,
            title=rule.name,
            severity=rule.severity,
            triggered_value=float(val),
            level=_level_for_alert(rule, val),
            message=f"{rule.name}: {rule.metric}={val:.3f} {rule.operator} {rule.threshold}",
            is_active=True,
        ))
    return new_alerts


def run_alert_engine(db: Session, as_of: date = None) -> int:
    as_of = as_of or date.today()
    rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()
    fired = 0
    for rule in rules:
        try:
            alerts = evaluate_rule(db, rule, as_of)
            for a in alerts:
                db.add(a)
            fired += len(alerts)
        except Exception as e:
            logger.error(f"Rule {rule.name} failed: {e}")
    db.commit()
    logger.info(f"Alert engine fired {fired} new alerts")
    return fired
