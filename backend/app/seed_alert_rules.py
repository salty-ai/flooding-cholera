# backend/app/seed_alert_rules.py
"""Seed default alert rules."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal
from app.models import AlertRule

DEFAULTS = [
    dict(name="High risk score", metric="risk_score", operator=">=", threshold=0.6,
         window_days=0, severity="critical",
         description="Latest risk score at or above 0.6"),
    dict(name="Recent flooding", metric="flood_event_count", operator=">=", threshold=1,
         window_days=14, severity="warning",
         description="One or more flood events in the last 14 days"),
    dict(name="Case surge", metric="new_cases", operator=">=", threshold=20,
         window_days=14, severity="critical",
         description="20+ new cholera cases in the last 14 days"),
    dict(name="High case fatality", metric="cfr", operator=">=", threshold=0.05,
         window_days=14, severity="warning",
         description="Case fatality rate >= 5% over 14 days"),
]


def main():
    db = SessionLocal()
    try:
        for d in DEFAULTS:
            existing = db.query(AlertRule).filter(AlertRule.name == d["name"]).first()
            if existing:
                for k, v in d.items():
                    setattr(existing, k, v)
                existing.enabled = True
            else:
                db.add(AlertRule(enabled=True, **d))
        db.commit()
        print(f"Seeded {len(DEFAULTS)} alert rules")
    finally:
        db.close()


if __name__ == "__main__":
    main()
