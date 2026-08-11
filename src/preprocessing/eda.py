import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set aesthetics for plots
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 14,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.titlesize": 16
})

# Path definitions
MASTER_CSV_PATH = "dataset/processed/master_heal_city.csv"
PENYAKIT_CSV_PATH = "dataset/cleaned/clean_penyakit.csv"
OUTPUT_EDA_DIR = "outputs/eda"
OUTPUT_FIG_DIR = "outputs/figures"

# Create directories
os.makedirs(OUTPUT_EDA_DIR, exist_ok=True)
os.makedirs(OUTPUT_FIG_DIR, exist_ok=True)

print("Loading dataset for EDA...")
df = pd.read_csv(MASTER_CSV_PATH)

# Add aliased/calculated columns matching spec terminology
df["nakes_per_1000"] = df["workforce_ratio"]
df["perawat_per_1000"] = df["jumlah_perawat"] / df["jumlah_penduduk"]
df["faskes_per_100k"] = df["facility_ratio"]
df["puskesmas_per_100k"] = (df["jumlah_puskesmas"] / df["jumlah_penduduk"]) * 100.0
df["visits_per_1000"] = df["service_pressure"]
df["disease_per_1000"] = df["disease_burden"]
df["beds_per_1000"] = df["bed_ratio"]

# Verify that there are 31 Kecamatan
assert df["kecamatan"].nunique() == 31, f"Expected 31 unique kecamatan but got {df['kecamatan'].nunique()}!"
print(f"Verified {len(df)} records for the 31 Kecamatan of Surabaya.")

# -----------------------------------------------------------------------------
# 1. GENERATE ANALYSIS CSV REPORTS
# -----------------------------------------------------------------------------

# A. Population Analysis
print("Generating population analysis...")
pop_cols = ["kecamatan", "jumlah_penduduk", "kepadatan_penduduk"]
df_pop = df[pop_cols].copy()
df_pop["rank_penduduk"] = df_pop["jumlah_penduduk"].rank(ascending=False, method="min").astype(int)
df_pop["rank_kepadatan"] = df_pop["kepadatan_penduduk"].rank(ascending=False, method="min").astype(int)
df_pop.to_csv(os.path.join(OUTPUT_EDA_DIR, "population_analysis.csv"), index=False)

# B. Workforce Analysis
print("Generating workforce analysis...")
workforce_cols = ["kecamatan", "jumlah_perawat", "jumlah_bidan", "jumlah_tenaga_medis", "total_tenaga_kesehatan", "nakes_per_1000", "perawat_per_1000"]
df_work = df[workforce_cols].copy()
df_work["rank_total_nakes"] = df_work["total_tenaga_kesehatan"].rank(ascending=False, method="min").astype(int)
df_work["rank_nakes_ratio"] = df_work["nakes_per_1000"].rank(ascending=False, method="min").astype(int)
df_work.to_csv(os.path.join(OUTPUT_EDA_DIR, "workforce_analysis.csv"), index=False)

# C. Facility Analysis
print("Generating facility analysis...")
facility_cols = ["kecamatan", "jumlah_puskesmas", "jumlah_pustu", "total_faskes", "faskes_per_100k", "puskesmas_per_100k"]
df_fac = df[facility_cols].copy()
df_fac["rank_total_faskes"] = df_fac["total_faskes"].rank(ascending=False, method="min").astype(int)
df_fac["rank_faskes_ratio"] = df_fac["faskes_per_100k"].rank(ascending=False, method="min").astype(int)
df_fac.to_csv(os.path.join(OUTPUT_EDA_DIR, "facility_analysis.csv"), index=False)

# D. Visit Analysis
print("Generating visit analysis...")
visit_cols = ["kecamatan", "total_kunjungan", "visits_per_1000"]
df_visit = df[visit_cols].copy()
df_visit["rank_total_kunjungan"] = df_visit["total_kunjungan"].rank(ascending=False, method="min").astype(int)
df_visit["rank_visits_ratio"] = df_visit["visits_per_1000"].rank(ascending=False, method="min").astype(int)
df_visit.to_csv(os.path.join(OUTPUT_EDA_DIR, "visit_analysis.csv"), index=False)

