"""Pytest tests for the benchmark scoring functions.

Covers:
  * grounding detection with invented vs real columns
  * role binding (case / lga / deaths) on the canonical spec
  * N/A deaths on the reduced schema (correct_deaths_binding is null, not failed)
"""

import os
import sys

import pytest

# Make the harness dir importable when pytest runs from anywhere.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scoring import (
    TRUTH, VARIANTS,
    load_actual_columns, extract_referenced_columns,
    compute_grounding, bind_roles, score_trial,
)


# Canonical spec the agent would emit for canonical.csv, bound to the true
# columns: lga_name (LGA), suspected_cases (cases, sum), deaths (deaths, sum).
CANONICAL_SPEC = {
    "file_path": "data/agent_uploads/canonical.csv",
    "config": {
        "title": "Cholera Surveillance",
        "description": "Cases by LGA",
        "widgets": [
            {
                "type": "kpi", "title": "Total Cases", "gridSpan": 4,
                "config": {"valueKey": "suspected_cases", "aggType": "sum",
                           "icon": "coronavirus", "color": "red"},
            },
            {
                "type": "kpi", "title": "Total Deaths", "gridSpan": 4,
                "config": {"valueKey": "deaths", "aggType": "sum",
                           "icon": "warning", "color": "black"},
            },
            {
                "type": "chart", "title": "Cases by LGA", "gridSpan": 6,
                "config": {"chartType": "bar", "xAxisKey": "lga_name",
                           "series": [{"key": "suspected_cases", "color": "#fa6238"}]},
            },
            {
                "type": "map", "title": "Spatial Distribution", "gridSpan": 12,
                "config": {"latKey": "lat", "lngKey": "lng",
                           "labelKey": "lga_name",
                           "valueKeyForMarker": "suspected_cases"},
            },
            {
                "type": "table", "title": "Data", "gridSpan": 12,
                "config": {},
            },
        ],
    },
}

VARIANTS_DIR = os.path.join(ROOT, "variants")


# ── Grounding ─────────────────────────────────────────────────────────────
def test_grounding_real_columns_only():
    refs = extract_referenced_columns(CANONICAL_SPEC)
    actual = load_actual_columns(os.path.join(VARIANTS_DIR, "canonical.csv"))
    # canonical.csv has lga_name, suspected_cases, deaths — but the spec above
    # also references "lat"/"lng" which are NOT in the file, so it is NOT grounded.
    assert "lat" in refs and "lng" in refs
    assert compute_grounding(refs, actual) is False


def test_grounding_with_invented_column_fails():
    actual = ["lga_name", "suspected_cases", "deaths"]
    assert compute_grounding(["lga_name", "suspected_cases"], actual) is True
    assert compute_grounding(["lga_name", "phantom_col"], actual) is False
    # invented column that does not exist verbatim → not grounded
    assert compute_grounding(["Suspected  Cases "], actual) is False


def test_grounding_empty_refs_fails():
    assert compute_grounding([], ["a", "b"]) is False
    # a spec with no column refs (e.g. only a table widget) is not grounded
    empty_spec = {"config": {"widgets": [{"type": "table", "config": {}}]}}
    assert extract_referenced_columns(empty_spec) == []
    assert compute_grounding(extract_referenced_columns(empty_spec), ["a"]) is False


def test_grounding_dirty_header_exact_match_required():
    # dirty_header.csv has whitespace-laden columns; exact match only.
    actual = load_actual_columns(os.path.join(VARIANTS_DIR, "dirty_header.csv"))
    assert actual == ["  lga name ", "Suspected  Cases ", " deaths"]
    # The agent almost certainly emits clean names → not grounded.
    assert compute_grounding(["lga name", "Suspected Cases", "deaths"], actual) is False
    # But exact strings ARE grounded.
    assert compute_grounding(["  lga name ", "Suspected  Cases "], actual) is True


