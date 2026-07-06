import uuid as _uuid
from datetime import date, datetime
from app.database import SessionLocal
from app.models import LGA, CaseReport, RiskScore, FloodEvent, Alert
from app.services.report_service import build_surveillance_report, render_report_pdf, render_report_csv


def test_pdf_renders():
    report = {"period": "monthly", "scope": "national", "from": "2024-06-01",
              "to": "2024-06-30", "totals": {"cases": 100, "deaths": 5, "cfr": 0.05},
              "hotspots_by_cases": [], "hotspots_by_risk": [], "flood_summary": {},
              "alerts_fired": [], "risk_distribution": {"green": 700, "yellow": 60, "red": 14},
              "previous": {"cases": 80}}
    pdf = render_report_pdf(report)
    assert pdf.startswith(b"%PDF")
    csv = render_report_csv(report)
    assert b"cases" in csv


def test_report_scope_lga_filters_all_queries():
    """With scope level=lga, every report query must be scoped to that LGA."""
    db = SessionLocal()
    try:
        tag = _uuid.uuid4().hex[:8]
        lga_a = LGA(name=f"TestScopeA_{tag}", code=f"TSA_{tag}",
                    state=f"TestState_{tag}",
                    water_coverage_pct=50, sanitation_coverage_pct=50)
        lga_b = LGA(name=f"TestScopeB_{tag}", code=f"TSB_{tag}",
                    state=f"TestState_{tag}",
                    water_coverage_pct=50, sanitation_coverage_pct=50)
        db.add_all([lga_a, lga_b])
        db.flush()

        d = date(2024, 6, 3)
        db.add_all([
            CaseReport(lga_id=lga_a.id, report_date=d, new_cases=50, deaths=5),
            CaseReport(lga_id=lga_b.id, report_date=d, new_cases=10, deaths=1),
        ])
        db.add_all([
            RiskScore(lga_id=lga_a.id, score_date=d, score=0.9, level="red"),
            RiskScore(lga_id=lga_b.id, score_date=d, score=0.2, level="green"),
        ])
        db.add_all([
            FloodEvent(uuid=f"fe_a_{tag}", lga_id=lga_a.id, start_date=d,
                       end_date=d, data_source="test"),
            FloodEvent(uuid=f"fe_b_{tag}", lga_id=lga_b.id, start_date=d,
                       end_date=d, data_source="test"),
        ])
        db.add_all([
            Alert(lga_id=lga_a.id, level="red", severity="critical", type="flood",
                  title="A", message="A", created_at=datetime(2024, 6, 3, 12, 0, 0),
                  is_active=True),
            Alert(lga_id=lga_b.id, level="green", severity="info", type="flood",
                  title="B", message="B", created_at=datetime(2024, 6, 3, 12, 0, 0),
                  is_active=True),
        ])
        db.flush()

        report = build_surveillance_report(
            db, "weekly", {"level": "lga", "lga_id": lga_a.id},
            date(2024, 6, 1), date(2024, 6, 7))

        # Totals: only lga_a's cases
        assert report["totals"]["cases"] == 50
        assert report["totals"]["deaths"] == 5

        # Hotspots by cases: only lga_a
        hsc = report["hotspots_by_cases"]
        assert all(h["lga_id"] == lga_a.id for h in hsc), \
            f"Expected only lga_a ({lga_a.id}), got {[h['lga_id'] for h in hsc]}"
        assert len(hsc) == 1

        # Hotspots by risk: only lga_a
        hsr = report["hotspots_by_risk"]
        assert all(h["lga_id"] == lga_a.id for h in hsr)
        assert len(hsr) == 1

        # Flood summary: only lga_a's event
        assert report["flood_summary"]["event_count"] == 1

        # Alerts fired: only lga_a's alert
        af = report["alerts_fired"]
        assert all(a["lga_id"] == lga_a.id for a in af)
        assert len(af) == 1

        # Risk distribution: only lga_a's level
        assert report["risk_distribution"]["red"] == 1
        assert report["risk_distribution"]["green"] == 0
    finally:
        db.rollback()
        db.close()
