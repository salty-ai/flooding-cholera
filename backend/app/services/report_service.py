"""Weekly/monthly surveillance report assembly + PDF/CSV rendering."""
import io
import csv
import logging
from datetime import date, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import LGA, CaseReport, RiskScore, FloodEvent, Alert

logger = logging.getLogger(__name__)


def build_surveillance_report(
    db: Session,
    period: str,                # "weekly" | "monthly"
    scope: Dict[str, Any],      # {"level": "national"|"state"|"lga", ...}
    from_date: date,
    to_date: date,
) -> Dict[str, Any]:
    scope_level = scope.get("level")
    scope_lga_id = scope.get("lga_id")
    scope_state = scope.get("state")

    def _apply_scope(q, lga_col, lga_joined=False):
        """Apply scope filter to *q*. lga_col is the FK to lgas.id."""
        if scope_level == "lga" and scope_lga_id:
            return q.filter(lga_col == scope_lga_id)
        if scope_level == "state" and scope_state:
            if not lga_joined:
                q = q.join(LGA, LGA.id == lga_col)
            return q.filter(LGA.state == scope_state)
        return q

    # Totals
    cq = db.query(func.sum(CaseReport.new_cases), func.sum(CaseReport.deaths)).filter(
        CaseReport.report_date >= from_date, CaseReport.report_date <= to_date)
    cq = _apply_scope(cq, CaseReport.lga_id)
    cases, deaths = cq.first()
    cases = int(cases or 0); deaths = int(deaths or 0)
    cfr = (deaths / cases) if cases else 0.0

    # Previous period delta
    span = (to_date - from_date).days + 1
    prev_from = from_date - timedelta(days=span)
    pq = db.query(func.sum(CaseReport.new_cases)).filter(
        CaseReport.report_date >= prev_from, CaseReport.report_date < from_date)
    pq = _apply_scope(pq, CaseReport.lga_id)
    prev_cases = int(pq.scalar() or 0)

    # Hotspots by cases
    hq = db.query(LGA.id, LGA.name, func.sum(CaseReport.new_cases).label("c")).join(
        CaseReport, CaseReport.lga_id == LGA.id).filter(
        CaseReport.report_date >= from_date, CaseReport.report_date <= to_date)
    hq = _apply_scope(hq, CaseReport.lga_id, lga_joined=True)
    hq = hq.group_by(LGA.id, LGA.name).order_by(func.sum(CaseReport.new_cases).desc()).limit(10)
    hotspots_by_cases = [{"lga_id": r.id, "lga_name": r.name, "cases": int(r.c or 0)} for r in hq.all()]

    # Hotspots by risk (latest score in window)
    rq = db.query(LGA.id, LGA.name, func.max(RiskScore.score).label("s")).join(
        RiskScore, RiskScore.lga_id == LGA.id).filter(
        RiskScore.score_date >= from_date, RiskScore.score_date <= to_date)
    rq = _apply_scope(rq, RiskScore.lga_id, lga_joined=True)
    rq = rq.group_by(LGA.id, LGA.name).order_by(func.max(RiskScore.score).desc()).limit(10)
    hotspots_by_risk = [{"lga_id": r.id, "lga_name": r.name, "max_risk": float(r.s or 0)} for r in rq.all()]

    # Flood summary
    fq = db.query(func.count(FloodEvent.id), func.coalesce(func.sum(FloodEvent.area_km2), 0.0)).filter(
        FloodEvent.start_date >= from_date, FloodEvent.start_date <= to_date)
    fq = _apply_scope(fq, FloodEvent.lga_id)
    fcount, farea = fq.first()
    flood_summary = {"event_count": int(fcount or 0), "total_area_km2": float(farea or 0)}

    # Alerts fired in period
    aq = db.query(Alert).filter(Alert.created_at >= from_date, Alert.created_at <= to_date + timedelta(days=1))
    aq = _apply_scope(aq, Alert.lga_id)
    alerts_fired = [{"id": a.id, "severity": a.severity, "message": a.message, "lga_id": a.lga_id} for a in aq.all()]

    # Risk distribution (latest per LGA in window)
    dist_q = db.query(RiskScore.level, func.count(RiskScore.lga_id.distinct())).filter(
        RiskScore.score_date >= from_date, RiskScore.score_date <= to_date)
    dist_q = _apply_scope(dist_q, RiskScore.lga_id)
    dist = {"green": 0, "yellow": 0, "red": 0}
    for r in dist_q.group_by(RiskScore.level).all():
        if r[0] in dist:
            dist[r[0]] = int(r[1])

    return {
        "period": period, "scope": scope, "from": from_date.isoformat(), "to": to_date.isoformat(),
        "totals": {"cases": cases, "deaths": deaths, "cfr": round(cfr, 4)},
        "previous": {"cases": prev_cases},
        "hotspots_by_cases": hotspots_by_cases,
        "hotspots_by_risk": hotspots_by_risk,
        "flood_summary": flood_summary,
        "alerts_fired": alerts_fired,
        "risk_distribution": dist,
    }