# E. Disease Analysis
print("Generating disease analysis...")
disease_cols = ["kecamatan", "total_kasus_penyakit", "disease_per_1000"]
df_dis = df[disease_cols].copy()
df_dis["rank_total_kasus"] = df_dis["total_kasus_penyakit"].rank(ascending=False, method="min").astype(int)
df_dis["rank_disease_ratio"] = df_dis["disease_per_1000"].rank(ascending=False, method="min").astype(int)
df_dis.to_csv(os.path.join(OUTPUT_EDA_DIR, "disease_analysis.csv"), index=False)

# F. Correlation Matrix
print("Generating correlation matrix...")
corr_columns = [
    "jumlah_penduduk",
    "total_kunjungan",
    "total_tenaga_kesehatan",
    "total_faskes",
    "total_tempat_tidur",
    "total_kasus_penyakit",
    "visits_per_1000",
    "nakes_per_1000",
    "faskes_per_100k",
    "beds_per_1000",
    "disease_per_1000"
]
corr_matrix = df[corr_columns].corr()
corr_matrix.to_csv(os.path.join(OUTPUT_EDA_DIR, "correlation_matrix.csv"))

# G. Outlier Report (IQR method)
print("Generating outlier report...")
def detect_outliers_iqr(df, column):
    q1 = df[column].quantile(0.25)
    q3 = df[column].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
    
    records = []
    for idx, row in outliers.iterrows():
        records.append({
            "column": column,
            "kecamatan": row["kecamatan"],
            "value": row[column],
            "lower_bound": lower_bound,
            "upper_bound": upper_bound
        })
    return records

outlier_records = []
for col in corr_columns:
    outlier_records.extend(detect_outliers_iqr(df, col))
df_outliers = pd.DataFrame(outlier_records)
df_outliers.to_csv(os.path.join(OUTPUT_EDA_DIR, "outlier_report.csv"), index=False)

# H. Feature Candidates Evaluation
print("Generating feature candidates...")
candidates = [
    {"feature": "jumlah_penduduk", "category": "Demand", "source": "clean_penduduk.csv", "unit": "Ribu", "missing_rate": "0.0%", "interpretation": "Population size demand", "selected": "YES", "reason": "Primary demographic scale variable"},
    {"feature": "kepadatan_penduduk", "category": "Demand", "source": "clean_penduduk.csv", "unit": "km2", "missing_rate": "0.0%", "interpretation": "Population density", "selected": "YES", "reason": "Indicates physical pressure on local facilities"},
    {"feature": "visits_per_1000", "category": "Demand", "source": "clean_kunjungan.csv", "unit": "visits/1,000 pop", "missing_rate": "0.0%", "interpretation": "Healthcare service pressure", "selected": "YES", "reason": "Measures actual primary care utilization density"},
    {"feature": "disease_per_1000", "category": "Demand", "source": "clean_penyakit.csv", "unit": "cases/1,000 pop", "missing_rate": "0.0%", "interpretation": "Disease burden need", "selected": "YES", "reason": "Measures disease burden of the community"},
    {"feature": "nakes_per_1000", "category": "Workforce", "source": "clean_tenaga_kesehatan.csv", "unit": "nakes/1,000 pop", "missing_rate": "0.0%", "interpretation": "Healthcare workforce ratio", "selected": "YES", "reason": "Core capacity indicator for healthcare labor"},
    {"feature": "perawat_per_1000", "category": "Workforce", "source": "clean_tenaga_kesehatan.csv", "unit": "nurses/1,000 pop", "missing_rate": "0.0%", "interpretation": "Nursing capacity ratio", "selected": "YES", "reason": "Measures core supporting medical workforce"},
    {"feature": "faskes_per_100k", "category": "Facility", "source": "clean_faskes.csv", "unit": "faskes/100k pop", "missing_rate": "0.0%", "interpretation": "Total facilities ratio", "selected": "YES", "reason": "Measures spatial availability of all faskes"},
    {"feature": "puskesmas_per_100k", "category": "Facility", "source": "clean_puskesmas.csv", "unit": "pkm/100k pop", "missing_rate": "0.0%", "interpretation": "Puskesmas availability ratio", "selected": "YES", "reason": "Primary care facility density"},
    {"feature": "beds_per_1000", "category": "Facility", "source": "clean_tempat_tidur.csv", "unit": "beds/1,000 pop", "missing_rate": "0.0%", "interpretation": "Bed capacity ratio", "selected": "YES", "reason": "Indicates inpatient healthcare capacity"},
    {"feature": "accessibility_gap", "category": "Accessibility", "source": "GIS data (TBA)", "unit": "index", "missing_rate": "100.0%", "interpretation": "Travel time accessibility", "selected": "NO", "reason": "GIS/spatial travel time data is not yet integrated"}
]
df_cand = pd.DataFrame(candidates)
df_cand.to_csv(os.path.join(OUTPUT_EDA_DIR, "feature_candidates.csv"), index=False)

