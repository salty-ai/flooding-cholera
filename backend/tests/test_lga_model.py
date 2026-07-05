from app.models import LGA

def test_lga_has_state_and_pcode():
    lga = LGA(name="Aba North", code="NG001001", state="Abia", pcode="NG001001")
    assert lga.state == "Abia"
    assert lga.pcode == "NG001001"
