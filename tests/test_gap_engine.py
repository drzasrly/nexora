from src.gap_engine import classify_priority

def test_classify_priority():
    assert classify_priority(15) == "Rendah"
    assert classify_priority(20) == "Rendah"
    assert classify_priority(25) == "Sedang"
    assert classify_priority(40) == "Sedang"
    assert classify_priority(55) == "Tinggi"
    assert classify_priority(60) == "Tinggi"
    assert classify_priority(75) == "Sangat Tinggi"
    assert classify_priority(80) == "Sangat Tinggi"
    assert classify_priority(85) == "Kritis"