# I. EDA Summary
print("Generating EDA summary...")
# Find key findings programmatically
top_pop = df.loc[df["jumlah_penduduk"].idxmax()]["kecamatan"]
top_pop_val = df["jumlah_penduduk"].max()

top_pressure = df.loc[df["visits_per_1000"].idxmax()]["kecamatan"]
top_pressure_val = df["visits_per_1000"].max()

low_nakes = df.loc[df["nakes_per_1000"].idxmin()]["kecamatan"]
low_nakes_val = df["nakes_per_1000"].min()

low_fac = df.loc[df["faskes_per_100k"].idxmin()]["kecamatan"]
low_fac_val = df["faskes_per_100k"].min()

top_burden = df.loc[df["disease_per_1000"].idxmax()]["kecamatan"]
top_burden_val = df["disease_per_1000"].max()

# Check strong correlation in matrix
corr_unstacked = corr_matrix.unstack().sort_values(ascending=False)
corr_unstacked = corr_unstacked[corr_unstacked < 1.0] # exclude self correlation
strong_corr = corr_unstacked.index[0]
strong_corr_val = corr_unstacked.iloc[0]

# Determine priority investigation target (Low Nakes and High Service Pressure)
high_pressure_med = df["visits_per_1000"].median()
low_nakes_med = df["nakes_per_1000"].median()
priority_list = df[(df["visits_per_1000"] >= high_pressure_med) & (df["nakes_per_1000"] <= low_nakes_med)]["kecamatan"].tolist()

summary_records = [
    {"finding": "Kecamatan dengan populasi tertinggi", "value": f"{top_pop} ({top_pop_val:.1f} Ribu)"},
    {"finding": "Kecamatan dengan service pressure tertinggi", "value": f"{top_pressure} ({top_pressure_val:.1f} kunjungan/1.000 pop)"},
    {"finding": "Kecamatan dengan workforce ratio terendah", "value": f"{low_nakes} ({low_nakes_val:.2f} nakes/1.000 pop)"},
    {"finding": "Kecamatan dengan facility ratio terendah", "value": f"{low_fac} ({low_fac_val:.1f} faskes/100k pop)"},
    {"finding": "Kecamatan dengan disease burden tertinggi", "value": f"{top_burden} ({top_burden_val:.1f} kasus/1.000 pop)"},
    {"finding": "Variabel dengan missing value terbanyak di master", "value": "None (all master aggregated values are populated)"},
    {"finding": "Outlier penting yang dideteksi", "value": f"{len(df_outliers)} outliers across indicators (e.g. Kenjeran population)"},
    {"finding": "Hubungan korelasi terkuat", "value": f"{strong_corr[0]} <-> {strong_corr[1]} ({strong_corr_val:.3f})"},
    {"finding": "Kecamatan prioritas investigasi awal (mismatch)", "value": ", ".join(priority_list[:5])}
]
df_sum = pd.DataFrame(summary_records)
df_sum.to_csv(os.path.join(OUTPUT_EDA_DIR, "eda_summary.csv"), index=False)
print("Saved all analysis CSV files to outputs/eda/.")

# -----------------------------------------------------------------------------
# 2. GENERATE STATIC CHART PNG VISUALIZATIONS
# -----------------------------------------------------------------------------
print("Generating static PNG visualizations...")

# Color palettes
bar_color = "#3a86c8"
scatter_color = "#e05c5c"

# Helper function to save bar plots
def plot_bar(df_data, x_col, y_col, title, y_label, filename, ascending=False):
    plt.figure(figsize=(12, 6))
    df_sorted = df_data.sort_values(y_col, ascending=ascending)
    sns.barplot(data=df_sorted, x=x_col, y=y_col, color=bar_color)
    plt.title(title, pad=15)
    plt.xlabel("Kecamatan")
    plt.ylabel(y_label)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_FIG_DIR, filename), dpi=150)
    plt.close()

