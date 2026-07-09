"""Tests for the dashboard summary endpoint."""
from datetime import date
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)  # noqa: S101


def test_dashboard_summary_has_v2_fields():
    """GET /api/lgas/dashboard returns the new v2 fields."""
    response = client.get("/api/lgas/dashboard")
    assert response.status_code == 200
    body = response.json()
    for key in (
        "total_lgas", "total_cases", "total_deaths",
        "lgas_high_risk", "lgas_medium_risk", "lgas_low_risk",
        "avg_rainfall_7day", "last_updated",
        "active_alerts_count", "alert_level", "flood_events_count",
        "applied_window_start", "applied_window_end", "max_data_date",
    ):
        assert key in body, f"missing field: {key}"
