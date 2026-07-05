from app.services.data_importer import DataImporter


def test_find_lga_by_state_disambiguation():
    importer = DataImporter.__new__(DataImporter)
    # Two states both have an "Aba North"? Build a cache simulating it.
    importer._lga_cache = {
        "aba north": 1,            # Abia
        "aba north__abia": 1,
        "aba north__oyo": 2,       # hypothetical duplicate
    }
    assert importer._find_lga_id("Aba North", state="Oyo") == 2
    assert importer._find_lga_id("Aba North", state="Abia") == 1
    assert importer._find_lga_id("Aba North") == 1  # first match fallback
