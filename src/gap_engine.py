import os
import json
import pandas as pd
from src.feature_engineering import minmax

def minmax_ref(series, ref_min=None, ref_max=None):
    """Min-max scale a pandas Series using optional reference baseline boundaries and clip to [0, 1]."""
    min_val = ref_min if ref_min is not None else series.min()
    max_val = ref_max if ref_max is not None else series.max()
    if max_val == min_val:
        return pd.Series(0.0, index=series.index)
    return ((series - min_val) / (max_val - min_val)).clip(0.0, 1.0)

def calculate_demand_score(df, config, ref_norm=None):
    """Calculate demographic and service pressure demand score (no double counting disease)."""
    demand_cfg = config["gap_engine"]["demand"]
    w_pop = demand_cfg["population_weight"]
    w_srv = demand_cfg["service_weight"]
    
    # Assert weight sum validation (assert weight total is 1.0)
    w_sum = w_pop + w_srv
    if w_sum > 0:
        w_pop, w_srv = w_pop / w_sum, w_srv / w_sum
    else:
        w_pop, w_srv = 0.5, 0.5
        
    pop_ref = ref_norm.get("jumlah_penduduk", {}) if ref_norm else {}
    srv_ref = ref_norm.get("visits_per_1000", {}) if ref_norm else {}
    
    pop_norm = minmax_ref(df["jumlah_penduduk"], pop_ref.get("min"), pop_ref.get("max"))
    srv_norm = minmax_ref(df["visits_per_1000"], srv_ref.get("min"), srv_ref.get("max"))
    
    return w_pop * pop_norm + w_srv * srv_norm

def calculate_workforce_gap(df, config, ref_norm=None):
    """Calculate healthcare workforce capacity deficit using doctor, nurse, and midwife ratios."""
    wf_cfg = config["gap_engine"]["workforce"]
    w_doc = wf_cfg["doctors_weight"]
    w_nur = wf_cfg["nurses_weight"]
    w_mid = wf_cfg["midwives_weight"]
    
    w_sum = w_doc + w_nur + w_mid
    if w_sum > 0:
        w_doc, w_nur, w_mid = w_doc / w_sum, w_nur / w_sum, w_mid / w_sum
    else:
        w_doc, w_nur, w_mid = 0.4, 0.4, 0.2
        
    doc_ref = ref_norm.get("doctors_per_1000", {}) if ref_norm else {}
    nur_ref = ref_norm.get("perawat_per_1000", {}) if ref_norm else {}
    mid_ref = ref_norm.get("bidan_per_1000", {}) if ref_norm else {}
    
    doc_norm = minmax_ref(df["doctors_per_1000"], doc_ref.get("min"), doc_ref.get("max"))
    nur_norm = minmax_ref(df["perawat_per_1000"], nur_ref.get("min"), nur_ref.get("max"))
    mid_norm = minmax_ref(df["bidan_per_1000"], mid_ref.get("min"), mid_ref.get("max"))
    
    return w_doc * (1.0 - doc_norm) + w_nur * (1.0 - nur_norm) + w_mid * (1.0 - mid_norm)

def calculate_facility_gap(df, config, ref_norm=None):
    """Calculate healthcare physical facility capacity deficit (faskes, pkm, pustu, beds)."""
    fac_cfg = config["gap_engine"]["facility"]
    w_fas = fac_cfg["facilities_weight"]
    w_pkm = fac_cfg["puskesmas_weight"]
    w_pst = fac_cfg["pustu_weight"]
    w_bed = fac_cfg["beds_weight"]
    
    w_sum = w_fas + w_pkm + w_pst + w_bed
    if w_sum > 0:
        w_fas, w_pkm, w_pst, w_bed = w_fas / w_sum, w_pkm / w_sum, w_pst / w_sum, w_bed / w_sum
    else:
        w_fas, w_pkm, w_pst, w_bed = 0.3, 0.3, 0.2, 0.2
        
    fas_ref = ref_norm.get("faskes_per_100k", {}) if ref_norm else {}
    pkm_ref = ref_norm.get("puskesmas_per_100k", {}) if ref_norm else {}
    pst_ref = ref_norm.get("pustu_per_100k", {}) if ref_norm else {}
    bed_ref = ref_norm.get("beds_per_1000", {}) if ref_norm else {}
    
    fas_norm = minmax_ref(df["faskes_per_100k"], fas_ref.get("min"), fas_ref.get("max"))
    pkm_norm = minmax_ref(df["puskesmas_per_100k"], pkm_ref.get("min"), pkm_ref.get("max"))
    pst_norm = minmax_ref(df["pustu_per_100k"], pst_ref.get("min"), pst_ref.get("max"))
    bed_norm = minmax_ref(df["beds_per_1000"], bed_ref.get("min"), bed_ref.get("max"))
    
    return w_fas * (1.0 - fas_norm) + w_pkm * (1.0 - pkm_norm) + w_pst * (1.0 - pst_norm) + w_bed * (1.0 - bed_norm)

