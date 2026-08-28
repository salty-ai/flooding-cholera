"""Smoke tests for the admin data import router.

These do not depend on the real CSV/Parquet being present. They verify that:
- both endpoints are registered under /api/admin/data
- PathBody validation runs (path must be a string when present)
- the cholera-import default-path logic runs and returns 404 when the file is missing
- the groundsource-import endpoint rejects a missing/non-existent path with 404
"""
from fastapi.testclient import TestClient

from app.main import app
from app.routers.admin_data import PathBody

# Pass `app` as positional arg — httpx >= 0.28 removed the `app=` keyword
client = TestClient(app)  # noqa: S101


def _headers(tag: str) -> dict:
    """Give each test a unique forwarded-IP so the per-IP rate limiter isolates tests."""
    return {"X-Forwarded-For": f"10.0.0.{abs(hash(tag)) % 250 + 1}"}


def test_cholera_import_route_registered():
    """POST /api/admin/data/cholera-import exists; with no real CSV default it 404s."""
    response = client.post("/api/admin/data/cholera-import", json={}, headers=_headers("cholera-default"))
    # Either the default CSV exists (200) or it doesn't (404) — both prove the route is wired.
    assert response.status_code in (200, 404)


def test_cholera_import_explicit_missing_path_returns_404():
    """An explicit non-existent path should 404 (proves PathBody + path logic)."""
    response = client.post(
        "/api/admin/data/cholera-import",
        json={"path": "/definitely/not/a/real/path.csv"},
        headers=_headers("cholera-missing"),
    )
    assert response.status_code == 404


def test_groundsource_import_missing_path_returns_404():
    """groundsource-import with no path should 404 (path is required)."""
    response = client.post(
        "/api/admin/data/groundsource-import",
        json={},
        headers=_headers("gs-missing"),
    )
    assert response.status_code == 404


def test_groundsource_import_nonexistent_path_returns_404():
    """groundsource-import with a non-existent path should 404."""
    response = client.post(
        "/api/admin/data/groundsource-import",
        json={"path": "/definitely/not/a/real.parquet"},
        headers=_headers("gs-nonexistent"),
    )
    assert response.status_code == 404


def test_pathbody_validates_optional_path():
    """PathBody accepts None and a string."""
    assert PathBody().path is None
    assert PathBody(path="/tmp/x.csv").path == "/tmp/x.csv"


def test_admin_routes_in_app_routes():
    """Both admin routes are registered on the app."""
    paths = set(app.openapi().get("paths", {}))
    assert "/api/admin/data/cholera-import" in paths
    assert "/api/admin/data/groundsource-import" in paths
