# backend/tests/test_risk_calculation_v2.py
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy.sql.elements import BindParameter
from app.services.risk_calculator import RiskCalculator

def test_overall_score_uses_flood_event_component():
    calc = RiskCalculator(MagicMock())
    # Force component scores directly
    with patch.object(RiskCalculator, "calculate_flood_score", return_value=0.4), \
         patch.object(RiskCalculator, "calculate_flood_event_score", return_value=0.8), \
         patch.object(RiskCalculator, "calculate_rainfall_score", return_value=0.2), \
         patch.object(RiskCalculator, "calculate_case_score", return_value=0.5), \
         patch.object(RiskCalculator, "calculate_vulnerability_score", return_value=0.6), \
         patch.object(RiskCalculator, "get_recent_cases", return_value={"cases": 0, "deaths": 0}), \
         patch.object(RiskCalculator, "get_latest_environmental", return_value=None):
        score, level, components = calc.calculate_for_lga(lga=MagicMock(id=1, water_coverage_pct=50, sanitation_coverage_pct=50), as_of_date=date(2024,6,1))
    # 0.25*0.4 + 0.20*0.8 + 0.20*0.2 + 0.25*0.5 + 0.10*0.6
    expected = 0.25*0.4 + 0.20*0.8 + 0.20*0.2 + 0.25*0.5 + 0.10*0.6
    assert abs(score - expected) < 1e-6
    assert components["flood_event_score"] == 0.8


def test_get_recent_cases_uses_as_of_not_today():
    """get_recent_cases must scope the window to as_of, not date.today()."""
    calc = RiskCalculator(MagicMock())
    as_of = date(2024, 6, 15)
    calc.db.query.return_value.filter.return_value.first.return_value = (10, 2)
    result = calc.get_recent_cases(lga_id=1, days=14, as_of=as_of)
    assert result == {"cases": 10, "deaths": 2}
    # Inspect the filter call to verify as_of-based bounds were used
    filter_args = calc.db.query.return_value.filter.call_args[0]
    bind_values = []
    for arg in filter_args:
        if hasattr(arg, "right") and isinstance(arg.right, BindParameter):
            bind_values.append(arg.right.value)
    expected_start = as_of - timedelta(days=14)
    assert as_of in bind_values, f"as_of {as_of} not in filter bind values {bind_values}"
    assert expected_start in bind_values, f"start {expected_start} not in filter bind values {bind_values}"


def test_get_latest_environmental_uses_as_of():
    """get_latest_environmental must return the latest row <= as_of."""
    calc = RiskCalculator(MagicMock())
    as_of = date(2024, 6, 15)
    env_mock = MagicMock(ndwi=0.5, flood_extent_pct=10.0,
                         rainfall_7day_mm=50.0, rainfall_30day_mm=100.0)
    calc.db.query.return_value.filter.return_value.order_by.return_value.first.return_value = env_mock
    result = calc.get_latest_environmental(lga_id=1, as_of=as_of)
    assert result is env_mock
    filter_args = calc.db.query.return_value.filter.call_args[0]
    bind_values = []
    for arg in filter_args:
        if hasattr(arg, "right") and isinstance(arg.right, BindParameter):
            bind_values.append(arg.right.value)
    assert as_of in bind_values, f"as_of {as_of} not in filter bind values {bind_values}"


def test_calculate_for_lga_threads_as_of_to_helpers():
    """calculate_for_lga must pass as_of to get_recent_cases and get_latest_environmental."""
    calc = RiskCalculator(MagicMock())
    lga = MagicMock(id=1, water_coverage_pct=50, sanitation_coverage_pct=50)
    as_of = date(2024, 6, 15)
    with patch.object(RiskCalculator, "get_recent_cases") as mock_cases, \
         patch.object(RiskCalculator, "get_latest_environmental") as mock_env, \
         patch.object(RiskCalculator, "calculate_flood_event_score", return_value=0.0):
        mock_cases.return_value = {"cases": 0, "deaths": 0}
        mock_env.return_value = None
        calc.calculate_for_lga(lga, as_of_date=as_of)
        mock_cases.assert_called_once_with(1, days=14, as_of=as_of)
        mock_env.assert_called_once_with(1, as_of=as_of)
