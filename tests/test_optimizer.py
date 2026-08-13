import yaml
import pandas as pd
from src.intervention_optimizer import optimize_interventions

def test_optimizer_run():
    # Load config
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    # Load features
    df_features = pd.read_csv(config["data"]["features"])
    
    district = df_features.iloc[0]["kecamatan"]
    budget = 2000000000 # 2 billion
    resources = {
        "nakes": 15,
        "doctors": 5,
        "nurses": 10,
        "beds": 10
    }
    
    # Run optimizer
    candidates = optimize_interventions(df_features, district, budget, resources, config)
    
    assert len(candidates) > 0
    
    # Verify candidate attributes
    first = candidates[0]
    assert "intervention_name" in first
    assert "cost" in first
    assert "gap_reduction" in first
    assert "feasibility" in first
    assert "score" in first
    
    # Verify sorting (first should have higher score than last)
    if len(candidates) > 1:
        assert candidates[0]["score"] >= candidates[-1]["score"]
