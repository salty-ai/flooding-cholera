"""Tests for v2.0 fields on the risk-scores endpoint."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)  # noqa: S101


def test_risk_scores_return_v2_fields():
    response = client.get("/api/analytics/risk-scores", params={"limit": 5})
    assert response.status_code == 200
    scores = response.json()
    for s in scores:
        for key in (
            "flood_event_score",
            "recent_flood_events",
            "vulnerability_score",
            "algorithm_version",
        ):
            assert key in s, f"missing v2 field: {key}"
