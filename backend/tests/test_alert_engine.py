# backend/tests/test_alert_engine.py
from datetime import date
from unittest.mock import MagicMock, patch
from app.services.alert_engine import _applies, _metric_value, evaluate_rule, _level_for_alert


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


def test_level_for_alert_risk_score_high_is_red():
    """A risk_score metric with a high value must map to 'red'."""
    rule = MagicMock(metric="risk_score", severity="critical")
    assert _level_for_alert(rule, 0.85) == "red"
    assert _level_for_alert(rule, 0.2) == "green"
    assert _level_for_alert(rule, 0.5) == "yellow"


def test_level_for_alert_non_risk_maps_severity():
    """Non-risk_score metrics map severity to green/yellow/red."""
    rule = MagicMock(metric="new_cases", severity="critical")
    assert _level_for_alert(rule, 50.0) == "red"
    rule.severity = "warning"
    assert _level_for_alert(rule, 50.0) == "yellow"
    rule.severity = "info"
    assert _level_for_alert(rule, 50.0) == "green"


def test_evaluate_rule_produces_valid_level():
    """Alerts from evaluate_rule must have level in green/yellow/red."""
    db = MagicMock()
    lga = MagicMock(id=1, name="Test LGA")
    db.query.return_value.all.return_value = [lga]
    db.query.return_value.filter.return_value.all.return_value = []

    rule = MagicMock(id=1, name="High risk", metric="risk_score",
                     operator=">=", threshold=0.6, severity="critical",
                     window_days=0)

    with patch("app.services.alert_engine._metric_value", return_value=0.85):
        alerts = evaluate_rule(db, rule, as_of=date(2024, 6, 1))

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.level in ("green", "yellow", "red")
    assert alert.level == "red"
    assert alert.severity == "critical"
