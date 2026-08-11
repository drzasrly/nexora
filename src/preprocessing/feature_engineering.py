import os
import numpy as np
import pandas as pd

# Paths
MASTER_CSV_PATH = "dataset/processed/master_heal_city.csv"
PENYAKIT_CSV_PATH = "dataset/cleaned/clean_penyakit.csv"
PROCESSED_DIR_DATA = "data/processed"
PROCESSED_DIR_DATASET = "dataset/processed"
LOGS_DIR = "logs"

# Ensure directories exist
os.makedirs(PROCESSED_DIR_DATA, exist_ok=True)
os.makedirs(PROCESSED_DIR_DATASET, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

print("Starting HEAL-CITY Feature Engineering Pipeline...")

# Load master dataset
assert os.path.exists(MASTER_CSV_PATH), f"Master dataset not found at {MASTER_CSV_PATH}!"
df = pd.read_csv(MASTER_CSV_PATH)

# Load clean disease dataset for detailed features
assert os.path.exists(PENYAKIT_CSV_PATH), f"Clean penyakit dataset not found at {PENYAKIT_CSV_PATH}!"
df_peny = pd.read_csv(PENYAKIT_CSV_PATH)

# Official 31 Kecamatan
OFFICIAL_KECAMATAN = df["kecamatan"].tolist()

# -----------------------------------------------------------------------------
# 1. CORE COMPONENT RATIOS
# -----------------------------------------------------------------------------

# Pre-validation: ensure Population > 0
assert (df["jumlah_penduduk"] > 0).all(), "Error: Population is 0 or negative in some Kecamatan!"

# Compute ratios
df_feat = pd.DataFrame({"kecamatan": OFFICIAL_KECAMATAN})
df_feat = pd.merge(df_feat, df[["kecamatan", "jumlah_penduduk", "kepadatan_penduduk"]], on="kecamatan", how="left")

# Visits & Service Pressure
df_feat = pd.merge(df_feat, df[["kecamatan", "total_kunjungan"]], on="kecamatan", how="left")
df_feat["visits_per_1000"] = df_feat["total_kunjungan"] / df_feat["jumlah_penduduk"]

# Workforce & Nakes Ratios
df_feat = pd.merge(df_feat, df[["kecamatan", "total_tenaga_kesehatan", "jumlah_perawat", "jumlah_bidan"]], on="kecamatan", how="left")
df_feat["nakes_per_1000"] = df_feat["total_tenaga_kesehatan"] / df_feat["jumlah_penduduk"]
df_feat["perawat_per_1000"] = df_feat["jumlah_perawat"] / df_feat["jumlah_penduduk"]
df_feat["bidan_per_1000"] = df_feat["jumlah_bidan"] / df_feat["jumlah_penduduk"]

# Facilities & Facility Ratios
df_feat = pd.merge(df_feat, df[["kecamatan", "total_faskes", "jumlah_puskesmas", "jumlah_pustu"]], on="kecamatan", how="left")
df_feat["faskes_per_100k"] = (df_feat["total_faskes"] / df_feat["jumlah_penduduk"]) * 100.0
df_feat["puskesmas_per_100k"] = (df_feat["jumlah_puskesmas"] / df_feat["jumlah_penduduk"]) * 100.0
df_feat["pustu_per_100k"] = (df_feat["jumlah_pustu"] / df_feat["jumlah_penduduk"]) * 100.0

# Beds Capacity Ratio
df_feat = pd.merge(df_feat, df[["kecamatan", "total_tempat_tidur"]], on="kecamatan", how="left")
df_feat["beds_per_1000"] = df_feat["total_tempat_tidur"] / df_feat["jumlah_penduduk"]

# Disease Need & Burden Ratio
df_feat = pd.merge(df_feat, df[["kecamatan", "total_kasus_penyakit"]], on="kecamatan", how="left")
df_feat["disease_per_1000"] = df_feat["total_kasus_penyakit"] / df_feat["jumlah_penduduk"]


# -----------------------------------------------------------------------------
# 2. DISEASE-SPECIFIC FEATURES
# -----------------------------------------------------------------------------
print("Extracting detailed disease features per Kecamatan...")

# Group by kecamatan and disease to sum cases
df_peny_grouped = df_peny.groupby(["kecamatan", "jenis_penyakit"])["jumlah_kasus"].sum().reset_index()

disease_spec_records = []
for kec in OFFICIAL_KECAMATAN:
    kec_df = df_peny_grouped[df_peny_grouped["kecamatan"] == kec]
    
    # 1. unique disease types count with cases > 0
    unique_diseases_count = kec_df[kec_df["jumlah_kasus"] > 0]["jenis_penyakit"].nunique()
    
    # 2. Dominant disease name and its highest cases sum
    active_cases = kec_df[kec_df["jumlah_kasus"] > 0]
    if len(active_cases) > 0:
        max_row = active_cases.loc[active_cases["jumlah_kasus"].idxmax()]
        dominant_disease = max_row["jenis_penyakit"]
        highest_case_count = max_row["jumlah_kasus"]
    else:
        dominant_disease = pd.NA
        highest_case_count = 0
        
    disease_spec_records.append({
        "kecamatan": kec,
        "jenis_penyakit_dominan": dominant_disease,
        "kasus_penyakit_tertinggi": highest_case_count,
        "jumlah_jenis_penyakit": unique_diseases_count
    })

df_dis_spec = pd.DataFrame(disease_spec_records)
df_feat = pd.merge(df_feat, df_dis_spec, on="kecamatan", how="left")


# -----------------------------------------------------------------------------
# 3. WORKFORCE GROWTH & MISMATCH PLACEHOLDERS
# -----------------------------------------------------------------------------
# Since we only have 1 year of data, growth and mismatch cannot be calculated. Set to NaN.
df_feat["workforce_growth"] = pd.NA
df_feat["demand_growth"] = pd.NA
df_feat["workforce_demand_mismatch"] = pd.NA


# -----------------------------------------------------------------------------
# 4. ACCESSIBILITY PLACEHOLDERS
# -----------------------------------------------------------------------------
# Spatial data is not yet available, initialize as NaN
df_feat["distance_to_facility"] = pd.NA
df_feat["travel_time"] = pd.NA
df_feat["accessibility_gap"] = pd.NA


# -----------------------------------------------------------------------------
# 5. SAVE FINAL FEATURES DATASET
# -----------------------------------------------------------------------------
# Select target variables in order
final_features_cols = [
    "kecamatan", "jumlah_penduduk", "kepadatan_penduduk",
    "total_kunjungan", "visits_per_1000",
    "total_tenaga_kesehatan", "nakes_per_1000", "perawat_per_1000", "bidan_per_1000",
    "total_faskes", "faskes_per_100k", "jumlah_puskesmas", "puskesmas_per_100k", "jumlah_pustu", "pustu_per_100k",
    "total_tempat_tidur", "beds_per_1000",
    "total_kasus_penyakit", "disease_per_1000",
    "workforce_growth", "demand_growth", "workforce_demand_mismatch",
    "jenis_penyakit_dominan", "kasus_penyakit_tertinggi", "jumlah_jenis_penyakit",
    "distance_to_facility", "travel_time", "accessibility_gap"
]
df_feat_final = df_feat[final_features_cols]

# Save outputs
df_feat_final.to_csv(os.path.join(PROCESSED_DIR_DATA, "heal_city_features.csv"), index=False)
df_feat_final.to_csv(os.path.join(PROCESSED_DIR_DATASET, "heal_city_features.csv"), index=False)
print("Saved heal_city_features.csv to outputs successfully.")


# -----------------------------------------------------------------------------
# 6. FEATURE VALIDATION & LOG REPORT
# -----------------------------------------------------------------------------
print("Generating feature validation report...")

validation_records = []
numeric_cols = df_feat_final.select_dtypes(include="number").columns

for col in numeric_cols:
    # Check infinite values
    inf_count = np.isinf(df_feat_final[col]).sum()
    
    # Check negative values
    neg_count = (df_feat_final[col] < 0).sum()
    
    # Check missing values
    missing_count = df_feat_final[col].isna().sum()
    missing_pct = (missing_count / len(df_feat_final)) * 100.0
    
    # Check min/max/mean bounds
    c_min = df_feat_final[col].min()
    c_max = df_feat_final[col].max()
    c_mean = df_feat_final[col].mean()
    
    validation_records.append({
        "feature_name": col,
        "infinite_count": inf_count,
        "negative_count": neg_count,
        "missing_count": missing_count,
        "missing_percentage": f"{missing_pct:.1f}%",
        "min_value": f"{c_min:.4f}" if pd.notna(c_min) else "NaN",
        "max_value": f"{c_max:.4f}" if pd.notna(c_max) else "NaN",
        "mean_value": f"{c_mean:.4f}" if pd.notna(c_mean) else "NaN",
        "status": "PASS" if inf_count == 0 and neg_count == 0 else "FAIL"
    })

# Add categorical and object columns to validation report
obj_cols = df_feat_final.select_dtypes(exclude="number").columns
for col in obj_cols:
    missing_count = df_feat_final[col].isna().sum()
    missing_pct = (missing_count / len(df_feat_final)) * 100.0
    validation_records.append({
        "feature_name": col,
        "infinite_count": 0,
        "negative_count": 0,
        "missing_count": missing_count,
        "missing_percentage": f"{missing_pct:.1f}%",
        "min_value": "N/A",
        "max_value": "N/A",
        "mean_value": "N/A",
        "status": "PASS"
    })

df_val_report = pd.DataFrame(validation_records)
df_val_report.to_csv(os.path.join(LOGS_DIR, "feature_validation_report.csv"), index=False)
print("Saved logs/feature_validation_report.csv.")


# -----------------------------------------------------------------------------
# 7. FEATURE DICTIONARY LOG
# -----------------------------------------------------------------------------
print("Generating feature dictionary...")

dict_records = [
    {"feature_name": "kecamatan", "category": "Geographic", "formula": "N/A", "unit": "Name", "direction": "N/A", "source": "master_kecamatan", "purpose": "Primary unit of analysis key"},
    {"feature_name": "jumlah_penduduk", "category": "Demand", "formula": "N/A", "unit": "Ribu", "direction": "higher_is_worse", "source": "clean_penduduk.csv", "purpose": "Kecamatan demographic scale size"},
    {"feature_name": "kepadatan_penduduk", "category": "Demand", "formula": "Population / area_km2", "unit": "km2", "direction": "higher_is_worse", "source": "clean_penduduk.csv", "purpose": "Population concentration in area"},
    {"feature_name": "total_kunjungan", "category": "Demand", "formula": "Sum of visits (Jan-Dec)", "unit": "visits", "direction": "higher_is_worse", "source": "clean_kunjungan.csv", "purpose": "Cumulative visits volume"},
    {"feature_name": "visits_per_1000", "category": "Demand", "formula": "Total Visits / Population", "unit": "visits/1k pop", "direction": "higher_is_worse", "source": "clean_kunjungan.csv", "purpose": "Service pressure indicator"},
    {"feature_name": "total_tenaga_kesehatan", "category": "Capacity", "formula": "Sum of nakes categories", "unit": "nakes", "direction": "higher_is_better", "source": "clean_tenaga_kesehatan.csv", "purpose": "Workforce absolute size"},
    {"feature_name": "nakes_per_1000", "category": "Capacity", "formula": "Total Nakes / Population", "unit": "nakes/1k pop", "direction": "higher_is_better", "source": "clean_tenaga_kesehatan.csv", "purpose": "Healthcare workforce capacity ratio"},
    {"feature_name": "perawat_per_1000", "category": "Capacity", "formula": "Jumlah Perawat / Population", "unit": "nurses/1k pop", "direction": "higher_is_better", "source": "clean_tenaga_kesehatan.csv", "purpose": "Nursing labor capacity ratio"},
    {"feature_name": "bidan_per_1000", "category": "Capacity", "formula": "Jumlah Bidan / Population", "unit": "midwives/1k pop", "direction": "higher_is_better", "source": "clean_tenaga_kesehatan.csv", "purpose": "Midwife capacity ratio"},
    {"feature_name": "total_faskes", "category": "Capacity", "formula": "Count of registered faskes", "unit": "facilities", "direction": "higher_is_better", "source": "clean_faskes.csv", "purpose": "Healthcare facilities absolute size"},
    {"feature_name": "faskes_per_100k", "category": "Capacity", "formula": "Total Faskes / Population * 100", "unit": "faskes/100k pop", "direction": "higher_is_better", "source": "clean_faskes.csv", "purpose": "Total facility capacity ratio"},
    {"feature_name": "jumlah_puskesmas", "category": "Capacity", "formula": "Count of puskesmas", "unit": "facilities", "direction": "higher_is_better", "source": "clean_puskesmas.csv", "purpose": "Primary care facility count"},
    {"feature_name": "puskesmas_per_100k", "category": "Capacity", "formula": "Jumlah Puskesmas / Population * 100", "unit": "pkm/100k pop", "direction": "higher_is_better", "source": "clean_puskesmas.csv", "purpose": "Primary care facility density"},
    {"feature_name": "jumlah_pustu", "category": "Capacity", "formula": "Count of puskesmas pembantu", "unit": "facilities", "direction": "higher_is_better", "source": "clean_faskes.csv", "purpose": "Auxiliary primary care facility count"},
    {"feature_name": "pustu_per_100k", "category": "Capacity", "formula": "Jumlah Pustu / Population * 100", "unit": "pustu/100k pop", "direction": "higher_is_better", "source": "clean_faskes.csv", "purpose": "Auxiliary care density"},
    {"feature_name": "total_tempat_tidur", "category": "Capacity", "formula": "Sum of bed capacity", "unit": "beds", "direction": "higher_is_better", "source": "clean_tempat_tidur.csv", "purpose": "Absolute inpatient capacity size"},
    {"feature_name": "beds_per_1000", "category": "Capacity", "formula": "Total Beds / Population", "unit": "beds/1k pop", "direction": "higher_is_better", "source": "clean_tempat_tidur.csv", "purpose": "Inpatient bed capacity ratio"},
    {"feature_name": "total_kasus_penyakit", "category": "Demand", "formula": "Sum of cases (Jan-Dec)", "unit": "cases", "direction": "higher_is_worse", "source": "clean_penyakit.csv", "purpose": "Absolute cumulative disease cases volume"},
    {"feature_name": "disease_per_1000", "category": "Demand", "formula": "Total Cases / Population", "unit": "cases/1k pop", "direction": "higher_is_worse", "source": "clean_penyakit.csv", "purpose": "Disease burden index"},
    {"feature_name": "workforce_growth", "category": "Mismatch", "formula": "(Nakes_t - Nakes_t-1) / Nakes_t-1", "unit": "percentage", "direction": "higher_is_better", "source": "Historical (TBA)", "purpose": "Rate of nakes growth over years (not available in single-year workbook)"},
    {"feature_name": "demand_growth", "category": "Mismatch", "formula": "(Visits_t - Visits_t-1) / Visits_t-1", "unit": "percentage", "direction": "higher_is_worse", "source": "Historical (TBA)", "purpose": "Rate of visit growth over years (not available in single-year workbook)"},
    {"feature_name": "workforce_demand_mismatch", "category": "Mismatch", "formula": "Demand Growth - Workforce Growth", "unit": "percentage", "direction": "higher_is_worse", "source": "Historical (TBA)", "purpose": "Growth mismatch indicator (not available in single-year workbook)"},
    {"feature_name": "jenis_penyakit_dominan", "category": "Disease Highlight", "formula": "Argmax of disease cases", "unit": "Name", "direction": "N/A", "source": "clean_penyakit.csv", "purpose": "Primary disease driver for Root Cause Analysis"},
    {"feature_name": "kasus_penyakit_tertinggi", "category": "Disease Highlight", "formula": "Max of disease cases", "unit": "cases", "direction": "higher_is_worse", "source": "clean_penyakit.csv", "purpose": "Highest caseload of the dominant disease"},
    {"feature_name": "jumlah_jenis_penyakit", "category": "Disease Highlight", "formula": "Count of unique active diseases", "unit": "diseases", "direction": "higher_is_worse", "source": "clean_penyakit.csv", "purpose": "Disease diversity/burden indicator"},
    {"feature_name": "distance_to_facility", "category": "Accessibility", "formula": "Average distance to facility", "unit": "km", "direction": "higher_is_worse", "source": "GIS data (TBA)", "purpose": "Travel accessibility distance"},
    {"feature_name": "travel_time", "category": "Accessibility", "formula": "Average travel time to facility", "unit": "minutes", "direction": "higher_is_worse", "source": "GIS data (TBA)", "purpose": "Travel accessibility time duration"},
    {"feature_name": "accessibility_gap", "category": "Accessibility", "formula": "Normalized travel gap", "unit": "index", "direction": "higher_is_worse", "source": "GIS data (TBA)", "purpose": "Accessibility deficit score"}
]

df_dict = pd.DataFrame(dict_records)
df_dict.to_csv(os.path.join(LOGS_DIR, "feature_dictionary.csv"), index=False)
print("Saved logs/feature_dictionary.csv.")

print("HEAL-CITY Feature Engineering Pipeline Completed Successfully!")
