import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from src.feature_engineering import minmax

def determine_primary_root_cause(row):
    """Determine the component with the highest gap score."""
    values = {
        "HIGH_DEMAND": row["demand_score"],
        "WORKFORCE_SHORTAGE": row["workforce_gap"],
        "FACILITY_SHORTAGE": row["facility_gap"],
        "DISEASE_BURDEN": row["disease_need_score"]
    }
    if "accessibility_gap" in row.index and pd.notna(row["accessibility_gap"]):
        values["ACCESS_BARRIERS"] = row["accessibility_gap"]
    return max(values, key=values.get)

def rank_root_causes(row):
    """Sort components descending to get root cause ranking list."""
    values = {
        "HIGH_DEMAND": row["demand_score"],
        "WORKFORCE_SHORTAGE": row["workforce_gap"],
        "FACILITY_SHORTAGE": row["facility_gap"],
        "DISEASE_BURDEN": row["disease_need_score"]
    }
    if "accessibility_gap" in row.index and pd.notna(row["accessibility_gap"]):
        values["ACCESS_BARRIERS"] = row["accessibility_gap"]
    
    ranking = sorted(values.items(), key=lambda x: x[1], reverse=True)
    return ranking

def detect_multi_factor(row, threshold=0.80):
    """Classify the root cause type based on components crossing threshold."""
    components = [
        row["demand_score"],
        row["workforce_gap"],
        row["facility_gap"],
        row["disease_need_score"]
    ]
    if "accessibility_gap" in row.index and pd.notna(row["accessibility_gap"]) and row["accessibility_gap"] != 0.0:
        components.append(row["accessibility_gap"])
        
    high_count = sum(value >= threshold for value in components)
    
    if high_count >= 3:
        return "MULTI_FACTOR"
    elif high_count == 1:
        return "SINGLE_FACTOR"
    elif high_count == 0:
        return "NO_DOMINANT_ROOT_CAUSE"
    else:
        return "MULTI_FACTOR" # Fallback for 2 triggers

def calculate_root_cause_margin(ranking):
    """Calculate the margin difference between top two components."""
    if len(ranking) < 2:
        return 0.0
    return ranking[0][1] - ranking[1][1]

