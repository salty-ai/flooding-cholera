# backend/tests/test_groundsource_importer.py
import math
from app.services.groundsource_importer import compute_flood_event_score_inputs


def test_compute_flood_event_score_inputs_decay():
    # area 0..500 -> 0..1, recency exp(-dt/14)
    s = compute_flood_event_score_inputs(area_km2=250.0, days_since_start=0)
    assert math.isclose(s, 1.0 * 1.0, rel_tol=1e-6)
    s2 = compute_flood_event_score_inputs(area_km2=250.0, days_since_start=14)
    assert math.isclose(s2, 1.0 * math.exp(-1.0), rel_tol=1e-6)
    s3 = compute_flood_event_score_inputs(area_km2=0.0, days_since_start=0)
    assert s3 == 0.0
