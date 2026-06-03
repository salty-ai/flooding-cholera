"""Tests for the agent router endpoints."""
from fastapi.testclient import TestClient
from app.main import app

# Pass `app` as positional arg — httpx >= 0.28 removed the `app=` keyword
client = TestClient(app)  # noqa: S101


def test_agent_chat_endpoint():
    """POST /api/agent/chat should return 200 with streaming content."""
    response = client.post(
        "/api/agent/chat",
        json={"message": "hello", "provider": "deepseek", "model": "deepseek-v4-flash"},
    )
    assert response.status_code == 200
    
    # Verify the streamed chunks format
    import json
    lines = response.content.decode().split("\n")
    # Clean trailing empty line
    if lines and not lines[-1]:
        lines.pop()
        
    assert len(lines) > 0
    for line in lines:
        if line.startswith("UI_SPEC:"):
            payload = line[len("UI_SPEC:"):]
            json.loads(payload)
        else:
            assert line.startswith("TEXT:") or line.startswith("THOUGHT:")
            prefix = "TEXT:" if line.startswith("TEXT:") else "THOUGHT:"
            payload = line[len(prefix):]
            decoded = json.loads(payload)
            assert isinstance(decoded, str)


def test_providers_status_endpoint():
    """GET /api/agent/providers/status should return a dict of booleans."""
    response = client.get("/api/agent/providers/status")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    # All five providers should be present
    for provider in ("google", "anthropic", "deepseek", "openrouter", "nvidia_nim"):
        assert provider in data
        assert isinstance(data[provider], bool)


def test_get_active_spec_endpoint():
    """GET /api/agent/active-spec should return 200 and a spec or null."""
    response = client.get("/api/agent/active-spec")
    assert response.status_code == 200
    # Since it might be None or a dict spec
    data = response.json()
    assert data is None or isinstance(data, dict)


def test_agent_data_geocoding():
    """GET /api/agent/data should fetch data and inject missing LGA coordinates if absent."""
    # We will test using Copy of Cholera Data for CRS 2021.xlsx which does not have coordinates
    response = client.get("/api/agent/data?file_path=backend/data/agent_uploads/Copy of Cholera Data for CRS 2021.xlsx")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        row = data[0]
        # Should have latitude and longitude injected
        assert "latitude" in row
        assert "longitude" in row
        assert isinstance(row["latitude"], float)
        assert isinstance(row["longitude"], float)
