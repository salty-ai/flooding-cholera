from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_correlation_endpoint_shape():
    resp = client.get("/api/analytics/correlation", params={"from_year": 2020, "to_year": 2025})
    assert resp.status_code == 200
    data = resp.json()
    assert "lags" in data
    assert "caveat" in data
    assert isinstance(data["lags"], list)