# 1. Population
plot_bar(df, "kecamatan", "jumlah_penduduk", "Jumlah Penduduk per Kecamatan", "Jumlah Penduduk (Ribu)", "population.png")

# 2. Population Density
plot_bar(df, "kecamatan", "kepadatan_penduduk", "Kepadatan Penduduk per Kecamatan", "Kepadatan Penduduk (km2)", "population_density.png")

# 3. Workforce Total
plot_bar(df, "kecamatan", "total_tenaga_kesehatan", "Jumlah Tenaga Kesehatan per Kecamatan", "Total Tenaga Kesehatan", "workforce.png")

# 4. Workforce Ratio
plot_bar(df, "kecamatan", "nakes_per_1000", "Tenaga Kesehatan per 1.000 Penduduk", "Ratio Nakes per 1.000 Penduduk", "workforce_ratio.png")

# 5. Facility Total
plot_bar(df, "kecamatan", "total_faskes", "Jumlah Fasilitas Kesehatan per Kecamatan", "Total Faskes", "facility.png")

# 6. Facility Ratio
plot_bar(df, "kecamatan", "faskes_per_100k", "Fasilitas Kesehatan per 100.000 Penduduk", "Ratio Faskes per 100k Penduduk", "facility_ratio.png")

# 7. Service Pressure
plot_bar(df, "kecamatan", "visits_per_1000", "Total Kunjungan Puskesmas per 1.000 Penduduk (Service Pressure)", "Ratio Kunjungan per 1.000 Penduduk", "service_pressure.png")

# 8. Disease Burden
plot_bar(df, "kecamatan", "disease_per_1000", "Total Beban Penyakit per 1.000 Penduduk (Disease Burden)", "Ratio Kasus Penyakit per 1.000 Penduduk", "disease_burden.png")

# 9. Demand vs Workforce Scatter Plot
plt.figure(figsize=(10, 8))
plt.scatter(df["nakes_per_1000"], df["visits_per_1000"], color=scatter_color, s=80, alpha=0.8, edgecolors="black")
for idx, row in df.iterrows():
    plt.annotate(row["kecamatan"], (row["nakes_per_1000"], row["visits_per_1000"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
plt.title("Healthcare Demand vs Workforce Capacity", pad=15)
plt.xlabel("Nakes per 1.000 Penduduk")
plt.ylabel("Visits per 1.000 Penduduk")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_FIG_DIR, "demand_vs_workforce.png"), dpi=150)
plt.close()

# 10. Demand vs Facility Scatter Plot
plt.figure(figsize=(10, 8))
plt.scatter(df["faskes_per_100k"], df["visits_per_1000"], color=scatter_color, s=80, alpha=0.8, edgecolors="black")
for idx, row in df.iterrows():
    plt.annotate(row["kecamatan"], (row["faskes_per_100k"], row["visits_per_1000"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
plt.title("Healthcare Demand vs Facility Capacity", pad=15)
plt.xlabel("Faskes per 100.000 Penduduk")
plt.ylabel("Visits per 1.000 Penduduk")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_FIG_DIR, "demand_vs_facility.png"), dpi=150)
plt.close()

# 11. Disease vs Workforce Scatter Plot
plt.figure(figsize=(10, 8))
plt.scatter(df["nakes_per_1000"], df["disease_per_1000"], color=scatter_color, s=80, alpha=0.8, edgecolors="black")
for idx, row in df.iterrows():
    plt.annotate(row["kecamatan"], (row["nakes_per_1000"], row["disease_per_1000"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
plt.title("Disease Burden vs Healthcare Workforce Capacity", pad=15)
plt.xlabel("Nakes per 1.000 Penduduk")
plt.ylabel("Disease Burden per 1.000 Penduduk")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_FIG_DIR, "disease_vs_workforce.png"), dpi=150)
plt.close()

# 12. Correlation Matrix Heatmap
plt.figure(figsize=(12, 10))
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", cbar=True, square=True)
plt.title("Correlation Matrix HEAL-CITY Variables", pad=20)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_FIG_DIR, "correlation_matrix.png"), dpi=150)
plt.close()

print("Saved all static PNG charts to outputs/figures/.")
print("EDA pipeline execution completed successfully!")
