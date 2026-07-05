from app.models import AlertRule, Alert


def test_alert_rule_construct():
    r = AlertRule(name="High risk", metric="risk_score", operator=">=",
                  threshold=0.6, window_days=0, severity="critical", enabled=True)
    assert r.metric == "risk_score"


def test_alert_has_rule_fields():
    a = Alert(rule_id=1, lga_id=2, triggered_value=0.72, message="x")
    assert a.triggered_value == 0.72
