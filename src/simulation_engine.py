import os
import json
import pandas as pd
from src.gap_engine import calculate_healthcare_gap

def simulate_intervention(df_features, district, deltas, config):
    """
    Simulates changes in healthcare resources for a given district using baseline 
    normalization references, re-runs the gap engine, and returns before/after comparisons.
    """
    df_sim = df_features.copy()
    
    # Locate row
    idx = df_sim[df_sim["kecamatan"].str.strip().str.upper() == district.strip().upper()].index
    if len(idx) == 0:
        raise ValueError(f"District {district} not found in features.")
    
    i = idx[0]
    pop = df_sim.at[i, "jumlah_penduduk"]
    pop_abs = pop * 1000.0
    
    # 1. Apply additions and recalculate workforce ratios
    if pop > 0:
        # Doctors (jumlah_tenaga_medis)
        d_docs = deltas.get("doctors", 0)
        df_sim.at[i, "jumlah_tenaga_medis"] = max(0.0, df_sim.at[i, "jumlah_tenaga_medis"] + d_docs)
        df_sim.at[i, "doctors_per_1000"] = (df_sim.at[i, "jumlah_tenaga_medis"] / pop_abs) * 1000.0
        
        # Nurses (jumlah_perawat)
        d_nurses = deltas.get("nurses", 0)
        df_sim.at[i, "jumlah_perawat"] = max(0.0, df_sim.at[i, "jumlah_perawat"] + d_nurses)
        df_sim.at[i, "perawat_per_1000"] = (df_sim.at[i, "jumlah_perawat"] / pop_abs) * 1000.0
        
        # Midwives (jumlah_bidan)
        d_midwives = deltas.get("midwives", 0)
        df_sim.at[i, "jumlah_bidan"] = max(0.0, df_sim.at[i, "jumlah_bidan"] + d_midwives)
        df_sim.at[i, "bidan_per_1000"] = (df_sim.at[i, "jumlah_bidan"] / pop_abs) * 1000.0
        
        # Total health workers (total_tenaga_kesehatan)
        df_sim.at[i, "total_tenaga_kesehatan"] = (
            df_sim.at[i, "jumlah_tenaga_medis"] +
            df_sim.at[i, "jumlah_perawat"] +
            df_sim.at[i, "jumlah_bidan"]
        )
        df_sim.at[i, "nakes_per_1000"] = (df_sim.at[i, "total_tenaga_kesehatan"] / pop_abs) * 1000.0
        
    # 2. Apply additions to physical capacities
    df_sim.at[i, "total_faskes"] = max(0.0, df_sim.at[i, "total_faskes"] + deltas.get("faskes", 0))
    df_sim.at[i, "total_tempat_tidur"] = max(0.0, df_sim.at[i, "total_tempat_tidur"] + deltas.get("beds", 0))
    
    # 3. Recalculate facility ratios
    if pop > 0:
        df_sim.at[i, "faskes_per_100k"] = (df_sim.at[i, "total_faskes"] / pop_abs) * 100000.0
        df_sim.at[i, "beds_per_1000"] = (df_sim.at[i, "total_tempat_tidur"] / pop_abs) * 1000.0
        
    # Load baseline normalization reference (Section 31 & 32)
    ref_path = os.path.join(config["data"]["processed_dir"], "normalization_reference.json")
    if os.path.exists(ref_path):
        with open(ref_path, "r") as f:
            ref_norm = json.load(f)
    else:
        ref_norm = None
        
    # 4. Re-run composite gap engine using reference boundaries
    df_new_gaps = calculate_healthcare_gap(df_sim, config, ref_norm=ref_norm)
    df_orig_gaps = calculate_healthcare_gap(df_features, config, ref_norm=ref_norm)
    
    before_gap = float(df_orig_gaps.at[i, "healthcare_gap_score"])
    after_gap = float(df_new_gaps.at[i, "healthcare_gap_score"])
    
    # No arbitrary offset modification to after_gap (Section 33)
    improvement_abs = before_gap - after_gap
    improvement_pct = (improvement_abs / before_gap) * 100.0 if before_gap > 0 else 0.0
    
    # Assert monotonicity strictly (Section 32)
    assert after_gap <= before_gap, f"Monotonicity violation! Gap increased from {before_gap} to {after_gap}."
    
    return {
        "before_gap": before_gap,
        "after_gap": after_gap,
        "improvement_absolute": improvement_abs,
        "improvement_percent": improvement_pct,
        "simulated_df": df_new_gaps
    }
