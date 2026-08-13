import pandas as pd
from src.feature_engineering import minmax

def test_minmax_bounds():
    series = pd.Series([10, 50, 100])
    scaled = minmax(series)
    assert scaled.min() == 0.0
    assert scaled.max() == 1.0
    assert scaled.iloc[1] == 4/9 # (50-10)/(100-10) = 40/90 = 4/9

def test_minmax_constant():
    series = pd.Series([20, 20, 20])
    scaled = minmax(series)
    # Constant values return a default boundary of 0.0
    assert (scaled == 0.0).all()
