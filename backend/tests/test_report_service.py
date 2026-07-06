from app.services.report_service import render_report_pdf, render_report_csv

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
