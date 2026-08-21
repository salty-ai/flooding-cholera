#!/usr/bin/env python3
"""Seed realistic active alerts for publication screenshots (idempotent)."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import SessionLocal  # noqa: E402
from app.models import Alert, LGA  # noqa: E402


def find_lga(db, name: str) -> LGA | None:
    return (
        db.query(LGA)
        .filter(LGA.name.ilike(name))
        .order_by(LGA.id.asc())
        .first()
    )


def main() -> None:
    db = SessionLocal()
    try:
        targets = [
            ("Yakurr", "Cross River"),
            ("Biase", "Cross River"),
            ("Calabar Municipal", "Cross River"),
            ("Yenegoa", "Bayelsa"),
            ("Zuru", "Kebbi"),
            ("Maiduguri", "Borno"),
            ("Lagos Island", "Lagos"),
            ("Kano Municipal", "Kano"),
        ]
        lgas = {}
        for name, _state in targets:
            row = find_lga(db, name)
            if row:
                lgas[name] = row
                print(f"LGA ok: {name} id={row.id}")
            else:
                print(f"LGA missing: {name}")

        # Fallback: pick any LGA if named ones missing
        if len(lgas) < 4:
            for row in db.query(LGA).order_by(LGA.id.asc()).limit(12).all():
                lgas[row.name] = row

        now = datetime.utcnow()
        specs = [
            {
                "name": "Yakurr",
                "level": "red",
                "severity": "critical",
                "type": "case_spike",
                "title": "Critical case spike — Yakurr LGA (Cross River pilot)",
                "message": (
                    "14-day case count rose above the local threshold during the Cross River "
                    "2021 sentinel window. Prioritize ORS stock check, active case search, and "
                    "water-point inspection in Ugep ward clusters."
                ),
                "triggered_value": 53.0,
                "hours_ago": 6,
                "triggered_by": {
                    "metric": "cases_14d",
                    "threshold": 20,
                    "observed": 53,
                    "source": "crossriver_2021_pilot_linelist",
                    "state": "Cross River",
                },
            },
            {
                "name": "Biase",
                "level": "yellow",
                "severity": "warning",
                "type": "flood_warning",
                "title": "Flood persistence warning — Biase LGA",
                "message": (
                    "Satellite-detected surface-water anomalies remain elevated for >7 days. "
                    "Exploratory lag signal suggests heightened environmental suitability; "
                    "increase WASH messaging and clinic readiness."
                ),
                "triggered_value": 0.71,
                "hours_ago": 14,
                "triggered_by": {
                    "metric": "ndwi_anomaly",
                    "threshold": 0.55,
                    "observed": 0.71,
                    "lag_note": "exploratory_only",
                    "state": "Cross River",
                },
            },
            {
                "name": "Yenegoa",
                "level": "red",
                "severity": "critical",
                "type": "flood_warning",
                "title": "Critical flood exposure — Yenegoa LGA (Bayelsa)",
                "message": (
                    "NEMA/Groundsource flood footprint indicates 6,300+ affected individuals and "
                    "extended inundation. National dashboard flags multi-factor vulnerability; "
                    "coordinate state emergency ops and cholera kit prepositioning."
                ),
                "triggered_value": 6321.0,
                "hours_ago": 9,
                "triggered_by": {
                    "metric": "affected_individuals",
                    "observed": 6321,
                    "area_km2": 107.2,
                    "source": "GROUNDSOURCE_NEMA",
                    "state": "Bayelsa",
                },
            },
            {
                "name": "Zuru",
                "level": "yellow",
                "severity": "warning",
                "type": "rainfall_alert",
                "title": "Rainfall threshold exceeded — Zuru LGA (Kebbi)",
                "message": (
                    "Seven-day cumulative rainfall exceeded the configured warning threshold. "
                    "Monitor drainage choke points and community water sources for contamination risk."
                ),
                "triggered_value": 96.4,
                "hours_ago": 20,
                "triggered_by": {
                    "metric": "rainfall_7d_mm",
                    "threshold": 75.0,
                    "observed": 96.4,
                    "source": "GPM-IMERG",
                    "state": "Kebbi",
                },
            },
            {
                "name": "Maiduguri",
                "level": "yellow",
                "severity": "warning",
                "type": "risk_change",
                "title": "Risk score elevated — Maiduguri LGA",
                "message": (
                    "Composite heuristic risk score crossed the yellow band after environmental "
                    "and facility-functionality inputs updated. Review LGA report and alert rules."
                ),
                "triggered_value": 0.62,
                "hours_ago": 30,
                "triggered_by": {
                    "metric": "risk_score_v2",
                    "band": "yellow",
                    "observed": 0.62,
                    "method": "heuristic_mcda",
                    "state": "Borno",
                },
            },
            {
                "name": "Calabar Municipal",
                "level": "green",
                "severity": "info",
                "type": "high_risk",
                "title": "Surveillance notice — Calabar Municipal",
                "message": (
                    "Pilot line-list includes culture-referenced cases in Calabar Municipal. "
                    "Maintain routine reporting cadence; no active flood threshold breach."
                ),
                "triggered_value": 6.0,
                "hours_ago": 48,
                "triggered_by": {
                    "metric": "pilot_cases",
                    "observed": 6,
                    "source": "crossriver_2021_pilot_linelist",
                    "state": "Cross River",
                },
                "ack_hours_ago": 40,
            },
            {
                "name": "Lagos Island",
                "level": "yellow",
                "severity": "warning",
                "type": "case_spike",
                "title": "Case acceleration watch — Lagos Island",
                "message": (
                    "National situational awareness layer flags rising recent case counts relative "
                    "to the trailing baseline. Verify state SitRep alignment before escalation."
                ),
                "triggered_value": 28.0,
                "hours_ago": 11,
                "triggered_by": {
                    "metric": "cases_14d",
                    "threshold": 15,
                    "observed": 28,
                    "state": "Lagos",
                },
            },
            {
                "name": "Kano Municipal",
                "level": "red",
                "severity": "critical",
                "type": "case_spike",
                "title": "Critical outbreak pressure — Kano Municipal",
                "message": (
                    "High recent caseload with concurrent environmental stress indicators. "
                    "Recommend multi-agency huddle: state EOC, WASH leads, and logistics for ORS/IV fluids."
                ),
                "triggered_value": 112.0,
                "hours_ago": 4,
                "triggered_by": {
                    "metric": "cases_14d",
                    "threshold": 40,
                    "observed": 112,
                    "state": "Kano",
                },
            },
        ]

        created = 0
        refreshed = 0
        for spec in specs:
            lga = lgas.get(spec["name"]) or next(iter(lgas.values()), None)
            if lga is None:
                continue
            existing = (
                db.query(Alert)
                .filter(Alert.title == spec["title"])
                .first()
            )
            payload = {
                "lga_id": lga.id,
                "level": spec["level"],
                "severity": spec["severity"],
                "type": spec["type"],
                "title": spec["title"],
                "message": spec["message"],
                "triggered_value": spec.get("triggered_value"),
                "triggered_by": spec.get("triggered_by"),
                "created_at": now - timedelta(hours=spec.get("hours_ago", 12)),
                "is_active": True,
                "resolved_at": None,
            }
            if "ack_hours_ago" in spec:
                payload["acknowledged_at"] = now - timedelta(hours=spec["ack_hours_ago"])
                payload["acknowledged_by"] = 1
            else:
                payload["acknowledged_at"] = None
                payload["acknowledged_by"] = None

            if existing:
                for k, v in payload.items():
                    setattr(existing, k, v)
                refreshed += 1
            else:
                db.add(Alert(**payload))
                created += 1

        db.commit()
        active = db.query(Alert).filter(Alert.is_active.is_(True)).count()
        print(f"created={created} refreshed={refreshed} active_total={active}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