# ── Role binding on the canonical spec ───────────────────────────────────
def test_role_binding_canonical_correct():
    case_ok, lga_ok, deaths_ok = bind_roles(CANONICAL_SPEC, TRUTH["canonical"])
    assert case_ok is True, "case-count role should bind to suspected_cases"
    assert lga_ok is True, "LGA role should bind to lga_name"
    assert deaths_ok is True, "deaths role should bind to deaths"


def test_role_binding_wrong_case_column_fails():
    spec = {
        "config": {"widgets": [
            {"type": "kpi", "config": {"valueKey": "deaths", "aggType": "sum"}},
            {"type": "chart", "config": {"chartType": "bar",
             "xAxisKey": "lga_name",
             "series": [{"key": "deaths"}]}},
        ]}
    }
    case_ok, lga_ok, deaths_ok = bind_roles(spec, TRUTH["canonical"])
    # No widget binds suspected_cases as a case value → case binding fails.
    assert case_ok is False
    assert lga_ok is True   # lga_name still bound as x-axis
    assert deaths_ok is True


def test_role_binding_wrong_agg_fails_case():
    # value bound to true case column but with avg aggregation (not case-like).
    spec = {"config": {"widgets": [
        {"type": "kpi", "config": {"valueKey": "suspected_cases", "aggType": "avg"}},
    ]}}
    case_ok, _, _ = bind_roles(spec, TRUTH["canonical"])
    assert case_ok is False


# ── Reduced schema: deaths is N/A (null), not failed ──────────────────────
def test_reduced_schema_deaths_is_na():
    truth = TRUTH["reduced_schema"]
    assert truth["deaths"] is None
    spec = {
        "config": {"widgets": [
            {"type": "kpi", "config": {"valueKey": "suspected_cases", "aggType": "sum"}},
            {"type": "chart", "config": {"xAxisKey": "lga_name",
             "series": [{"key": "suspected_cases"}]}},
        ]}
    }
    case_ok, lga_ok, deaths_ok = bind_roles(spec, truth)
    assert case_ok is True
    assert lga_ok is True
    assert deaths_ok is None, "deaths binding must be null (N/A) for reduced schema"


def test_reduced_schema_no_deaths_field_scored_na_via_score_trial():
    actual = load_actual_columns(os.path.join(VARIANTS_DIR, "reduced_schema.csv"))
    spec = {"config": {"widgets": [
        {"type": "kpi", "config": {"valueKey": "suspected_cases", "aggType": "sum"}},
        {"type": "chart", "config": {"xAxisKey": "lga_name",
         "series": [{"key": "suspected_cases"}]}},
    ]}}
    s = score_trial(spec, "reduced_schema", actual)
    assert s["grounding"] is True
    assert s["correct_case_binding"] is True
    assert s["correct_lga_binding"] is True
    assert s["correct_deaths_binding"] is None


# ── score_trial end-to-end on the canonical spec ──────────────────────────
def test_score_trial_canonical_with_map_latlng_ungrounded():
    actual = load_actual_columns(os.path.join(VARIANTS_DIR, "canonical.csv"))
    s = score_trial(CANONICAL_SPEC, "canonical", actual)
    assert s["correct_case_binding"] is True
    assert s["correct_lga_binding"] is True
    assert s["correct_deaths_binding"] is True
    # The map references lat/lng which are not in canonical.csv → not grounded.
    assert s["grounding"] is False
    assert "lat" in s["referenced_columns"] and "lng" in s["referenced_columns"]


def test_score_trial_grounded_when_no_invented_refs():
    spec = {"config": {"widgets": [
        {"type": "kpi", "config": {"valueKey": "suspected_cases", "aggType": "sum"}},
        {"type": "chart", "config": {"xAxisKey": "lga_name",
         "series": [{"key": "suspected_cases"}]}},
        {"type": "table", "config": {}},
    ]}}
    actual = load_actual_columns(os.path.join(VARIANTS_DIR, "canonical.csv"))
    s = score_trial(spec, "canonical", actual)
    assert s["grounding"] is True
    assert s["correct_case_binding"] is True
    assert s["correct_lga_binding"] is True
    assert s["correct_deaths_binding"] is False  # deaths never referenced
