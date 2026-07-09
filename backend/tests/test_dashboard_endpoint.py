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


def test_dashboard_explicit_date_window():
    """Explicit start/end dates are reflected in applied_window."""
    response = client.get(
        "/api/lgas/dashboard",
        params={"start_date": "2024-01-01", "end_date": "2024-12-31"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["applied_window_start"] == "2024-01-01"
    assert body["applied_window_end"] == "2024-12-31"


def test_dashboard_latest_available_default():
    """With no dates, applied_window_end == max_data_date (latest-available)."""
    response = client.get("/api/lgas/dashboard")
    assert response.status_code == 200
    body = response.json()
    # If there is any case data, the default window ends at max_data_date.
    if body["max_data_date"] is not None:
        assert body["applied_window_end"] == body["max_data_date"]
    else:
        # No data at all: window fields are null, counts are zero.
        assert body["applied_window_start"] is None
        assert body["total_cases"] == 0


def test_dashboard_rejects_bad_dates():
    """Invalid date strings return 422."""
    response = client.get(
        "/api/lgas/dashboard",
        params={"start_date": "not-a-date"},
    )
    assert response.status_code == 422


def test_dashboard_alert_and_flood_fields_are_integers():
    """active_alerts_count and flood_events_count are ints (>= 0)."""
    response = client.get("/api/lgas/dashboard")
    body = response.json()
    assert isinstance(body["active_alerts_count"], int)
    assert body["active_alerts_count"] >= 0
    assert isinstance(body["flood_events_count"], int)
    assert body["flood_events_count"] >= 0
    assert body["alert_level"] in ("green", "yellow", "red")


def test_dashboard_alert_count_matches_db():
    from app.models import Alert
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        expected = db.query(Alert).filter(Alert.is_active == True).count()
    finally:
        db.close()
    body = client.get("/api/lgas/dashboard").json()
    assert body["active_alerts_count"] == expected
