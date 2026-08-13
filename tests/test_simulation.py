import yaml
import pandas as pd
from src.simulation_engine import simulate_intervention

def test_simulation_run():
    # Load config
    with open("config/config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    # Load features
    df_features = pd.read_csv(config["data"]["features"])
    
    district = df_features.iloc[0]["kecamatan"]
    deltas = {
        "nakes": 5,
        "perawat": 3,
        "beds": 10
    }
    
    # Run simulation
    res = simulate_intervention(df_features, district, deltas, config)
    
    assert "before_gap" in res
    assert "after_gap" in res
    assert "improvement_absolute" in res
    assert "improvement_percent" in res
    
    # Check validator (after_gap <= before_gap)
    assert res["after_gap"] <= res["before_gap"]
    assert res["improvement_absolute"] >= 0.0
