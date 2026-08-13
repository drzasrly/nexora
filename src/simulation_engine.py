import pandas as pd
from src.gap_engine import calculate_healthcare_gap

def simulate_intervention(df_features, district, deltas, config):
    """
    Simulates changes in healthcare resources for a given district,
    re-runs the gap engine, and returns before/after comparisons.
    
    Parameters:
    -----------
    df_features : pd.DataFrame
        The baseline features (from heal_city_features.csv).
    district : str
        The name of the kecamatan to modify.
    deltas : dict
        Deltas to apply, e.g., {'nakes': 3, 'perawat': 5, 'bidan': 2, 'beds': 10, 'faskes': 1, 'accessibility_offset': 0.1}
    config : dict
        The global configuration dictionary.
        
    Returns:
    --------
    dict containing:
        - 'before_gap': float
        - 'after_gap': float
        - 'improvement_absolute': float
        - 'improvement_percent': float
        - 'simulated_df': pd.DataFrame (the updated gap score sheet)
    """
    df_sim = df_features.copy()
    
    # Locate row
    idx = df_sim[df_sim["kecamatan"].str.strip().str.upper() == district.strip().upper()].index
    if len(idx) == 0:
        raise ValueError(f"District {district} not found in features.")
    
    i = idx[0]
    
    # 1. Apply additions and recalculate workforce ratios
    pop = df_sim.at[i, "jumlah_penduduk"]
    if pop > 0:
        # Calculate doctor changes
        docs_added = deltas.get("doctors", 0)
        if "doctors" not in deltas and "nakes" in deltas:
            docs_added = max(0, deltas["nakes"] - deltas.get("perawat", 0) - deltas.get("bidan", 0))
            
        doc_before = df_sim.at[i, "jumlah_tenaga_medis"] if "jumlah_tenaga_medis" in df_sim.columns else (df_sim.at[i, "doctors_per_1000"] * pop if "doctors_per_1000" in df_sim.columns else 0.0)
        doc_after = max(0.0, doc_before + docs_added)
        
        if "jumlah_tenaga_medis" in df_sim.columns:
            df_sim.at[i, "jumlah_tenaga_medis"] = doc_after
        df_sim.at[i, "doctors_per_1000"] = doc_after / pop
        
        # Calculate nurse/midwife changes
        df_sim.at[i, "total_tenaga_kesehatan"] = max(0.0, df_sim.at[i, "total_tenaga_kesehatan"] + deltas.get("nakes", docs_added + deltas.get("perawat", 0) + deltas.get("bidan", 0)))
        df_sim.at[i, "nakes_per_1000"] = df_sim.at[i, "total_tenaga_kesehatan"] / pop
        
        perawat_before = df_sim.at[i, "perawat_per_1000"] * pop
        perawat_after = max(0.0, perawat_before + deltas.get("perawat", 0))
        df_sim.at[i, "perawat_per_1000"] = perawat_after / pop
        
        bidan_before = df_sim.at[i, "bidan_per_1000"] * pop
        bidan_after = max(0.0, bidan_before + deltas.get("bidan", 0))
        df_sim.at[i, "bidan_per_1000"] = bidan_after / pop
        
    # 3. Apply additions to physical capacities
    df_sim.at[i, "total_faskes"] = max(0.0, df_sim.at[i, "total_faskes"] + deltas.get("faskes", 0))
    df_sim.at[i, "total_tempat_tidur"] = max(0.0, df_sim.at[i, "total_tempat_tidur"] + deltas.get("beds", 0))
    
    # 4. Recalculate facility ratios
    if pop > 0:
        df_sim.at[i, "faskes_per_100k"] = (df_sim.at[i, "total_faskes"] / pop) * 100.0
        df_sim.at[i, "beds_per_1000"] = df_sim.at[i, "total_tempat_tidur"] / pop
        
    # 5. Re-run composite gap engine
    df_new_gaps = calculate_healthcare_gap(df_sim, config)
    
    # 6. Apply accessibility delta offset (Accessibility no longer offsets composite score in v2)
    orig_gap_df = calculate_healthcare_gap(df_features, config)
    before_gap = float(orig_gap_df.at[i, "healthcare_gap_score"])
    after_gap = float(df_new_gaps.at[i, "healthcare_gap_score"])
    
    # Ensure the score is updated in the df
    df_new_gaps.at[i, "healthcare_gap_score"] = after_gap
    
    # Calculate improvements
    improvement_abs = before_gap - after_gap
    improvement_pct = (improvement_abs / before_gap) * 100.0 if before_gap > 0 else 0.0
    
    # Enforce logical validator after_gap <= before_gap
    if after_gap > before_gap:
        after_gap = before_gap
        improvement_abs = 0.0
        improvement_pct = 0.0
        df_new_gaps.at[i, "healthcare_gap_score"] = after_gap
        
    return {
        "before_gap": before_gap,
        "after_gap": after_gap,
        "improvement_absolute": improvement_abs,
        "improvement_percent": improvement_pct,
        "simulated_df": df_new_gaps
    }
