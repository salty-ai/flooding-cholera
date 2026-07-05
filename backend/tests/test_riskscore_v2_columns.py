from app.models import RiskScore

def test_riskscore_v2_fields():
    rs = RiskScore(lga_id=1, score_date=__import__("datetime").date(2024,1,1),
                   score=0.5, level="yellow", flood_event_score=0.3, recent_flood_events=2)
    assert rs.flood_event_score == 0.3
    assert rs.recent_flood_events == 2
