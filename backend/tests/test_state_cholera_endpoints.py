"""Tests for the verified state-level (national tier) endpoints."""
from datetime import date

import pytest

from app.constants import OFFICIAL_YEAR_END
from app.models import StateCholeraRecord

SITREP = "https://ncdc.gov.ng/themes/common/files/sitreps/{}.pdf"


def _record(state, year, week, cases, deaths, **kw):
    return StateCholeraRecord(
        state=state,
        year=year,
        epi_week=week,
        report_date=date.fromisocalendar(year, week, 1),
        month=kw.get("month", "June"),
        suspected_cases=cases,
        deaths=deaths,
        cfr=round(deaths / cases * 100, 2) if cases else None,
        confidence=kw.get("confidence", "high"),
        monotonic_ok=kw.get("monotonic_ok", True),
        extraction_method=kw.get("extraction_method", "text_cluster_plaintext"),
        source_url=kw.get("source_url", SITREP.format(f"{state}{year}{week}")),
    )


@pytest.fixture
def seeded_states(db_session):
    """A miniature but structurally faithful slice of the verified dataset."""
    db_session.add_all([
        # Two weeks for Abia 2021: the later one is the year-end snapshot.
        _record("Abia", 2021, 40, 80, 2),
        _record("Abia", 2021, 47, 97, 3),
        # A quarantined row with an absurd value — must never reach an aggregate.
        _record("Abia", 2021, 44, 9999, 999, monotonic_ok=False),
        _record("Cross River", 2021, 45, 74, 4, confidence="reassembled",
                extraction_method="text_cluster_ocr"),
        # The dataset spells the capital territory "FCT".
        _record("FCT", 2021, 46, 120, 5),
        # A second year, so years_available / default-year logic is exercised.
        _record("Abia", 2024, 12, 30, 1),
        _record("Lagos", 2024, 39, 210, 6),
    ])
    db_session.commit()
    return db_session


def test_choropleth_defaults_to_latest_year_with_official_total(sqlite_client, seeded_states):
    # 2024 is the latest year with data but has no official NCDC year-end total;
    # the landing view should open on the latest *citable* year (2021).
    body = sqlite_client.get("/api/states/choropleth").json()
    assert body["year"] == 2021
    assert body["years_available"] == [2024, 2021]


def test_choropleth_uses_year_end_snapshot_not_a_sum(sqlite_client, seeded_states):
    body = sqlite_client.get("/api/states/choropleth", params={"year": 2021}).json()
    abia = next(s for s in body["states"] if s["state"] == "Abia")
    # Week 47 is the latest analysis-safe row; weeks 40/44 must not be added in.
    assert abia["epi_week"] == 47
    assert abia["suspected_cases"] == 97
    assert abia["deaths"] == 3


def test_choropleth_excludes_quarantined_rows_but_counts_them(sqlite_client, seeded_states):
    body = sqlite_client.get("/api/states/choropleth", params={"year": 2021}).json()
    abia = next(s for s in body["states"] if s["state"] == "Abia")
    assert abia["suspected_cases"] != 9999
    # n_reports is the extraction count, quarantined rows included.
    assert abia["n_reports"] == 3


def test_choropleth_joins_adm1_pcodes_including_fct(sqlite_client, seeded_states):
    body = sqlite_client.get("/api/states/choropleth", params={"year": 2021}).json()
    pcodes = {s["state"]: s["adm1_pcode"] for s in body["states"]}
    assert pcodes["Abia"] == "NG001"
    assert pcodes["Cross River"] == "NG009"
    assert pcodes["FCT"] == "NG015"  # normalised to Federal Capital Territory
    assert body["unmatched_states"] == []
    fct = next(s for s in body["states"] if s["state"] == "FCT")
    assert fct["adm1_name"] == "Federal Capital Territory"


def test_choropleth_sorted_by_cases_and_carries_provenance(sqlite_client, seeded_states):
    body = sqlite_client.get("/api/states/choropleth", params={"year": 2021}).json()
    cases = [s["suspected_cases"] for s in body["states"]]
    assert cases == sorted(cases, reverse=True)
    for s in body["states"]:
        assert s["source_url"].startswith("https://ncdc.gov.ng/")
        assert s["confidence"] in ("high", "reassembled")


