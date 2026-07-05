# backend/tests/test_lga_loader.py
import os
from unittest.mock import MagicMock
from app.services.lga_loader import load_national_lgas

GEOJSON = os.path.join(
    os.path.dirname(__file__), "..", "data", "boundaries", "nigeria_lgas_774.geojson"
)

def test_load_national_lgas_returns_count_and_upserts():
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = None  # no existing
    count = load_national_lgas(db, GEOJSON)
    assert count == 774
    assert db.add.call_count == 774
    assert db.commit.called