def render_report_pdf(report: Dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 20 * mm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, "Cholera Surveillance Report")
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Period: {report['period']}  {report['from']} → {report['to']}    Scope: {report['scope']}")
    y -= 8 * mm
    t = report["totals"]
    c.drawString(20 * mm, y, f"Cases: {t['cases']}   Deaths: {t['deaths']}   CFR: {t['cfr']:.1%}   (previous cases: {report['previous']['cases']})")
    y -= 8 * mm
    rd = report["risk_distribution"]
    c.drawString(20 * mm, y, f"Risk levels — Green: {rd.get('green',0)}  Yellow: {rd.get('yellow',0)}  Red: {rd.get('red',0)}")
    y -= 8 * mm
    fs = report["flood_summary"]
    c.drawString(20 * mm, y, f"Flood events: {fs.get('event_count', 0)}   Total area: {fs.get('total_area_km2', 0.0):.1f} km²")
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 12); c.drawString(20 * mm, y, "Top-10 hotspot LGAs (cases)"); y -= 6 * mm
    c.setFont("Helvetica", 9)
    for h in report["hotspots_by_cases"]:
        c.drawString(20 * mm, y, f"{h['lga_name']} — {h['cases']} cases"); y -= 5 * mm
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 12); c.drawString(20 * mm, y, "Top-10 LGAs by risk"); y -= 6 * mm
    c.setFont("Helvetica", 9)
    for h in report["hotspots_by_risk"]:
        c.drawString(20 * mm, y, f"{h['lga_name']} — {h['max_risk']:.3f}"); y -= 5 * mm
    y -= 4 * mm
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(20 * mm, y, "Correlation is a decision-support signal, not proof of causation. Risk algorithm v2.0.")
    c.showPage(); c.save()
    return buf.getvalue()


def render_report_csv(report: Dict[str, Any]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["section", "key", "value"])
    for k, v in report["totals"].items():
        w.writerow(["totals", k, v])
    w.writerow(["previous", "cases", report["previous"]["cases"]])
    for k, v in report["risk_distribution"].items():
        w.writerow(["risk_distribution", k, v])
    for k, v in report["flood_summary"].items():
        w.writerow(["flood_summary", k, v])
    w.writerow([])
    w.writerow(["hotspots_by_cases"])
    w.writerow(["lga_id", "lga_name", "cases"])
    for h in report["hotspots_by_cases"]:
        w.writerow([h["lga_id"], h["lga_name"], h["cases"]])
    w.writerow([])
    w.writerow(["hotspots_by_risk"])
    w.writerow(["lga_id", "lga_name", "max_risk"])
    for h in report["hotspots_by_risk"]:
        w.writerow([h["lga_id"], h["lga_name"], h["max_risk"]])
    w.writerow([])
    w.writerow(["alerts_fired"])
    w.writerow(["id", "severity", "lga_id", "message"])
    for a in report["alerts_fired"]:
        w.writerow([a["id"], a["severity"], a["lga_id"], a["message"]])
    return out.getvalue().encode("utf-8")