def calculate_healthcare_gap(df, config, ref_norm=None):
    """Calculate final composite healthcare gap score using baseline reference scaling."""
    comp_cfg = config["gap_engine"]["composite"]
    w_dem = comp_cfg["demand_weight"]
    w_wrk = comp_cfg["workforce_weight"]
    w_fac = comp_cfg["facility_weight"]
    w_dis = comp_cfg["disease_weight"]
    
    df = df.copy()
    
    # Save baseline normalization references if not provided (Section 31 & 32)
    if ref_norm is None:
        ref_norm = {}
        cols_to_ref = [
            "jumlah_penduduk", "visits_per_1000", "doctors_per_1000",
            "perawat_per_1000", "bidan_per_1000", "faskes_per_100k",
            "puskesmas_per_100k", "pustu_per_100k", "beds_per_1000", "disease_per_1000"
        ]
        for col in cols_to_ref:
            if col in df.columns:
                ref_norm[col] = {
                    "min": float(df[col].min()),
                    "max": float(df[col].max())
                }
        ref_path = os.path.join(config["data"]["processed_dir"], "normalization_reference.json")
        os.makedirs(os.path.dirname(ref_path), exist_ok=True)
        with open(ref_path, "w") as f:
            json.dump(ref_norm, f, indent=4)
            
    # Calculate scores with baseline reference minmax bounds
    df["demand_score"] = calculate_demand_score(df, config, ref_norm)
    df["workforce_gap"] = calculate_workforce_gap(df, config, ref_norm)
    df["facility_gap"] = calculate_facility_gap(df, config, ref_norm)
    
    dis_ref = ref_norm.get("disease_per_1000", {}) if ref_norm else {}
    df["disease_need_score"] = minmax_ref(df["disease_per_1000"], dis_ref.get("min"), dis_ref.get("max"))
    df["accessibility_gap"] = 0.0
    
    df["healthcare_gap_score"] = (
        w_dem * df["demand_score"] +
        w_wrk * df["workforce_gap"] +
        w_fac * df["facility_gap"] +
        w_dis * df["disease_need_score"]
    ) * 100.0
    
    # Validations
    assert df["healthcare_gap_score"].min() >= 0.0, "Score underflow!"
    assert df["healthcare_gap_score"].max() <= 100.0, "Score overflow!"
    
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
    
    # Evaluate data quality dynamically (Section 43)
    from src.validation import evaluate_data_quality
    df["data_quality_status"] = df.apply(evaluate_data_quality, axis=1)
    df["workforce_demand_mismatch"] = pd.NA
    
    df_output = df[[c for c in final_cols if c in df.columns or c in ["workforce_demand_mismatch"]]]
    df_output.to_csv(os.path.join(processed_dir, "healthcare_gap_scores.csv"), index=False)
    
    # Save weights logs
    comp_cfg = config["gap_engine"]["composite"]
    pd.DataFrame([{
        "demand_weight": comp_cfg["demand_weight"],
        "workforce_weight": comp_cfg["workforce_weight"],
        "facility_weight": comp_cfg["facility_weight"],
        "disease_weight": comp_cfg["disease_weight"]
    }]).to_csv("logs/healthcare_gap_weights.csv", index=False)
    
    print("Healthcare gap scoring and prioritization complete.")
    return df
