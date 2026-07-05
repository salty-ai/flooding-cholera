# backend/tests/test_risk_calculation_v2.py
from datetime import date
from unittest.mock import MagicMock, patch
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
