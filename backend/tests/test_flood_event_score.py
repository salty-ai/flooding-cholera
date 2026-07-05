# backend/tests/test_flood_event_score.py
import math
from datetime import date, timedelta
from unittest.mock import MagicMock
from app.services.risk_calculator import RiskCalculator

def test_score_zero_when_no_events():
    calc = RiskCalculator.__new__(RiskCalculator)
    calc.db = MagicMock()
    calc.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    assert calc.calculate_flood_event_score(1, as_of_date=date(2024,6,1)) == 0.0

def test_score_saturates_with_events():
    calc = RiskCalculator.__new__(RiskCalculator)
    today = date(2024, 6, 15)
    class E:
        def __init__(self, area, start):
            self.area_km2 = area
            self.start_date = start
    events = [E(250.0, today - timedelta(days=0)), E(250.0, today - timedelta(days=1))]
    calc.db = MagicMock()
    calc.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = events
    score = calc.calculate_flood_event_score(1, as_of_date=today)
    # two full-area, recent events -> high but < 1
    assert 0.0 < score < 1.0
    assert score > 0.5
