import os
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

def validate_config(config):
    """Assert that all composite and sub-component weights sum exactly to 1.0."""
    composite = config["gap_engine"]["composite"]
    total = (
        composite["demand_weight"]
        + composite["workforce_weight"]
        + composite["facility_weight"]
        + composite["disease_weight"]
    )
    if abs(total - 1.0) >= 1e-9:
        raise ValueError(f"Composite weights sum is {total}, expected 1.0!")

    workforce = config["gap_engine"]["workforce"]
    workforce_total = (
        workforce["doctors_weight"]
        + workforce["nurses_weight"]
        + workforce["midwives_weight"]
    )
    if abs(workforce_total - 1.0) >= 1e-9:
        raise ValueError(f"Workforce weights sum is {workforce_total}, expected 1.0!")

    facility = config["gap_engine"]["facility"]
    facility_total = (
        facility["facilities_weight"]
        + facility["puskesmas_weight"]
        + facility["pustu_weight"]
        + facility["beds_weight"]
    )
    if abs(facility_total - 1.0) >= 1e-9:
        raise ValueError(f"Facility weights sum is {facility_total}, expected 1.0!")
    print("Configuration weights validation: PASS")
    return True

def evaluate_data_quality(row):
    """Performs qualitative evaluation check for completeness on a row."""
    checks = [
        row.get("jumlah_penduduk", 0) > 0,
        pd.notna(row.get("nakes_per_1000")),
        pd.notna(row.get("perawat_per_1000")),
        pd.notna(row.get("bidan_per_1000")),
        pd.notna(row.get("faskes_per_100k"))
    ]
    return "COMPLETE" if all(checks) else "INCOMPLETE"
