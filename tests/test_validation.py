import pytest
import pandas as pd
import numpy as np
from src.validation import validate_required_columns, validate_kecamatan, validate_numeric, validate_infinity

def test_validate_required_columns():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert validate_required_columns(df, ["a", "b"]) is True
    with pytest.raises(ValueError):
        validate_required_columns(df, ["a", "c"])

def test_validate_kecamatan():
    # 31 Mock Kecamatan
    kecamatans = [f"Kec{i}" for i in range(31)]
    df_ok = pd.DataFrame({"kecamatan": kecamatans})
    assert validate_kecamatan(df_ok) is True
    
    # Incorrect count
    df_err = pd.DataFrame({"kecamatan": ["Kec1", "Kec2"]})
    with pytest.raises(ValueError):
        validate_kecamatan(df_err)

def test_validate_numeric():
    df = pd.DataFrame({"num": [1.5, 2.3], "txt": ["x", "y"]})
    assert validate_numeric(df, ["num"]) is True
    with pytest.raises(TypeError):
        validate_numeric(df, ["txt"])

def test_validate_infinity():
    df_ok = pd.DataFrame({"val": [1.0, 2.0]})
    assert validate_infinity(df_ok) is True
    
    df_inf = pd.DataFrame({"val": [1.0, np.inf]})
    with pytest.raises(ValueError):
        validate_infinity(df_inf)
