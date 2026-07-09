"""Tests for the flood-events endpoint."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)  # noqa: S101


def test_flood_events_list_shape():
    response = client.get("/api/flood-events", params={"limit": 5})
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    for e in events:
        for key in (
            "id", "uuid", "lga_id", "lga_name",
            "start_date", "end_date", "duration_days", "area_km2",
        ):
            assert key in e, f"missing field: {key}"


def test_flood_events_limit_cap():
    response = client.get("/api/flood-events", params={"limit": 500})
    assert response.status_code == 422  # limit max is 200


def test_flood_events_lga_filter():
    response = client.get("/api/flood-events", params={"lga_id": 1, "limit": 5})
    assert response.status_code == 200
    for e in response.json():
        assert e["lga_id"] == 1
