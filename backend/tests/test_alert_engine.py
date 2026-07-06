# backend/tests/test_alert_engine.py
from datetime import date
from unittest.mock import MagicMock
from app.services.alert_engine import _applies, _metric_value


def test_applies_operator():
    assert _applies(">=", 0.6, 0.6) is True
    assert _applies(">", 0.6, 0.6) is False
    assert _applies("<", 0.6, 0.3) is True
    assert _applies("<=", 0.3, 0.3) is True


def test_metric_value_risk_score():
    rule = MagicMock(metric="risk_score", operator=">=", threshold=0.6, window_days=0)
    calc = MagicMock()
    db = MagicMock()
    # _metric_value returns (value, numeric) for the given lga
    # Implementation chains .filter(...).order_by(...).first(), so the mock
    # chain must include the .filter() link.
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = MagicMock(score=0.72)
    val = _metric_value(db, rule, lga_id=1, as_of=date(2024, 6, 1))
    assert val == 0.72
