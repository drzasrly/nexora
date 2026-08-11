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
FEATURES_CSV_PATH = "dataset/processed/heal_city_features.csv"
PROCESSED_DIR_DATA = "data/processed"
PROCESSED_DIR_DATASET = "dataset/processed"
LOGS_DIR = "logs"
GAP_DIR = "outputs/gap_analysis"

# Create directories
os.makedirs(PROCESSED_DIR_DATA, exist_ok=True)
os.makedirs(PROCESSED_DIR_DATASET, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(GAP_DIR, exist_ok=True)

print("Starting HEAL-CITY Healthcare Gap Engine...")

# Load features dataset
assert os.path.exists(FEATURES_CSV_PATH), f"Features dataset not found at {FEATURES_CSV_PATH}!"
df = pd.read_csv(FEATURES_CSV_PATH)

# Helper function
def minmax(series):
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series(0.5, index=series.index)
    return (series - min_val) / (max_val - min_val)

# -----------------------------------------------------------------------------
# 1. COMPONENT CALCULATIONS
# -----------------------------------------------------------------------------
print("Calculating normalized components...")

# A. Demand Score
pop_demand = minmax(df["jumlah_penduduk"])
service_press = minmax(df["visits_per_1000"])
disease_need = minmax(df["disease_per_1000"])
df["demand_score"] = 0.30 * pop_demand + 0.40 * service_press + 0.30 * disease_need

# B. Workforce Gap
nakes_cap = minmax(df["nakes_per_1000"])
nurse_cap = minmax(df["perawat_per_1000"])
midwife_cap = minmax(df["bidan_per_1000"])
df["workforce_gap"] = 0.40 * (1.0 - nakes_cap) + 0.40 * (1.0 - nurse_cap) + 0.20 * (1.0 - midwife_cap)

# C. Facility Gap
faskes_cap = minmax(df["faskes_per_100k"])
pkm_cap = minmax(df["puskesmas_per_100k"])
pustu_cap = minmax(df["pustu_per_100k"])
bed_cap = minmax(df["beds_per_1000"])
df["facility_gap"] = 0.30 * (1.0 - faskes_cap) + 0.30 * (1.0 - pkm_cap) + 0.20 * (1.0 - pustu_cap) + 0.20 * (1.0 - bed_cap)

# D. Disease Need Score
df["disease_need_score"] = minmax(df["disease_per_1000"])

# E. Accessibility Gap (Spatial data missing, so NaN)
df["accessibility_gap"] = np.nan

# -----------------------------------------------------------------------------
# 2. BASELINE COMPOSITE HEALTHCARE GAP SCORE
# -----------------------------------------------------------------------------
print("Computing baseline composite gap score...")

# Baseline weight configuration (simplified from spec without accessibility)
w_demand = 0.30
w_workforce = 0.30
w_facility = 0.20
w_disease = 0.20

df["healthcare_gap_score"] = (
    w_demand * df["demand_score"] +
    w_workforce * df["workforce_gap"] +
    w_facility * df["facility_gap"] +
    w_disease * df["disease_need_score"]
) * 100.0

# Ensure score within [0, 100]
assert df["healthcare_gap_score"].between(0.0, 100.0).all(), "Error: Healthcare gap score out of bounds!"

# Priority Category Classification
def classify_priority(score):
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

df["priority_category"] = df["healthcare_gap_score"].apply(classify_priority)

# Priority Ranking
df["priority_rank"] = df["healthcare_gap_score"].rank(ascending=False, method="min").astype(int)

# -----------------------------------------------------------------------------
# 3. DATA QUALITY & DATA CONFIDENCE
# -----------------------------------------------------------------------------
# Core variables: penduduk, kunjungan, nakes, faskes, tempat tidur, penyakit. (6 indicators)
# Out of 8 possible indicators (6 core + 2 spatial distance & travel time placeholders)
df["data_completeness_score"] = 6.0 / 8.0 # 0.75
df["data_quality_status"] = "COMPLETE" # Core MVP data is 100% complete

# -----------------------------------------------------------------------------
# 4. EXPORT WEIGHTS LOG
# -----------------------------------------------------------------------------
weights_records = [
    {"component": "Demand Score", "weight": w_demand},
    {"component": "Workforce Gap", "weight": w_workforce},
    {"component": "Facility Gap", "weight": w_facility},
    {"component": "Disease Need Score", "weight": w_disease},
    {"component": "Accessibility Gap", "weight": 0.0}
]
df_weights = pd.DataFrame(weights_records)
df_weights.to_csv(os.path.join(LOGS_DIR, "healthcare_gap_weights.csv"), index=False)
print("Saved logs/healthcare_gap_weights.csv.")

# -----------------------------------------------------------------------------
# 5. SENSITIVITY ANALYSIS
# -----------------------------------------------------------------------------
print("Running Sensitivity Analysis across 4 scenarios...")

# Scenarios definition
scenarios = {
    "Scenario_A_Balanced": {"w_d": 0.30, "w_w": 0.30, "w_f": 0.20, "w_dis": 0.20},
    "Scenario_B_Redistributed": {"w_d": 0.294, "w_w": 0.294, "w_f": 0.235, "w_dis": 0.176},
    "Scenario_C_DemandFocus": {"w_d": 0.45, "w_w": 0.20, "w_f": 0.15, "w_dis": 0.20},
    "Scenario_D_CapacityFocus": {"w_d": 0.20, "w_w": 0.45, "w_f": 0.20, "w_dis": 0.15}
}

sens_ranks = {"kecamatan": df["kecamatan"].tolist()}
sens_scores = {"kecamatan": df["kecamatan"].tolist()}

for name, sc in scenarios.items():
    score_series = (
        sc["w_d"] * df["demand_score"] +
        sc["w_w"] * df["workforce_gap"] +
        sc["w_f"] * df["facility_gap"] +
        sc["w_dis"] * df["disease_need_score"]
    ) * 100.0
    sens_scores[name] = score_series
    sens_ranks[name] = score_series.rank(ascending=False, method="min").astype(int)

df_sens_ranks = pd.DataFrame(sens_ranks)
df_sens_scores = pd.DataFrame(sens_scores)

# Calculate rank variance and stability classification
rank_cols = [c for c in df_sens_ranks.columns if c != "kecamatan"]
df_sens_ranks["rank_variance"] = df_sens_ranks[rank_cols].var(axis=1)

def classify_stability(var):
    if var <= 1.0:
        return "High"
    elif var <= 4.0:
        return "Medium"
    else:
        return "Low"

df_sens_ranks["rank_stability"] = df_sens_ranks["rank_variance"].apply(classify_stability)
df_sens_ranks.to_csv(os.path.join(LOGS_DIR, "sensitivity_analysis.csv"), index=False)
print("Saved logs/sensitivity_analysis.csv.")

# -----------------------------------------------------------------------------
# 6. EXPORT FINAL HEALTHCARE GAP SCORES CSV
# -----------------------------------------------------------------------------
# Prepare export table matching spec
export_cols = [
    "kecamatan", "demand_score", "workforce_gap", "facility_gap", "disease_need_score", "accessibility_gap",
    "workforce_demand_mismatch", "healthcare_gap_score", "priority_category", "priority_rank",
    "data_completeness_score", "data_quality_status"
]
df_export_final = df[export_cols]

df_export_final.to_csv(os.path.join(PROCESSED_DIR_DATA, "healthcare_gap_scores.csv"), index=False)
df_export_final.to_csv(os.path.join(PROCESSED_DIR_DATASET, "healthcare_gap_scores.csv"), index=False)
print("Saved healthcare_gap_scores.csv to data/processed and dataset/processed.")

# -----------------------------------------------------------------------------
# 7. GENERATE VISUALIZATIONS
# -----------------------------------------------------------------------------
print("Generating figures under outputs/gap_analysis/...")

# Color palette variables
bar_color = "#3a86c8"
scatter_color = "#e05c5c"

# Sort by gap score for visual plots
df_sorted = df.sort_values("healthcare_gap_score", ascending=False)

# A. healthcare_gap_ranking.png
plt.figure(figsize=(12, 6))
sns.barplot(data=df_sorted, x="kecamatan", y="healthcare_gap_score", color=bar_color)
plt.title("HEAL-CITY Healthcare Gap Score Ranking by Kecamatan", pad=15)
plt.xlabel("Kecamatan")
plt.ylabel("Healthcare Gap Score (0-100)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(GAP_DIR, "healthcare_gap_ranking.png"), dpi=150)
plt.close()

# B. demand_vs_capacity.png (Demand vs inverse capacity gap)
# Capacity gap combined = 0.6 * Workforce gap + 0.4 * Facility gap
df["combined_capacity_gap"] = 0.6 * df["workforce_gap"] + 0.4 * df["facility_gap"]
plt.figure(figsize=(10, 8))
plt.scatter(df["combined_capacity_gap"], df["demand_score"], color=scatter_color, s=80, alpha=0.8, edgecolors="black")
for idx, row in df.iterrows():
    plt.annotate(row["kecamatan"], (row["combined_capacity_gap"], row["demand_score"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
plt.title("Healthcare Demand Score vs Combined Capacity Gap", pad=15)
plt.xlabel("Combined Capacity Gap (Higher = Worse)")
plt.ylabel("Demand Score (Higher = Worse)")
plt.tight_layout()
plt.savefig(os.path.join(GAP_DIR, "demand_vs_capacity.png"), dpi=150)
plt.close()

# C. gap_component_comparison.png (Stacked bar of top 10 Kecamatan)
df_top10 = df_sorted.head(10).copy()
df_top10_melted = df_top10.melt(
    id_vars="kecamatan", 
    value_vars=["demand_score", "workforce_gap", "facility_gap", "disease_need_score"],
    var_name="Component", 
    value_name="Score"
)
plt.figure(figsize=(12, 7))
sns.barplot(data=df_top10_melted, x="kecamatan", y="Score", hue="Component", palette="muted")
plt.title("HEAL-CITY Gap Component Comparison (Top 10 Kecamatan)", pad=15)
plt.xlabel("Kecamatan")
plt.ylabel("Normalized Component Score (0.0 - 1.0)")
plt.xticks(rotation=30, ha="right")
plt.legend(title="Components", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig(os.path.join(GAP_DIR, "gap_component_comparison.png"), dpi=150)
plt.close()

# D. workforce_gap.png
plt.figure(figsize=(12, 6))
sns.barplot(data=df.sort_values("workforce_gap", ascending=False), x="kecamatan", y="workforce_gap", color="#e76f51")
plt.title("HEAL-CITY Workforce Gap by Kecamatan", pad=15)
plt.xlabel("Kecamatan")
plt.ylabel("Workforce Gap (1 - Nakes Capacity)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(GAP_DIR, "workforce_gap.png"), dpi=150)
plt.close()

# E. facility_gap.png
plt.figure(figsize=(12, 6))
sns.barplot(data=df.sort_values("facility_gap", ascending=False), x="kecamatan", y="facility_gap", color="#f4a261")
plt.title("HEAL-CITY Facility Gap by Kecamatan", pad=15)
plt.xlabel("Kecamatan")
plt.ylabel("Facility Gap (1 - Facility Capacity)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(GAP_DIR, "facility_gap.png"), dpi=150)
plt.close()

# F. disease_need.png
plt.figure(figsize=(12, 6))
sns.barplot(data=df.sort_values("disease_need_score", ascending=False), x="kecamatan", y="disease_need_score", color="#2a9d8f")
plt.title("HEAL-CITY Disease Need Score by Kecamatan", pad=15)
plt.xlabel("Kecamatan")
plt.ylabel("Disease Need Score (Normalized Disease Burden)")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(GAP_DIR, "disease_need.png"), dpi=150)
plt.close()

# G. sensitivity_analysis.png (Line chart comparing Scenario Ranks of Top 10 Kecamatan)
top10_kec_names = df_top10["kecamatan"].tolist()
df_sens_top10 = df_sens_ranks[df_sens_ranks["kecamatan"].isin(top10_kec_names)].copy()
df_sens_top10 = df_sens_top10.set_index("kecamatan").reindex(top10_kec_names)
# Plot line comparisons
plt.figure(figsize=(12, 7))
for col in rank_cols:
    plt.plot(df_sens_top10.index, df_sens_top10[col], marker='o', label=col.replace("_", " "))
plt.gca().invert_yaxis() # Rank 1 is at the top
plt.title("Healthcare Gap Rank Sensitivity comparison (Top 10 Kecamatan)", pad=15)
plt.xlabel("Kecamatan")
plt.ylabel("Rank Number (1 = Highest Gap)")
plt.xticks(rotation=30, ha="right")
plt.legend(title="Scenarios")
plt.tight_layout()
plt.savefig(os.path.join(GAP_DIR, "sensitivity_analysis.png"), dpi=150)
plt.close()

print("Saved all visualizations to outputs/gap_analysis/.")
print("Healthcare Gap Engine pipeline execution completed successfully!")