def test_choropleth_on_empty_database(sqlite_client):
    response = sqlite_client.get("/api/states/choropleth")
    assert response.status_code == 200
    body = response.json()
    assert body["year"] is None
    assert body["states"] == []
    assert body["years_available"] == []


def test_state_records_returns_every_row_including_quarantined(sqlite_client, seeded_states):
    body = sqlite_client.get("/api/states/Abia/records").json()
    assert body["state"] == "Abia"
    assert body["count"] == 4  # 3x 2021 (one quarantined) + 1x 2024
    assert any(r["monotonic_ok"] is False for r in body["records"])
    ordering = [(r["year"], r["epi_week"]) for r in body["records"]]
    assert ordering == sorted(ordering)


def test_state_records_year_filter_and_provenance_fields(sqlite_client, seeded_states):
    body = sqlite_client.get("/api/states/Cross River/records", params={"year": 2021}).json()
    assert body["count"] == 1
    record = body["records"][0]
    for key in (
        "year", "epi_week", "month", "report_date", "suspected_cases", "deaths",
        "cfr", "confidence", "extraction_method", "monotonic_ok", "source_url",
    ):
        assert key in record, f"missing provenance field: {key}"
    assert record["confidence"] == "reassembled"
    assert record["extraction_method"] == "text_cluster_ocr"


def test_state_records_accepts_spelling_variants(sqlite_client, seeded_states):
    for spelling in ("FCT", "Federal Capital Territory", "fct"):
        body = sqlite_client.get(f"/api/states/{spelling}/records").json()
        assert body["state"] == "Federal Capital Territory"
        assert body["count"] == 1, f"{spelling} did not resolve to the FCT rows"


def test_state_records_unknown_state_is_404(sqlite_client, seeded_states):
    assert sqlite_client.get("/api/states/Atlantis/records").status_code == 404


def test_state_records_known_state_without_data_is_empty_not_404(sqlite_client, seeded_states):
    body = sqlite_client.get("/api/states/Sokoto/records").json()
    assert body["count"] == 0
    assert body["records"] == []


def test_national_summary_keeps_official_and_dataset_totals_separate(sqlite_client, seeded_states):
    body = sqlite_client.get("/api/states/national-summary").json()
    y2021 = next(y for y in body["years"] if y["year"] == 2021)

    # Dataset-derived: 97 (Abia) + 74 (Cross River) + 120 (FCT)
    assert y2021["dataset_sum_cases"] == 291
    assert y2021["dataset_sum_deaths"] == 12
    assert y2021["states_reporting"] == 3
    # Official: straight from the constants file, never recomputed.
    assert y2021["official_cases"] == OFFICIAL_YEAR_END[2021]["cases"]
    assert y2021["official_deaths"] == OFFICIAL_YEAR_END[2021]["deaths"]
    assert "epi-week 52, 2021" in y2021["official_citation"]
    assert y2021["official_cases"] != y2021["dataset_sum_cases"]


def test_national_summary_years_without_official_totals_report_null(sqlite_client, seeded_states):
    body = sqlite_client.get("/api/states/national-summary").json()
    y2024 = next(y for y in body["years"] if y["year"] == 2024)
    assert y2024["official_cases"] is None
    assert y2024["official_citation"] is None
    assert y2024["dataset_sum_cases"] == 240
    assert "No official year-end total" in y2024["coverage_note"]


def test_national_summary_ordering_and_label(sqlite_client, seeded_states):
    body = sqlite_client.get("/api/states/national-summary").json()
    assert body["years_available"] == [2024, 2021]
    assert "84/93 reports" in body["evidence_label"]


def test_national_summary_on_empty_database(sqlite_client):
    response = sqlite_client.get("/api/states/national-summary")
    assert response.status_code == 200
    assert response.json()["years"] == []


def test_summary_still_serves_its_legacy_shape(sqlite_client, seeded_states):
    body = sqlite_client.get("/api/states/summary").json()
    assert [y["year"] for y in body["years"]] == [2024, 2021]
    y2021 = body["years"][1]
    assert y2021["cases"] == 291
    assert y2021["cfr"] == round(12 / 291 * 100, 2)


def test_boundaries_endpoint_serves_geojson_with_cache_headers(sqlite_client):
    response = sqlite_client.get("/api/states/boundaries")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/geo+json")
    assert "max-age" in response.headers["cache-control"]
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 37
    assert body["features"][0]["properties"]["adm1_pcode"].startswith("NG")
