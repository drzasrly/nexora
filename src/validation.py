import numpy as np
import pandas as pd

def validate_required_columns(df, required_columns):
    """Check if all required columns exist in the DataFrame."""
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return True

def validate_kecamatan(df, column="kecamatan"):
    """Assert that there are exactly 31 unique Kecamatan in the dataset."""
    if column not in df.columns:
        raise ValueError(f"Kecamatan column '{column}' not found in DataFrame!")
    
    unique_count = df[column].nunique()
    if unique_count != 31:
        raise ValueError(f"Expected exactly 31 Kecamatan, but found {unique_count}!")
    return True

def validate_numeric(df, columns):
    """Verify that the specified columns contain numeric types."""
    for col in columns:
        if col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise TypeError(f"Column '{col}' is not of numeric type!")
    return True

def validate_infinity(df):
    """Scan all numerical columns to check for infinity or negative infinity values."""
    numeric_df = df.select_dtypes(include=[np.number])
    if np.isinf(numeric_df).any().any():
        raise ValueError("DataFrame contains invalid infinity values!")
    return True

def missing_report(df):
    """Generate a summary of missing counts and percentages per column."""
    report = pd.DataFrame({
        "missing_count": df.isna().sum(),
        "missing_percentage": df.isna().mean() * 100
    })
    return report.sort_values("missing_percentage", ascending=False)