def run_root_cause_analysis(df_gap, df_feats, config):
    """Run full Root Cause Analysis pipeline: rank drivers, breakdowns, and plots."""
    processed_dir = config["data"]["processed_dir"]
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("outputs/root_cause", exist_ok=True)
    
    threshold_high = config["root_cause"]["threshold_high"]
    
    print("Running Root Cause Analysis (RCA)...")
    
    # Merge datasets cleanly without clashing columns
    scoring_cols = [
        "kecamatan", "demand_score", "workforce_gap", "facility_gap", "disease_need_score", 
        "accessibility_gap", "healthcare_gap_score", "priority_category", "priority_rank"
    ]
    df_gap_clean = df_gap[[c for c in scoring_cols if c in df_gap.columns]]
    df_feats_clean = df_feats.drop(columns=["accessibility_gap"], errors="ignore")
    df_m = pd.merge(df_gap_clean, df_feats_clean, on="kecamatan", how="left")
    
    rca_records = []
    
    for idx, row in df_m.iterrows():
        kec = row["kecamatan"]
        
        # Rankings
        ranking = rank_root_causes(row)
        primary_rc = ranking[0][0]
        secondary_rc = ranking[1][0]
        tertiary_rc = ranking[2][0]
        
        primary_score = ranking[0][1]
        secondary_score = ranking[1][1]
        tertiary_score = ranking[2][1]
        
        margin = calculate_root_cause_margin(ranking)
        
        # Dominance Classification
        if margin >= 0.20:
            dominance = "Dominant"
        elif margin >= 0.10:
            dominance = "Moderate"
        else:
            dominance = "Shared"
            
        # Root cause type classification
        rc_type = detect_multi_factor(row, threshold_high)
        
        # Confidence Level
        if primary_score >= 0.80 and margin >= 0.10:
            confidence = "HIGH"
        elif primary_score >= 0.60 or margin < 0.10:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
            
        # Granular breakdowns
        work_gaps = {
            "Low Nakes Ratio": 1.0 - minmax(df_m["nakes_per_1000"])[idx],
            "Low Nurse Ratio": 1.0 - minmax(df_m["perawat_per_1000"])[idx],
            "Low Midwife Ratio": 1.0 - minmax(df_m["bidan_per_1000"])[idx]
        }
        work_issue = max(work_gaps, key=work_gaps.get)
        
        fac_gaps = {
            "Low Faskes Ratio": 1.0 - minmax(df_m["faskes_per_100k"])[idx],
            "Low Puskesmas Ratio": 1.0 - minmax(df_m["puskesmas_per_100k"])[idx],
            "Low Pustu Ratio": 1.0 - minmax(df_m["pustu_per_100k"])[idx],
            "Low Bed Capacity": 1.0 - minmax(df_m["beds_per_1000"])[idx]
        }
        fac_issue = max(fac_gaps, key=fac_gaps.get)
        
        dem_scores = {
            "High Population Demand": minmax(df_m["jumlah_penduduk"])[idx],
            "High Service Pressure": minmax(df_m["visits_per_1000"])[idx],
            "High Disease Burden": minmax(df_m["disease_per_1000"])[idx]
        }
        dem_issue = max(dem_scores, key=dem_scores.get)
        
        disease_issue = f"{row['jenis_penyakit_dominan']} ({row['kasus_penyakit_tertinggi']} cases)" if pd.notna(row['jenis_penyakit_dominan']) else "N/A"
        access_issue = "NOT_AVAILABLE"
        
        # Narrative explanations
        label_map = {
            "HIGH_DEMAND": "High Demand Score",
            "WORKFORCE_SHORTAGE": "Workforce Shortage Gap",
            "FACILITY_SHORTAGE": "Facility Capacity Gap",
            "DISEASE_BURDEN": "Disease Burden Need",
            "ACCESS_BARRIERS": "Access Barriers Gap"
        }
        indicator_map = {
            "HIGH_DEMAND": dem_issue,
            "WORKFORCE_SHORTAGE": work_issue,
            "FACILITY_SHORTAGE": fac_issue,
            "DISEASE_BURDEN": f"High caseload of {row['jenis_penyakit_dominan']}",
            "ACCESS_BARRIERS": "distance/travel time to facilities"
        }
        interpretation_map = {
            "HIGH_DEMAND": "tingginya volume populasi atau jumlah kunjungan puskesmas yang memberikan tekanan berat pada fasilitas setempat",
            "WORKFORCE_SHORTAGE": "keterbatasan jumlah tenaga kesehatan medis, terutama perawat, dibandingkan dengan kepadatan penduduk setempat",
            "FACILITY_SHORTAGE": "kurangnya ketersediaan fasilitas pelayanan kesehatan tingkat pertama (Puskesmas/Pustu) atau kapasitas tempat tidur rawat inap",
            "DISEASE_BURDEN": "besarnya prevalensi kasus penyakit masyarakat (terutama ISPA) yang memerlukan intervensi preventif dan promotif",
            "ACCESS_BARRIERS": "keterbatasan aksesibilitas fisik dan transportasi menuju fasilitas kesehatan terdekat"
        }
        
        # Check priority category (handles keys properly)
        p_category = row.get("priority_category", "Tinggi")
        gap_score = row.get("healthcare_gap_score", 50.0)
        
        explanation = (
            f"Kecamatan {kec} memiliki Healthcare Gap Score sebesar {gap_score:.1f} "
            f"dan termasuk kategori {p_category}. Faktor kontributor utama adalah: "
            f"1. {label_map[primary_rc]} ({primary_score:.2f}), "
            f"2. {label_map[secondary_rc]} ({secondary_score:.2f}), "
            f"3. {label_map[tertiary_rc]} ({tertiary_score:.2f}). "
            f"Indikator paling menonjol dalam model adalah {indicator_map[primary_rc]}, "
            f"dengan sub-skor {primary_score:.2f}. Temuan ini menunjukkan adanya indikasi {interpretation_map[primary_rc]}."
        )
        
        rca_records.append({
            "kecamatan": kec,
            "healthcare_gap_score": gap_score,
            "priority_category": p_category,
            "priority_rank": row.get("priority_rank", 0),
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
            "data_quality_status": "COMPLETE"
        })
        
    df_rca = pd.DataFrame(rca_records)
    df_rca.to_csv(os.path.join(processed_dir, "root_cause_analysis.csv"), index=False)
    
    # Save log report dictionary
    dict_records = [
        {"root_cause_code": "HIGH_DEMAND", "root_cause_name": "High Demand Score", "trigger": "demand_score is the highest among components or >= 0.80", "interpretation": "Relative demographic volume or visits load is high", "recommended_analysis": "Examine population density and visits_per_1000 pressure"},
        {"root_cause_code": "WORKFORCE_SHORTAGE", "root_cause_name": "Workforce Shortage Gap", "trigger": "workforce_gap is the highest among components or >= 0.80", "interpretation": "Normalized nakes-to-population ratio is low", "recommended_analysis": "Examine perawat_per_1000 and nakes_per_1000 breakdowns"},
        {"root_cause_code": "FACILITY_SHORTAGE", "root_cause_name": "Facility Capacity Gap", "trigger": "facility_gap is the highest among components or >= 0.80", "interpretation": "Standardized faskes/pkm/pustu counts or beds per 1k pop is low", "recommended_analysis": "Examine faskes_per_100k, puskesmas_per_100k, and beds_per_1000"},
        {"root_cause_code": "DISEASE_BURDEN", "root_cause_name": "Disease Burden Need", "trigger": "disease_need_score is the highest among components or >= 0.80", "interpretation": "Cases per 1k pop is high", "recommended_analysis": "Examine detailed disease profiles to identify dominant illness drivers"},
        {"root_cause_code": "ACCESSIBILITY", "root_cause_name": "Accessibility Gap", "trigger": "accessibility_gap >= 0.80 (placeholder)", "interpretation": "Travel time or distance to nearest facility is high", "recommended_analysis": "Integrate spatial GIS network analyst buffers when coordinates are loaded"}
    ]
    pd.DataFrame(dict_records).to_csv("logs/root_cause_dictionary.csv", index=False)
    
    # Generate static plots
    print("Generating diagnostic plots...")
    sns.set_theme(style="whitegrid")
    
    # A. Distribution
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df_rca, x="primary_root_cause", palette="Set2")
    plt.title("Distribution of Primary Root Cause Categories")
    plt.xlabel("Primary Root Cause")
    plt.ylabel("Kecamatan Count")
    plt.tight_layout()
    plt.savefig("outputs/root_cause/root_cause_distribution.png", dpi=150)
    plt.close()
    
    # B. Heatmap
    plt.figure(figsize=(12, 10))
    df_sorted = df_rca.sort_values("healthcare_gap_score", ascending=False)
    df_heat = df_sorted.set_index("kecamatan")[["demand_score", "workforce_gap", "facility_gap", "disease_need_score"]]
    sns.heatmap(df_heat, annot=True, cmap="YlOrRd", fmt=".2f")
    plt.title("Kecamatan Gap Component Heatmap")
    plt.xlabel("Components")
    plt.ylabel("Kecamatan (Sorted by Gap Score Descending)")
    plt.tight_layout()
    plt.savefig("outputs/root_cause/component_heatmap.png", dpi=150)
    plt.close()
    
    # C. Workforce issues
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df_rca, x="workforce_issue", palette="pastel")
    plt.title("Distribution of Primary Workforce Issues")
    plt.xlabel("Workforce Issue Category")
    plt.ylabel("Kecamatan Count")
    plt.tight_layout()
    plt.savefig("outputs/root_cause/workforce_root_cause.png", dpi=150)
    plt.close()
    
    # D. Facility issues
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df_rca, x="facility_issue", palette="pastel")
    plt.title("Distribution of Primary Facility Issues")
    plt.xlabel("Facility Issue Category")
    plt.ylabel("Kecamatan Count")
    plt.tight_layout()
    plt.savefig("outputs/root_cause/facility_root_cause.png", dpi=150)
    plt.close()
    
    # E. Demand issues
    plt.figure(figsize=(10, 6))
    sns.countplot(data=df_rca, x="demand_issue", palette="pastel")
    plt.title("Distribution of Primary Demand Issues")
    plt.xlabel("Demand Issue Category")
    plt.ylabel("Kecamatan Count")
    plt.tight_layout()
    plt.savefig("outputs/root_cause/disease_root_cause.png", dpi=150)
    plt.close()
    
    # F. Gap Score Bar Chart
    plt.figure(figsize=(14, 7))
    sns.barplot(data=df_sorted, x="kecamatan", y="healthcare_gap_score", hue="primary_root_cause", palette="Set2", dodge=False)
    plt.title("Kecamatan Healthcare Gap Score by Primary Root Cause Driver")
    plt.xlabel("Kecamatan")
    plt.ylabel("Healthcare Gap Score (0-100)")
    plt.xticks(rotation=45, ha="right")
    plt.legend(title="Primary Root Cause", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig("outputs/root_cause/root_cause_by_district.png", dpi=150)
    plt.close()
    
    # G. Average deficit contribution
    plt.figure(figsize=(10, 6))
    df_avg = df_rca[["demand_score", "workforce_gap", "facility_gap", "disease_need_score"]].mean()
    sns.barplot(x=df_avg.index, y=df_avg.values, palette="Set1")
    plt.title("Average Component Deficit Scores Across Surabaya")
    plt.xlabel("Gap Component")
    plt.ylabel("Average Score")
    plt.tight_layout()
    plt.savefig("outputs/root_cause/root_cause_contribution.png", dpi=150)
    plt.close()
    
    print("Root Cause Analysis completed successfully. Visuals generated.")
    return df_rca
