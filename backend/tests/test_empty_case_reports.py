"""Post-purge regression suite: every case-driven code path on an EMPTY table.

The nationwide LGA-month case panel was rejected by the manuscript and deleted
in production, so `case_reports` is empty while LGAs, flood events, risk scores
and alerts remain. Nothing that reads case data may 500, divide by zero, or
emit a null where the UI expects a number.
"""
from datetime import date, timedelta

import pytest

from app.models import Alert, AlertRule, CaseReport, EnvironmentalData, FloodEvent, LGA, RiskScore
from app.services.alert_engine import run_alert_engine
from app.services.correlation_service import build_correlation_report
from app.services.report_service import (
    build_surveillance_report,
    render_report_csv,
    render_report_pdf,
)
from app.services.risk_calculator import RiskCalculator

TODAY = date(2025, 6, 15)


@pytest.fixture
def purged_db(db_session):
    """Production shape after the purge: everything but case_reports populated."""
    lga = LGA(name="Yakurr", state="Cross River", code="CR-YAK", population=250_000,
              water_coverage_pct=40.0, sanitation_coverage_pct=35.0)
    other = LGA(name="Biase", state="Cross River", code="CR-BIA", population=180_000)
    db_session.add_all([lga, other])
    db_session.flush()

    db_session.add_all([
        EnvironmentalData(lga_id=lga.id, observation_date=TODAY - timedelta(days=2),
                          rainfall_mm=42.0, rainfall_7day_mm=90.0, ndwi=0.35,
                          flood_extent_pct=12.0),
        FloodEvent(uuid="test-flood-0001", lga_id=lga.id,
                   start_date=TODAY - timedelta(days=20),
                   end_date=TODAY - timedelta(days=15), duration_days=5, area_km2=31.4),
        RiskScore(lga_id=lga.id, score_date=TODAY - timedelta(days=1), score=0.62,
                  level="yellow", recent_cases=0, recent_deaths=0),
        AlertRule(name="Case surge", metric="new_cases", operator=">", threshold=10,
                  window_days=14, severity="warning", enabled=True),
        AlertRule(name="Elevated risk", metric="risk_score", operator=">", threshold=0.5,
                  window_days=30, severity="warning", enabled=True),
    ])
    db_session.commit()
    assert db_session.query(CaseReport).count() == 0
    return db_session


def _lga_id(db, name="Yakurr"):
    return db.query(LGA).filter(LGA.name == name).one().id


def test_dashboard_returns_zeros_not_nulls(sqlite_client, purged_db):
    response = sqlite_client.get("/api/lgas/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["total_cases"] == 0
    assert body["total_deaths"] == 0
    assert body["total_lgas"] == 2
    # No case data at all -> no resolvable window, and that is stated explicitly.
    assert body["max_data_date"] is None
    assert body["applied_window_start"] is None
    assert body["applied_window_end"] is None
    assert isinstance(body["avg_rainfall_7day"], (int, float))
    assert body["alert_level"] in ("green", "yellow", "red")


def test_dashboard_with_explicit_window_still_returns_zeros(sqlite_client, purged_db):
    body = sqlite_client.get(
        "/api/lgas/dashboard",
        params={"start_date": "2024-01-01", "end_date": "2024-12-31"},
    ).json()
    assert body["total_cases"] == 0
    assert body["total_deaths"] == 0
    assert body["applied_window_end"] == "2024-12-31"


def test_lga_geojson_reports_zero_recent_cases_not_null(sqlite_client, purged_db):
    response = sqlite_client.get("/api/lgas/geojson")
    assert response.status_code == 200
    features = response.json()["features"]
    assert len(features) == 2
    for feature in features:
        props = feature["properties"]
        assert props["recent_cases"] == 0
        assert props["risk_level"] in ("green", "yellow", "red", "unknown")


def test_lga_cases_endpoint_returns_empty_list(sqlite_client, purged_db):
    response = sqlite_client.get(f"/api/lgas/{_lga_id(purged_db)}/cases")
    assert response.status_code == 200
    assert response.json() == []


def test_lga_analytics_has_zero_totals_and_empty_series(sqlite_client, purged_db):
    response = sqlite_client.get(f"/api/analytics/lga/{_lga_id(purged_db)}")
    assert response.status_code == 200
    body = response.json()
    assert body["cases_time_series"] == []
    assert body["deaths_time_series"] == []
    assert body["total_cases"] == 0
    assert body["total_deaths"] == 0
    assert body["avg_risk_score"] == 0 or isinstance(body["avg_risk_score"], float)


def test_correlation_endpoint_reports_insufficient_data(sqlite_client, purged_db):
    response = sqlite_client.get(
        "/api/analytics/correlation", params={"from_year": 2021, "to_year": 2025}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["case_series"] == []
    # Every lag must degrade to "insufficient" rather than a bogus coefficient.
    assert body["lags"], "correlation returned no lag rows"
    for lag in body["lags"]:
        assert lag["insufficient_data"] is True
        assert lag["pearson_r"] is None


def test_correlation_service_is_json_safe(purged_db):
    report = build_correlation_report(
        purged_db, {"level": "national"}, 2021, 2025
    )
    assert report["case_series"] == []
    assert all(lag["n"] == 0 for lag in report["lags"])


def test_surveillance_report_totals_are_zero_without_nan_cfr(sqlite_client, purged_db):
    response = sqlite_client.get(
        "/api/reports/surveillance",
        params={"period": "monthly", "from": "2025-01-01", "to": "2025-06-30"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["totals"] == {"cases": 0, "deaths": 0, "cfr": 0.0}
    assert body["previous"]["cases"] == 0
    assert body["hotspots_by_cases"] == []
    # Risk distribution comes from risk_scores, which survived the purge.
    assert body["risk_distribution"] == {"green": 0, "yellow": 1, "red": 0}


def test_surveillance_report_renders_pdf_and_csv(purged_db):
    report = build_surveillance_report(
        purged_db, "monthly", {"level": "national"}, date(2025, 1, 1), date(2025, 6, 30)
    )
    assert render_report_pdf(report).startswith(b"%PDF")
    assert b"cases" in render_report_csv(report).lower()


def test_risk_calculator_scores_every_lga_from_environment_alone(purged_db):
    calculator = RiskCalculator(purged_db)
    results = calculator.calculate_all()
    assert len(results) == 2
    for row in results:
        assert "error" not in row, row.get("error")
        assert 0.0 <= row["score"] <= 1.0
        assert row["level"] in ("green", "yellow", "red")
        assert row["components"]["cases"] == 0.0
        assert row["raw_values"]["recent_cases"] == 0
        assert row["raw_values"]["recent_deaths"] == 0


def test_risk_calculator_case_component_is_zero(purged_db):
    calculator = RiskCalculator(purged_db)
    counts = calculator.get_recent_cases(_lga_id(purged_db), days=14, as_of=TODAY)
    assert counts == {"cases": 0, "deaths": 0}
    assert calculator.calculate_case_score(0, 0) == 0.0


def test_alert_engine_does_not_fire_case_rules_on_empty_data(purged_db):
    fired = run_alert_engine(purged_db, as_of=TODAY)
    assert isinstance(fired, int)
    case_alerts = purged_db.query(Alert).filter(Alert.type == "new_cases").all()
    assert case_alerts == [], "a case-metric rule fired with no case data"


def test_alerts_summary_endpoint_survives_the_purge(sqlite_client, purged_db):
    response = sqlite_client.get("/api/alerts/stats/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["total_active"] >= 0
