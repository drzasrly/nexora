import pandas as pd

def get_priority_areas(df, top_n=5):
    """
    Sorts districts by gap score descending and returns the top_n critical areas.
    """
    return (
        df.sort_values("healthcare_gap_score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
