import pytest
import pandas as pd
from src.root_cause import determine_primary_root_cause, detect_multi_factor, calculate_root_cause_margin

def test_determine_primary_root_cause():
    row = pd.Series({
        "demand_score": 0.90,
        "workforce_gap": 0.50,
        "facility_gap": 0.70,
        "disease_need_score": 0.30
    })
    assert determine_primary_root_cause(row) == "HIGH_DEMAND"

def test_detect_multi_factor():
    row_single = pd.Series({
        "demand_score": 0.85,
        "workforce_gap": 0.40,
        "facility_gap": 0.50,
        "disease_need_score": 0.20
    })
    assert detect_multi_factor(row_single) == "SINGLE_FACTOR"
    
    row_multi = pd.Series({
        "demand_score": 0.85,
        "workforce_gap": 0.82,
        "facility_gap": 0.90,
        "disease_need_score": 0.10
    })
    assert detect_multi_factor(row_multi) == "MULTI_FACTOR"

def test_calculate_root_cause_margin():
    ranking = [("HIGH_DEMAND", 0.90), ("FACILITY_SHORTAGE", 0.70), ("WORKFORCE_SHORTAGE", 0.50)]
    assert calculate_root_cause_margin(ranking) == pytest.approx(0.20)
