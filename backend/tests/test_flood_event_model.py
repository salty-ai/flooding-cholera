from datetime import date
from app.models import FloodEvent

def test_flood_event_construct():
    fe = FloodEvent(uuid="abc", lga_id=1, start_date=date(2024,6,1),
                    end_date=date(2024,6,3), duration_days=3, area_km2=12.5,
                    data_source="groundsource")
    assert fe.uuid == "abc"
    assert fe.duration_days == 3
