import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set theme
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 14,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.titlesize": 16
})

# Paths
SCORES_CSV_PATH = "dataset/processed/healthcare_gap_scores.csv"
FEATURES_CSV_PATH = "dataset/processed/heal_city_features.csv"
PROCESSED_DIR_DATA = "data/processed"
PROCESSED_DIR_DATASET = "dataset/processed"
LOGS_DIR = "logs"
RCA_DIR = "outputs/root_cause"

# Ensure directories exist
os.makedirs(PROCESSED_DIR_DATA, exist_ok=True)
os.makedirs(PROCESSED_DIR_DATASET, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(RCA_DIR, exist_ok=True)

print("Starting HEAL-CITY Root Cause Analysis (RCA) Pipeline...")

# Load datasets
assert os.path.exists(SCORES_CSV_PATH), f"Scores dataset not found at {SCORES_CSV_PATH}!"
df_scores = pd.read_csv(SCORES_CSV_PATH)

assert os.path.exists(FEATURES_CSV_PATH), f"Features dataset not found at {FEATURES_CSV_PATH}!"
df_feats = pd.read_csv(FEATURES_CSV_PATH)

# Merge datasets
df_m = pd.merge(df_scores, df_feats[[
    "kecamatan", "jumlah_penduduk", "visits_per_1000", "nakes_per_1000", 
    "perawat_per_1000", "bidan_per_1000", "faskes_per_100k", "puskesmas_per_100k", 
    "pustu_per_100k", "beds_per_1000", "disease_per_1000",
    "jenis_penyakit_dominan", "kasus_penyakit_tertinggi", "jumlah_jenis_penyakit"
]], on="kecamatan", how="left")

# Helper function
def minmax(series):
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series(0.5, index=series.index)
    return (series - min_val) / (max_val - min_val)

# -----------------------------------------------------------------------------
# 1. CORE RCA CALCULATIONS
# -----------------------------------------------------------------------------
print("Analyzing root cause categories...")

rca_records = []

for idx, row in df_m.iterrows():
    kec = row["kecamatan"]
    
    # Define score mappings
    scores = {
        "HIGH_DEMAND": row["demand_score"],
        "WORKFORCE_SHORTAGE": row["workforce_gap"],
        "FACILITY_SHORTAGE": row["facility_gap"],
        "DISEASE_BURDEN": row["disease_need_score"]
    }
    
    # Sort descending
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    primary_rc = sorted_scores[0][0]
    secondary_rc = sorted_scores[1][0]
    tertiary_rc = sorted_scores[2][0]
    
    primary_score = sorted_scores[0][1]
    secondary_score = sorted_scores[1][1]
    tertiary_score = sorted_scores[2][1]
    
    margin = primary_score - secondary_score
    
    # Dominance Classification
    if margin >= 0.20:
        dominance = "Dominant"
    elif margin >= 0.10:
        dominance = "Moderate"
    else:
        dominance = "Shared"
        
    # Multi-Contributor Rule (components >= 0.80)
    contributors = [k for k, v in scores.items() if v >= 0.80]
    if len(contributors) == 0:
        rc_type = "NO_DOMINANT_ROOT_CAUSE"
    elif len(contributors) == 1:
        rc_type = "SINGLE_FACTOR"
    else:
        rc_type = "MULTI_FACTOR"
        
    # Confidence Level
    if primary_score >= 0.80 and margin >= 0.10:
        confidence = "HIGH"
    elif primary_score >= 0.60 or margin < 0.10:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
        
    # -------------------------------------------------------------------------
    # SUB-COMPONENT BREAKDOWNS
    # -------------------------------------------------------------------------
    # We will use global min-max variables from df_m to find the worst subcomponents
    # A. Workforce breakdown
    work_gaps = {
        "Low Nakes Ratio": 1.0 - minmax(df_m["nakes_per_1000"])[idx],
        "Low Nurse Ratio": 1.0 - minmax(df_m["perawat_per_1000"])[idx],
        "Low Midwife Ratio": 1.0 - minmax(df_m["bidan_per_1000"])[idx]
    }
    work_issue = max(work_gaps, key=work_gaps.get)
    
    # B. Facility breakdown
    fac_gaps = {
        "Low Faskes Ratio": 1.0 - minmax(df_m["faskes_per_100k"])[idx],
        "Low Puskesmas Ratio": 1.0 - minmax(df_m["puskesmas_per_100k"])[idx],
        "Low Pustu Ratio": 1.0 - minmax(df_m["pustu_per_100k"])[idx],
        "Low Bed Capacity": 1.0 - minmax(df_m["beds_per_1000"])[idx]
    }
    fac_issue = max(fac_gaps, key=fac_gaps.get)
    
    # C. Demand breakdown
    dem_scores = {
        "High Population Demand": minmax(df_m["jumlah_penduduk"])[idx],
        "High Service Pressure": minmax(df_m["visits_per_1000"])[idx],
        "High Disease Burden": minmax(df_m["disease_per_1000"])[idx]
    }
    dem_issue = max(dem_scores, key=dem_scores.get)
    
    # D. Disease breakdown
    disease_issue = f"{row['jenis_penyakit_dominan']} ({row['kasus_penyakit_tertinggi']} cases)" if pd.notna(row['jenis_penyakit_dominan']) else "N/A"
    
    # E. Accessibility breakdown
    access_issue = "NOT_AVAILABLE"
    
    # -------------------------------------------------------------------------
    # EXPLAINABLE NARRATIVE GENERATION
    # -------------------------------------------------------------------------
    # Format labels for explanations
    label_map = {
        "HIGH_DEMAND": "High Demand Score",
        "WORKFORCE_SHORTAGE": "Workforce Shortage Gap",
        "FACILITY_SHORTAGE": "Facility Capacity Gap",
        "DISEASE_BURDEN": "Disease Burden Need"
    }
    
    indicator_map = {
        "HIGH_DEMAND": dem_issue,
        "WORKFORCE_SHORTAGE": work_issue,
        "FACILITY_SHORTAGE": fac_issue,
        "DISEASE_BURDEN": f"High caseload of {row['jenis_penyakit_dominan']}"
    }
    
    indicator_val_map = {
        "HIGH_DEMAND": sorted_scores[0][1], # score
        "WORKFORCE_SHORTAGE": sorted_scores[0][1],
        "FACILITY_SHORTAGE": sorted_scores[0][1],
        "DISEASE_BURDEN": sorted_scores[0][1]
    }
    
    interpretation_map = {
        "HIGH_DEMAND": "tingginya volume populasi atau jumlah kunjungan puskesmas yang memberikan tekanan berat pada fasilitas setempat",
        "WORKFORCE_SHORTAGE": "keterbatasan jumlah tenaga kesehatan medis, terutama perawat, dibandingkan dengan kepadatan penduduk setempat",
        "FACILITY_SHORTAGE": "kurangnya ketersediaan fasilitas pelayanan kesehatan tingkat pertama (Puskesmas/Pustu) atau kapasitas tempat tidur rawat inap",
        "DISEASE_BURDEN": "besarnya prevalensi kasus penyakit masyarakat (terutama ISPA) yang memerlukan intervensi preventif dan promotif"
    }
    
    explanation = (
        f"Kecamatan {kec} memiliki Healthcare Gap Score sebesar {row['healthcare_gap_score']:.1f} "
        f"dan termasuk kategori {row['priority_category']}. Faktor kontributor utama adalah: "
        f"1. {label_map[primary_rc]} ({primary_score:.2f}), "
        f"2. {label_map[secondary_rc]} ({secondary_score:.2f}), "
        f"3. {label_map[tertiary_rc]} ({tertiary_score:.2f}). "
        f"Indikator paling menonjol dalam model adalah {indicator_map[primary_rc]}, "
        f"dengan sub-skor {primary_score:.2f}. Temuan ini menunjukkan adanya indikasi {interpretation_map[primary_rc]}."
    )
    
    rca_records.append({
        "kecamatan": kec,
        "healthcare_gap_score": row["healthcare_gap_score"],
        "priority_category": row["priority_category"],
        "priority_rank": row["priority_rank"],
        "demand_score": row["demand_score"],
        "workforce_gap": row["workforce_gap"],
        "facility_gap": row["facility_gap"],
        "disease_need_score": row["disease_need_score"],
        "accessibility_gap": row["accessibility_gap"],
        "primary_root_cause": primary_rc,
        "secondary_root_cause": secondary_rc,
        "tertiary_root_cause": tertiary_rc,
        "root_cause_type": rc_type,
        "root_cause_confidence": confidence,
        "root_cause_margin": margin,
        "workforce_issue": work_issue,
        "facility_issue": fac_issue,
        "demand_issue": dem_issue,
        "disease_issue": disease_issue,
        "accessibility_issue": access_issue,
        "explanation": explanation,
        "data_quality_status": row["data_quality_status"]
    })

df_rca = pd.DataFrame(rca_records)

# -----------------------------------------------------------------------------
# 2. SAVE RCA DATASET
# -----------------------------------------------------------------------------
df_rca.to_csv(os.path.join(PROCESSED_DIR_DATA, "root_cause_analysis.csv"), index=False)
df_rca.to_csv(os.path.join(PROCESSED_DIR_DATASET, "root_cause_analysis.csv"), index=False)
print("Saved root_cause_analysis.csv to processed folders.")

# -----------------------------------------------------------------------------
# 3. EXPORT ROOT CAUSE DICTIONARY LOG
# -----------------------------------------------------------------------------
dict_records = [
    {"root_cause_code": "HIGH_DEMAND", "root_cause_name": "High Demand Score", "trigger": "demand_score is the highest among components or >= 0.80", "interpretation": "Relative demographic volume or visits load is high", "recommended_analysis": "Examine population density and visits_per_1000 pressure"},
    {"root_cause_code": "WORKFORCE_SHORTAGE", "root_cause_name": "Workforce Shortage Gap", "trigger": "workforce_gap is the highest among components or >= 0.80", "interpretation": "Normalized nakes-to-population ratio is low", "recommended_analysis": "Examine perawat_per_1000 and nakes_per_1000 breakdowns"},
    {"root_cause_code": "FACILITY_SHORTAGE", "root_cause_name": "Facility Capacity Gap", "trigger": "facility_gap is the highest among components or >= 0.80", "interpretation": "Standardized faskes/pkm/pustu counts or beds per 1k pop is low", "recommended_analysis": "Examine faskes_per_100k, puskesmas_per_100k, and beds_per_1000"},
    {"root_cause_code": "DISEASE_BURDEN", "root_cause_name": "Disease Burden Need", "trigger": "disease_need_score is the highest among components or >= 0.80", "interpretation": "Cases per 1k pop is high", "recommended_analysis": "Examine detailed disease profiles to identify dominant illness drivers"},
    {"root_cause_code": "ACCESSIBILITY", "root_cause_name": "Accessibility Gap", "trigger": "accessibility_gap >= 0.80 (placeholder)", "interpretation": "Travel time or distance to nearest facility is high", "recommended_analysis": "Integrate spatial GIS network analyst buffers when coordinates are loaded"}
]
df_dict = pd.DataFrame(dict_records)
df_dict.to_csv(os.path.join(LOGS_DIR, "root_cause_dictionary.csv"), index=False)
print("Saved logs/root_cause_dictionary.csv.")

# -----------------------------------------------------------------------------
# 4. GENERATE VISUALIZATIONS
# -----------------------------------------------------------------------------
print("Generating visualizations under outputs/root_cause/...")

# A. root_cause_distribution.png
plt.figure(figsize=(10, 6))
sns.countplot(data=df_rca, x="primary_root_cause", palette="Set2")
plt.title("Distribution of Primary Root Cause Categories across Surabaya", pad=15)
plt.xlabel("Primary Root Cause Category")
plt.ylabel("Kecamatan Count")
plt.tight_layout()
plt.savefig(os.path.join(RCA_DIR, "root_cause_distribution.png"), dpi=150)
plt.close()

# B. root_cause_by_district.png (Bar chart showing Gap Score colored by Root Cause)
plt.figure(figsize=(14, 7))
df_sorted = df_rca.sort_values("healthcare_gap_score", ascending=False)
sns.barplot(data=df_sorted, x="kecamatan", y="healthcare_gap_score", hue="primary_root_cause", palette="Set2", dodge=False)
plt.title("Kecamatan Healthcare Gap Score by Primary Root Cause Driver", pad=15)
plt.xlabel("Kecamatan")
plt.ylabel("Healthcare Gap Score (0-100)")
plt.xticks(rotation=45, ha="right")
plt.legend(title="Primary Root Cause", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig(os.path.join(RCA_DIR, "root_cause_by_district.png"), dpi=150)
plt.close()

# C. component_heatmap.png (Heatmap of Kecamatan by component scores)
plt.figure(figsize=(12, 10))
df_heat = df_sorted.set_index("kecamatan")[["demand_score", "workforce_gap", "facility_gap", "disease_need_score"]]
sns.heatmap(df_heat, annot=True, cmap="YlOrRd", fmt=".2f", cbar=True)
plt.title("HEAL-CITY Kecamatan Gap Component Heatmap", pad=20)
plt.xlabel("Components")
plt.ylabel("Kecamatan (Sorted by Gap Score Descending)")
plt.tight_layout()
plt.savefig(os.path.join(RCA_DIR, "component_heatmap.png"), dpi=150)
plt.close()

# D. workforce_root_cause.png
plt.figure(figsize=(10, 6))
sns.countplot(data=df_rca, x="workforce_issue", palette="pastel")
plt.title("Distribution of Primary Workforce Issues", pad=15)
plt.xlabel("Primary Issue Category")
plt.ylabel("Kecamatan Count")
plt.tight_layout()
plt.savefig(os.path.join(RCA_DIR, "workforce_root_cause.png"), dpi=150)
plt.close()

# E. facility_root_cause.png
plt.figure(figsize=(10, 6))
sns.countplot(data=df_rca, x="facility_issue", palette="pastel")
plt.title("Distribution of Primary Facility Issues", pad=15)
plt.xlabel("Primary Issue Category")
plt.ylabel("Kecamatan Count")
plt.tight_layout()
plt.savefig(os.path.join(RCA_DIR, "facility_root_cause.png"), dpi=150)
plt.close()

# F. disease_root_cause.png
plt.figure(figsize=(10, 6))
sns.countplot(data=df_rca, x="demand_issue", palette="pastel")
plt.title("Distribution of Primary Demand Issues", pad=15)
plt.xlabel("Primary Issue Category")
plt.ylabel("Kecamatan Count")
plt.tight_layout()
plt.savefig(os.path.join(RCA_DIR, "disease_root_cause.png"), dpi=150)
plt.close()

# G. root_cause_contribution.png (Average component scores across Surabaya)
plt.figure(figsize=(10, 6))
df_avg = df_rca[["demand_score", "workforce_gap", "facility_gap", "disease_need_score"]].mean()
sns.barplot(x=df_avg.index, y=df_avg.values, palette="Set1")
plt.title("Average Component Deficit Scores Across Surabaya", pad=15)
plt.xlabel("Gap Component")
plt.ylabel("Average Score (0.0 - 1.0)")
plt.tight_layout()
plt.savefig(os.path.join(RCA_DIR, "root_cause_contribution.png"), dpi=150)
plt.close()

print("Saved all visualizations to outputs/root_cause/.")
print("HEAL-CITY Root Cause Analysis Pipeline Completed Successfully!")
