# backend/tests/test_reports_endpoint.py
from datetime import date
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_report_json():
    resp = client.get("/api/reports/surveillance", params={"from": "2024-06-01", "to": "2024-06-30"})
    assert resp.status_code == 200
    data = resp.json()
    assert "totals" in data and "hotspots_by_cases" in data

def test_report_pdf():
    resp = client.get("/api/reports/surveillance/export", params={"from": "2024-06-01", "to": "2024-06-30", "format": "pdf"})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
