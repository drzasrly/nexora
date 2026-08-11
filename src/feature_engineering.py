import os
import numpy as np
import pandas as pd

def minmax(series):
    """Min-max scale a pandas Series to range [0, 1]."""
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series(0.5, index=series.index)
    return (series - min_val) / (max_val - min_val)

def build_features(df, df_peny, config):
    """
    Formulate core healthcare demand, capacity, accessibility, and mismatch indicators.
    Saves outputs to the configured processed directory.
    """
    processed_dir = config["data"]["processed_dir"]
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    print("Building healthcare features...")
    df_feat = pd.DataFrame({"kecamatan": df["kecamatan"].tolist()})
    df_feat = pd.merge(df_feat, df[["kecamatan", "jumlah_penduduk", "kepadatan_penduduk", "total_kunjungan"]], on="kecamatan", how="left")
    
    # 1. Demand ratios
    df_feat["visits_per_1000"] = df_feat["total_kunjungan"] / df_feat["jumlah_penduduk"]
    
    # 2. Workforce ratios
    df_feat = pd.merge(df_feat, df[["kecamatan", "total_tenaga_kesehatan", "jumlah_perawat", "jumlah_bidan"]], on="kecamatan", how="left")
    df_feat["nakes_per_1000"] = df_feat["total_tenaga_kesehatan"] / df_feat["jumlah_penduduk"]
    df_feat["perawat_per_1000"] = df_feat["jumlah_perawat"] / df_feat["jumlah_penduduk"]
    df_feat["bidan_per_1000"] = df_feat["jumlah_bidan"] / df_feat["jumlah_penduduk"]
    
    # 3. Facility ratios
    df_feat = pd.merge(df_feat, df[["kecamatan", "total_faskes", "jumlah_puskesmas", "jumlah_pustu"]], on="kecamatan", how="left")
    df_feat["faskes_per_100k"] = (df_feat["total_faskes"] / df_feat["jumlah_penduduk"]) * 100.0
    df_feat["puskesmas_per_100k"] = (df_feat["jumlah_puskesmas"] / df_feat["jumlah_penduduk"]) * 100.0
    df_feat["pustu_per_100k"] = (df_feat["jumlah_pustu"] / df_feat["jumlah_penduduk"]) * 100.0
    
    # 4. Inpatient bed ratio
    df_feat = pd.merge(df_feat, df[["kecamatan", "total_tempat_tidur"]], on="kecamatan", how="left")
    df_feat["beds_per_1000"] = df_feat["total_tempat_tidur"] / df_feat["jumlah_penduduk"]
    
    # 5. Disease burden ratio
    df_feat = pd.merge(df_feat, df[["kecamatan", "total_kasus_penyakit"]], on="kecamatan", how="left")
    df_feat["disease_per_1000"] = df_feat["total_kasus_penyakit"] / df_feat["jumlah_penduduk"]
    
    # 6. Extract dominant diseases
    print("Extracting dominant disease profiles...")
    df_peny_grouped = df_peny.groupby(["kecamatan", "jenis_penyakit"])["jumlah_kasus"].sum().reset_index()
    
    disease_records = []
    for kec in df_feat["kecamatan"].unique():
        kec_df = df_peny_grouped[df_peny_grouped["kecamatan"] == kec]
        active_cases = kec_df[kec_df["jumlah_kasus"] > 0]
        if len(active_cases) > 0:
            max_row = active_cases.loc[active_cases["jumlah_kasus"].idxmax()]
            dominant_disease = max_row["jenis_penyakit"]
            highest_cases = max_row["jumlah_kasus"]
        else:
            dominant_disease = pd.NA
            highest_cases = 0
        unique_disease_count = kec_df[kec_df["jumlah_kasus"] > 0]["jenis_penyakit"].nunique()
        disease_records.append({
            "kecamatan": kec,
            "jenis_penyakit_dominan": dominant_disease,
            "kasus_penyakit_tertinggi": highest_cases,
            "jumlah_jenis_penyakit": unique_disease_count
        })
    df_dis = pd.DataFrame(disease_records)
    df_feat = pd.merge(df_feat, df_dis, on="kecamatan", how="left")
    
    # Placeholders for growth/mismatch and accessibility
    df_feat["workforce_growth"] = pd.NA
    df_feat["demand_growth"] = pd.NA
    df_feat["workforce_demand_mismatch"] = pd.NA
    df_feat["distance_to_facility"] = pd.NA
    df_feat["travel_time"] = pd.NA
    df_feat["accessibility_gap"] = pd.NA
    
    # Reorder columns
    final_cols = [
        "kecamatan", "jumlah_penduduk", "kepadatan_penduduk", "total_kunjungan", "visits_per_1000",
        "total_tenaga_kesehatan", "nakes_per_1000", "perawat_per_1000", "bidan_per_1000",
        "total_faskes", "faskes_per_100k", "jumlah_puskesmas", "puskesmas_per_100k", "jumlah_pustu", "pustu_per_100k",
        "total_tempat_tidur", "beds_per_1000", "total_kasus_penyakit", "disease_per_1000",
        "workforce_growth", "demand_growth", "workforce_demand_mismatch",
        "jenis_penyakit_dominan", "kasus_penyakit_tertinggi", "jumlah_jenis_penyakit",
        "distance_to_facility", "travel_time", "accessibility_gap"
    ]
    df_feat_final = df_feat[final_cols]
    
    # Save processed files
    df_feat_final.to_csv(os.path.join(processed_dir, "heal_city_features.csv"), index=False)
    
    # Generate feature validation logs
    val_records = []
    for col in df_feat_final.select_dtypes(include="number").columns:
        inf_count = np.isinf(df_feat_final[col]).sum()
        neg_count = (df_feat_final[col] < 0).sum()
        missing_count = df_feat_final[col].isna().sum()
        c_min = df_feat_final[col].min()
        c_max = df_feat_final[col].max()
        c_mean = df_feat_final[col].mean()
        val_records.append({
            "feature_name": col, "infinite_count": inf_count, "negative_count": neg_count,
            "missing_count": missing_count, "missing_percentage": f"{(missing_count/len(df_feat_final))*100:.1f}%",
            "min_value": f"{c_min:.4f}" if pd.notna(c_min) else "NaN",
            "max_value": f"{c_max:.4f}" if pd.notna(c_max) else "NaN",
            "mean_value": f"{c_mean:.4f}" if pd.notna(c_mean) else "NaN",
            "status": "PASS" if inf_count == 0 and neg_count == 0 else "FAIL"
        })
    for col in df_feat_final.select_dtypes(exclude="number").columns:
        missing_count = df_feat_final[col].isna().sum()
        val_records.append({
            "feature_name": col, "infinite_count": 0, "negative_count": 0,
            "missing_count": missing_count, "missing_percentage": f"{(missing_count/len(df_feat_final))*100:.1f}%",
            "min_value": "N/A", "max_value": "N/A", "mean_value": "N/A", "status": "PASS"
        })
    pd.DataFrame(val_records).to_csv("logs/feature_validation_report.csv", index=False)
    
    # Dictionary log
    dict_records = [
        {"feature_name": "kecamatan", "category": "Geographic", "unit": "Name", "purpose": "Primary key"},
        {"feature_name": "jumlah_penduduk", "category": "Demand", "unit": "Ribu", "purpose": "Kecamatan demographic scale size"},
        {"feature_name": "kepadatan_penduduk", "category": "Demand", "unit": "km2", "purpose": "Population concentration"},
        {"feature_name": "total_kunjungan", "category": "Demand", "unit": "visits", "purpose": "Cumulative visits volume"},
        {"feature_name": "visits_per_1000", "category": "Demand", "unit": "visits/1k pop", "purpose": "Service pressure indicator"},
        {"feature_name": "total_tenaga_kesehatan", "category": "Capacity", "unit": "nakes", "purpose": "Workforce absolute size"},
        {"feature_name": "nakes_per_1000", "category": "Capacity", "unit": "nakes/1k pop", "purpose": "Healthcare workforce capacity ratio"},
        {"feature_name": "perawat_per_1000", "category": "Capacity", "unit": "nurses/1k pop", "purpose": "Nursing labor capacity ratio"},
        {"feature_name": "bidan_per_1000", "category": "Capacity", "unit": "midwives/1k pop", "purpose": "Midwife capacity ratio"},
        {"feature_name": "total_faskes", "category": "Capacity", "unit": "facilities", "purpose": "Healthcare facilities absolute size"},
        {"feature_name": "faskes_per_100k", "category": "Capacity", "unit": "faskes/100k pop", "purpose": "Total facility capacity ratio"},
        {"feature_name": "jumlah_puskesmas", "category": "Capacity", "unit": "facilities", "purpose": "Primary care facility count"},
        {"feature_name": "puskesmas_per_100k", "category": "Capacity", "unit": "pkm/100k pop", "purpose": "Primary care facility density"},
        {"feature_name": "jumlah_pustu", "category": "Capacity", "unit": "facilities", "purpose": "Auxiliary primary care facility count"},
        {"feature_name": "pustu_per_100k", "category": "Capacity", "unit": "pustu/100k pop", "purpose": "Auxiliary care density"},
        {"feature_name": "total_tempat_tidur", "category": "Capacity", "unit": "beds", "purpose": "Absolute inpatient capacity size"},
        {"feature_name": "beds_per_1000", "category": "Capacity", "unit": "beds/1k pop", "purpose": "Inpatient bed capacity ratio"},
        {"feature_name": "total_kasus_penyakit", "category": "Demand", "unit": "cases", "purpose": "Absolute disease caseload volume"},
        {"feature_name": "disease_per_1000", "category": "Demand", "unit": "cases/1k pop", "purpose": "Disease burden index"},
        {"feature_name": "workforce_growth", "category": "Mismatch", "unit": "percentage", "purpose": "Workforce growth (NaN)"},
        {"feature_name": "demand_growth", "category": "Mismatch", "unit": "percentage", "purpose": "Demand growth (NaN)"},
        {"feature_name": "workforce_demand_mismatch", "category": "Mismatch", "unit": "percentage", "purpose": "Growth mismatch (NaN)"},
        {"feature_name": "jenis_penyakit_dominan", "category": "Disease Highlight", "unit": "Name", "purpose": "Primary disease driver"},
        {"feature_name": "kasus_penyakit_tertinggi", "category": "Disease Highlight", "unit": "cases", "purpose": "Highest caseload of dominant disease"},
        {"feature_name": "jumlah_jenis_penyakit", "category": "Disease Highlight", "unit": "diseases", "purpose": "Disease diversity"},
        {"feature_name": "distance_to_facility", "category": "Accessibility", "unit": "km", "purpose": "Distance gap placeholder"},
        {"feature_name": "travel_time", "category": "Accessibility", "unit": "minutes", "purpose": "Travel duration placeholder"},
        {"feature_name": "accessibility_gap", "category": "Accessibility", "unit": "index", "purpose": "Accessibility gap score"}
    ]
    pd.DataFrame(dict_records).to_csv("logs/feature_dictionary.csv", index=False)
    
    print("Features built successfully.")
    return df_feat_final
