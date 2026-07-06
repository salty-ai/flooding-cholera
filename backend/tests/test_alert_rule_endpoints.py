from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_rules():
    resp = client.get("/api/alerts/rules")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_alerts_export_csv():
    resp = client.get("/api/alerts/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
