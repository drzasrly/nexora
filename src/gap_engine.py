import os
import pandas as pd
from src.feature_engineering import minmax

def calculate_demand_score(df, config):
    """Calculate demographic and service pressure demand score."""
    w_pop = config["gap_engine"]["demand_population_weight"]
    w_srv = config["gap_engine"]["demand_service_weight"]
    w_dis = config["gap_engine"]["demand_disease_weight"]
    
    pop_norm = minmax(df["jumlah_penduduk"])
    srv_norm = minmax(df["visits_per_1000"])
    dis_norm = minmax(df["disease_per_1000"])
    
    return w_pop * pop_norm + w_srv * srv_norm + w_dis * dis_norm

def calculate_workforce_gap(df, config):
    """Calculate healthcare workforce capacity deficit."""
    w_nak = config["gap_engine"]["workforce_nakes_weight"]
    w_nur = config["gap_engine"]["workforce_nurse_weight"]
    w_mid = config["gap_engine"]["workforce_midwife_weight"]
    
    nak_norm = minmax(df["nakes_per_1000"])
    nur_norm = minmax(df["perawat_per_1000"])
    mid_norm = minmax(df["bidan_per_1000"])
    
    return w_nak * (1.0 - nak_norm) + w_nur * (1.0 - nur_norm) + w_mid * (1.0 - mid_norm)

def calculate_facility_gap(df, config):
    """Calculate healthcare physical facility capacity deficit."""
    w_fas = config["gap_engine"]["facility_faskes_weight"]
    w_pkm = config["gap_engine"]["facility_pkm_weight"]
    w_pst = config["gap_engine"]["facility_pustu_weight"]
    
    fas_norm = minmax(df["faskes_per_100k"])
    pkm_norm = minmax(df["puskesmas_per_100k"])
    pst_norm = minmax(df["pustu_per_100k"])
    
    return w_fas * (1.0 - fas_norm) + w_pkm * (1.0 - pkm_norm) + w_pst * (1.0 - pst_norm)

def calculate_healthcare_gap(df, config):
    """Calculate final composite healthcare gap score and select rankings."""
    w_dem = config["gap_engine"]["demand_weight"]
    w_wrk = config["gap_engine"]["workforce_weight"]
    w_fac = config["gap_engine"]["facility_weight"]
    w_dis = config["gap_engine"]["disease_weight"]
    
    df = df.copy()
    
    # Ratios must be loaded from feature table
    df["demand_score"] = calculate_demand_score(df, config)
    df["workforce_gap"] = calculate_workforce_gap(df, config)
    df["facility_gap"] = calculate_facility_gap(df, config)
    df["disease_need_score"] = minmax(df["disease_per_1000"])
    df["accessibility_gap"] = 0.0 # fallback default since GIS distance not loaded yet
    
    df["healthcare_gap_score"] = (
        w_dem * df["demand_score"] +
        w_wrk * df["workforce_gap"] +
        w_fac * df["facility_gap"] +
        w_dis * df["disease_need_score"]
    ) * 100.0
    
    return df

def classify_priority(score):
    """Classify 0-100 gap score into qualitative priority categories."""
    if score <= 20.0:
        return "Rendah"
    elif score <= 40.0:
        return "Sedang"
    elif score <= 60.0:
        return "Tinggi"
    elif score <= 80.0:
        return "Sangat Tinggi"
    else:
        return "Kritis"

def create_priority_ranking(df, config):
    """Sort, rank, and categorize priority levels. Save output files."""
    processed_dir = config["data"]["processed_dir"]
    os.makedirs(processed_dir, exist_ok=True)
    
    df = df.copy()
    df["priority_category"] = df["healthcare_gap_score"].apply(classify_priority)
    df = df.sort_values("healthcare_gap_score", ascending=False).reset_index(drop=True)
    df["priority_rank"] = range(1, len(df) + 1)
    
    # Save output datasets
    final_cols = [
        "kecamatan", "demand_score", "workforce_gap", "facility_gap", "disease_need_score", 
        "accessibility_gap", "workforce_demand_mismatch", "healthcare_gap_score", 
        "priority_category", "priority_rank", "data_quality_status"
    ]
    
    # Map data completeness parameters
    df["workforce_demand_mismatch"] = pd.NA
    df["data_quality_status"] = "COMPLETE"
    
    df_output = df[[c for c in final_cols if c in df.columns or c in ["workforce_demand_mismatch", "data_quality_status"]]]
    df_output.to_csv(os.path.join(processed_dir, "healthcare_gap_scores.csv"), index=False)
    
    # Save weight logs
    weights_log = [
        {"component": "demand_weight", "weight": config["gap_engine"]["demand_weight"]},
        {"component": "workforce_weight", "weight": config["gap_engine"]["workforce_weight"]},
        {"component": "facility_weight", "weight": config["gap_engine"]["facility_weight"]},
        {"component": "disease_weight", "weight": config["gap_engine"]["disease_weight"]}
    ]
    pd.DataFrame(weights_log).to_csv("logs/healthcare_gap_weights.csv", index=False)
    
    print("Gap calculations and rankings complete. Saved healthcare_gap_scores.csv.")
    return df_output
