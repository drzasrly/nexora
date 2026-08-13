import os
import datetime
import json
import numpy as np
import pandas as pd

# Standard Official Kecamatan list
OFFICIAL_KECAMATAN = [
    "Asemrowo", "Benowo", "Bubutan", "Bulak", "Dukuh Pakis", "Gayungan", "Genteng",
    "Gubeng", "Gunung Anyar", "Jambangan", "Karang Pilang", "Kenjeran", "Krembangan",
    "Lakarsantri", "Mulyorejo", "Pabean Cantian", "Pakal", "Rungkut", "Sambikerep",
    "Sawahan", "Semampir", "Simokerto", "Suko Manunggal", "Sukolilo", "Tambaksari",
    "Tandes", "Tegalsari", "Tenggilis Mejoyo", "Wiyung", "Wonocolo", "Wonokromo"
]

# Kecamatan name mappings
KECAMATAN_MAPPING = {
    "Asem Rowo": "Asemrowo",
    "Sukomanunggal": "Suko Manunggal",
    "Tenggilis": "Tenggilis Mejoyo",
    "SEMAMPIR": "Semampir",
    "SUKOLILO": "Sukolilo",
    "WONOCOLO": "Wonocolo",
    "pakal": "Pakal",
    "sukolilo": "Sukolilo"
}

cleaning_log_entries = []

def log_cleaning_action(dataset, row_id, column, original, new, action, reason):
    """Log a data cleaning action."""
    cleaning_log_entries.append({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dataset": dataset,
        "row_identifier": str(row_id),
        "column": column,
        "original_value": str(original) if pd.notna(original) else "NaN",
        "new_value": str(new) if pd.notna(new) else "NaN",
        "action": action,
        "reason": reason
    })

def standardize_columns(df):
    """Standardize column names to lowercase and underscores."""
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("/", "_", regex=False)
        .str.replace("-", "_", regex=False)
        .str.replace(r"_+", "_", regex=True)
    )
    return df

def clean_text(value):
    """Clean text by stripping and removing duplicate spaces."""
    if pd.isna(value):
        return pd.NA
    return " ".join(str(value).strip().split())

def apply_text_cleaning(df):
    """Clean all string-typed columns in a DataFrame."""
    df = df.copy()
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(clean_text)
    return df

def clean_disease_value(val):
    """Correct dot separator thousands errors in disease caseload floats."""
    if pd.isna(val):
        return pd.NA
    try:
        val_str = str(val).strip()
        if "." in val_str:
            f_val = float(val_str)
            if f_val % 1 != 0:
                return int(round(f_val * 1000))
            else:
                return int(f_val)
        else:
            return int(float(val_str))
    except Exception:
        try:
            val_str = str(val).replace(".", "").strip()
            return int(float(val_str))
        except Exception:
            return pd.NA

def run_preprocessing(config):
    """Run full HEAL-CITY preprocessing pipeline based on configuration settings."""
    excel_path = config["data"]["raw_excel"]
    cleaned_dir = config["data"]["cleaned_dir"]
    processed_dir = config["data"]["processed_dir"]
    
    os.makedirs(cleaned_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    print("Pre-processing Raw Excel Workbook...")
    excel = pd.ExcelFile(excel_path)
    dq_report_records = []
    
    # 1. PENDUDUK
    df_raw_penduduk = pd.read_excel(excel, sheet_name="penduduk")
    dups_pend = df_raw_penduduk.duplicated().sum()
    df_clean_pend = standardize_columns(df_raw_penduduk)
    df_clean_pend = apply_text_cleaning(df_clean_pend)
    df_clean_pend["kecamatan"] = df_clean_pend["kecamatan"].replace(KECAMATAN_MAPPING)
    
    for idx, row in df_raw_penduduk.iterrows():
        orig_kec = str(row["Kecamatan"]).strip()
        norm_kec = KECAMATAN_MAPPING.get(orig_kec, orig_kec)
        if orig_kec != norm_kec and orig_kec.lower() != "surabaya":
            log_cleaning_action("penduduk", orig_kec, "kecamatan", orig_kec, norm_kec, "name normalization", "standardizing kecamatan name")
            
    df_clean_pend = df_clean_pend[df_clean_pend["kecamatan"].str.lower() != "surabaya"]
    df_clean_pend = df_clean_pend.rename(columns={
        "jumlah_penduduk_(ribu)": "jumlah_penduduk",
        "laju_pertumbuhan_penduduk_per_tahun": "laju_pertumbuhan",
        "kepadatan_penduduk_per_km_persegi_(km2)": "kepadatan_penduduk",
        "rasio_jenis_kelamin_penduduk": "rasio_jenis_kelamin"
    })
    df_clean_pend = df_clean_pend[[
        "kecamatan", "jumlah_penduduk", "laju_pertumbuhan", 
        "persentase_penduduk", "kepadatan_penduduk", "rasio_jenis_kelamin"
    ]]
    df_clean_pend.to_csv(os.path.join(cleaned_dir, "clean_penduduk.csv"), index=False)
    
    dq_report_records.append({
        "dataset": "penduduk", "total_rows": len(df_clean_pend), "duplicate_rows": dups_pend,
        "missing_values": df_clean_pend.isna().sum().sum(), "invalid_values": 0,
        "unmatched_kecamatan": df_clean_pend[~df_clean_pend["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0],
        "unmatched_puskesmas": 0, "outlier_count": 0, "status": "READY"
    })

    # 2. TENAGA KESEHATAN
    df_raw_nakes = pd.read_excel(excel, sheet_name="tenaga kesehatan")
    dups_nakes = df_raw_nakes.duplicated().sum()
    df_clean_nakes = standardize_columns(df_raw_nakes)
    df_clean_nakes = apply_text_cleaning(df_clean_nakes)
    df_clean_nakes["kecamatan"] = df_clean_nakes["kecamatan"].replace(KECAMATAN_MAPPING)
    df_clean_nakes = df_clean_nakes[df_clean_nakes["kecamatan"].str.lower() != "surabaya"]
    
    workforce_cols = [c for c in df_clean_nakes.columns if c != "kecamatan"]
    for col in workforce_cols:
        orig_col_series = df_clean_nakes[col].copy()
        df_clean_nakes[col] = df_clean_nakes[col].replace(["–", "-", "—"], pd.NA)
        df_clean_nakes[col] = pd.to_numeric(df_clean_nakes[col], errors="coerce")
        for idx, (orig, new) in enumerate(zip(orig_col_series, df_clean_nakes[col])):
            if str(orig) != str(new) and pd.notna(orig):
                kec_val = df_clean_nakes.iloc[idx]["kecamatan"]
                log_cleaning_action("tenaga kesehatan", kec_val, col, orig, new, "type coercion", "coercing to numeric and handling dash values")
                
    nakes_rename_dict = {
        "tenaga_kesehatan_perawat": "perawat", "tenaga_kesehatan_bidan": "bidan",
        "tenaga_kesehatan_tenaga_kefarmasian": "tenaga_kefarmasian",
        "tenaga_kesehatan_tenaga_kesehatan_masyarakat": "tenaga_kesehatan_masyarakat",
        "tenaga_kesehatan_tenaga_kesehatan_lingkungan": "tenaga_kesehatan_lingkungan",
        "tenaga_kesehatan_tenaga_gizi": "tenaga_gizi", "jumlah_tenaga_medis": "tenaga_medis",
        "jumlah_tenaga_kesehatan_psikologi_klinis": "psikologi_klinis",
        "jumlah_tenaga_keterapian_fisik": "keterapian_fisik", "jumlah_tenaga_keteknisan_medis": "keteknisan_medis",
        "jumlah_tenaga_teknik_biomedika": "teknik_biomedika", "jumlah_tenaga_kesehatan_tradisional": "tenaga_kesehatan_tradisional"
    }
    df_clean_nakes = df_clean_nakes.rename(columns=nakes_rename_dict)
    df_clean_nakes = df_clean_nakes[[
        "kecamatan", "perawat", "bidan", "tenaga_kefarmasian", "tenaga_kesehatan_masyarakat",
        "tenaga_kesehatan_lingkungan", "tenaga_gizi", "tenaga_medis", "psikologi_klinis",
        "keterapian_fisik", "keteknisan_medis", "teknik_biomedika", "tenaga_kesehatan_tradisional"
    ]]
    df_clean_nakes.to_csv(os.path.join(cleaned_dir, "clean_tenaga_kesehatan.csv"), index=False)
    
    dq_report_records.append({
        "dataset": "tenaga kesehatan", "total_rows": len(df_clean_nakes), "duplicate_rows": dups_nakes,
        "missing_values": df_clean_nakes.isna().sum().sum(), "invalid_values": 0,
        "unmatched_kecamatan": df_clean_nakes[~df_clean_nakes["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0],
        "unmatched_puskesmas": 0, "outlier_count": 0, "status": "READY"
    })

    # 3. PUSKESMAS MASTER
    df_raw_pkm = pd.read_excel(excel, sheet_name="puskemas")
    dups_pkm = df_raw_pkm.duplicated().sum()
    df_clean_pkm = standardize_columns(df_raw_pkm)
    df_clean_pkm = apply_text_cleaning(df_clean_pkm)
    df_clean_pkm["puskesmas_id"] = [f"PKM{i+1:03d}" for i in range(len(df_clean_pkm))]
    
    df_kunj_raw = pd.read_excel(excel, sheet_name="kunjungan puskesmas", header=2)
    df_kunj_raw = standardize_columns(df_kunj_raw)
    df_kunj_raw = apply_text_cleaning(df_kunj_raw)
    
    pkm_kec_map = {}
    for idx, row in df_kunj_raw.iterrows():
        raw_pkm_name = str(row["nama_puskesmas"]).strip()
        raw_kec = str(row["kecamatan"]).strip()
        clean_pkm = raw_pkm_name
        if clean_pkm.lower().startswith("puskesmas "):
            clean_pkm = clean_pkm[len("puskesmas "):].strip()
        if clean_pkm == "Moro Krembangan":
            clean_pkm = "Morokrembangan"
        norm_kec = KECAMATAN_MAPPING.get(raw_kec, raw_kec)
        pkm_kec_map[clean_pkm.lower()] = norm_kec
        
    df_clean_pkm["kecamatan"] = df_clean_pkm["puskesmas"].apply(lambda x: pkm_kec_map.get(str(x).strip().lower(), pd.NA))
    df_clean_pkm = df_clean_pkm.rename(columns={"puskesmas": "nama_puskesmas"})
    df_clean_pkm = df_clean_pkm[[
        "puskesmas_id", "nama_puskesmas", "kecamatan", "alamat", "telepon", "pelayanan_unggulan"
    ]]
    df_clean_pkm.to_csv(os.path.join(cleaned_dir, "clean_puskesmas.csv"), index=False)

    mapping_pkm_entries = []
    for idx, row in df_kunj_raw.iterrows():
        raw_name = str(row["nama_puskesmas"]).strip()
        clean_name = raw_name[len("puskesmas "):].strip() if raw_name.lower().startswith("puskesmas ") else raw_name
        mapped_std = "Morokrembangan" if clean_name == "Moro Krembangan" else clean_name
        matching_pkm = df_clean_pkm[df_clean_pkm["nama_puskesmas"].str.lower() == mapped_std.lower()]
        pkm_id = matching_pkm.iloc[0]["puskesmas_id"] if len(matching_pkm) > 0 else "UNKNOWN"
        kec_val = KECAMATAN_MAPPING.get(str(row["kecamatan"]).strip(), str(row["kecamatan"]).strip())
        mapping_pkm_entries.append({
            "nama_asli": clean_name, "nama_standar": mapped_std, "puskesmas_id": pkm_id,
            "kecamatan": kec_val, "status": "mapped" if pkm_id != "UNKNOWN" else "unmapped"
        })
    pd.DataFrame(mapping_pkm_entries).drop_duplicates().to_csv("logs/mapping_puskesmas.csv", index=False)
    
    dq_report_records.append({
        "dataset": "puskesmas", "total_rows": len(df_clean_pkm), "duplicate_rows": dups_pkm,
        "missing_values": df_clean_pkm.isna().sum().sum(), "invalid_values": 0,
        "unmatched_kecamatan": df_clean_pkm[~df_clean_pkm["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0],
        "unmatched_puskesmas": 0, "outlier_count": 0, "status": "READY"
    })

    # 4. KUNJUNGAN
    df_kunj_clean = standardize_columns(df_kunj_raw)
    df_kunj_clean = apply_text_cleaning(df_kunj_clean)
    df_kunj_clean["kecamatan"] = df_kunj_clean["kecamatan"].replace(KECAMATAN_MAPPING)
    
    def match_pkm_id(row):
        raw_name = str(row["nama_puskesmas"]).strip()
        clean_name = raw_name[len("puskesmas "):].strip() if raw_name.lower().startswith("puskesmas ") else raw_name
        if clean_name == "Moro Krembangan":
            clean_name = "Morokrembangan"
        match = df_clean_pkm[df_clean_pkm["nama_puskesmas"].str.lower() == clean_name.lower()]
        return match.iloc[0]["puskesmas_id"] if len(match) > 0 else pd.NA
        
    df_kunj_clean["puskesmas_id"] = df_kunj_clean.apply(match_pkm_id, axis=1)
    
    months_ind = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    long_records = []
    for idx, row in df_kunj_clean.iterrows():
        pkm_id = row["puskesmas_id"]
        kec = row["kecamatan"]
        if pd.isna(pkm_id):
            continue
        for m in months_ind:
            m_lower = m.lower()
            val_baru = row.get(f"{m_lower}_baru", pd.NA)
            val_lama = row.get(f"{m_lower}_lama", pd.NA)
            val_total = row.get(f"{m_lower}_total", pd.NA)
            long_records.append({
                "puskesmas_id": pkm_id, "kecamatan": kec, "bulan": m,
                "pasien_baru": val_baru, "pasien_lama": val_lama, "total_kunjungan": val_total
            })
            
    df_kunj_long = pd.DataFrame(long_records)
    df_kunj_resolved = df_kunj_long.groupby(["puskesmas_id", "kecamatan", "bulan"], as_index=False, dropna=False).first()
    df_kunj_resolved["pasien_baru"] = pd.to_numeric(df_kunj_resolved["pasien_baru"], errors="coerce")
    df_kunj_resolved["pasien_lama"] = pd.to_numeric(df_kunj_resolved["pasien_lama"], errors="coerce")
    df_kunj_resolved["total_kunjungan"] = pd.to_numeric(df_kunj_resolved["total_kunjungan"], errors="coerce")
    df_kunj_resolved.to_csv(os.path.join(cleaned_dir, "clean_kunjungan.csv"), index=False)
    
    dq_report_records.append({
        "dataset": "kunjungan", "total_rows": len(df_kunj_resolved), "duplicate_rows": 0,
        "missing_values": df_kunj_resolved.isna().sum().sum(), "invalid_values": 0,
        "unmatched_kecamatan": df_kunj_resolved[~df_kunj_resolved["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0],
        "unmatched_puskesmas": df_kunj_resolved["puskesmas_id"].isna().sum(), "outlier_count": 0, "status": "READY"
    })

    # 5. FASKES
    df_raw_faskes = pd.read_excel(excel, sheet_name="faskes")
    dups_faskes = df_raw_faskes.duplicated().sum()
    df_clean_faskes = standardize_columns(df_raw_faskes)
    df_clean_faskes = apply_text_cleaning(df_clean_faskes)
    df_clean_faskes["kecamatan"] = df_clean_faskes["kecamatan"].replace(KECAMATAN_MAPPING)
    df_clean_faskes["status_lokasi"] = "mapped"
    df_clean_faskes.loc[df_clean_faskes["kecamatan"].isna(), "status_lokasi"] = "unknown"
    df_clean_faskes.loc[~df_clean_faskes["kecamatan"].isin(OFFICIAL_KECAMATAN) & df_clean_faskes["kecamatan"].notna(), "status_lokasi"] = "unknown"
    df_clean_faskes.loc[df_clean_faskes["status_lokasi"] == "unknown", "kecamatan"] = pd.NA
    df_clean_faskes = df_clean_faskes.rename(columns={"_id": "generated_faskes_id", "penyelenggara_faskes": "penyelenggara"})
    df_clean_faskes["generated_faskes_id"] = [f"FSK{i+1:04d}" for i in range(len(df_clean_faskes))]
    df_clean_faskes = df_clean_faskes[[
        "generated_faskes_id", "kecamatan", "jenis_faskes", "nama_faskes", "penyelenggara", "status_lokasi"
    ]]
    df_clean_faskes.to_csv(os.path.join(cleaned_dir, "clean_faskes.csv"), index=False)
    
    dq_report_records.append({
        "dataset": "faskes", "total_rows": len(df_clean_faskes), "duplicate_rows": dups_faskes,
        "missing_values": df_clean_faskes.isna().sum().sum(), "invalid_values": 0,
        "unmatched_kecamatan": df_clean_faskes[(df_clean_faskes["status_lokasi"] == "mapped") & (~df_clean_faskes["kecamatan"].isin(OFFICIAL_KECAMATAN))].shape[0],
        "unmatched_puskesmas": 0, "outlier_count": 0, "status": "READY"
    })

    # 6. TEMPAT TIDUR
    df_raw_bed = pd.read_excel(excel, sheet_name="tempat tidur")
    dups_bed = df_raw_bed.duplicated().sum()
    df_clean_bed = standardize_columns(df_raw_bed)
    df_clean_bed = apply_text_cleaning(df_clean_bed)
    df_clean_bed["kecamatan"] = df_clean_bed["kecamatan"].replace(KECAMATAN_MAPPING)
    df_clean_bed["kapasitas_tempat_tidur"] = pd.to_numeric(df_clean_bed["kapasitas_tempat_tidur"], errors="coerce")
    df_clean_bed = df_clean_bed.rename(columns={"penyelenggara_faskes": "penyelenggara"})
    df_clean_bed["tipe_kelas"] = pd.NA
    df_clean_bed = df_clean_bed[[
        "kecamatan", "jenis_faskes", "penyelenggara", "nama_faskes", "tipe_kelas", "kapasitas_tempat_tidur"
    ]]
    df_clean_bed.to_csv(os.path.join(cleaned_dir, "clean_tempat_tidur.csv"), index=False)
    
    dq_report_records.append({
        "dataset": "tempat tidur", "total_rows": len(df_clean_bed), "duplicate_rows": dups_bed,
        "missing_values": df_clean_bed.isna().sum().sum(), "invalid_values": 0,
        "unmatched_kecamatan": df_clean_bed[~df_clean_bed["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0],
        "unmatched_puskesmas": 0, "outlier_count": 0, "status": "READY"
    })

    # 7. DATA PENYAKIT
    df_raw_peny = pd.read_excel(excel, sheet_name="data penyakit")
    df_peny_clean = apply_text_cleaning(df_raw_peny)
    
    months_cols_raw = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    for m_col in months_cols_raw:
        df_peny_clean[m_col] = df_peny_clean[m_col].apply(clean_disease_value)
        
    df_peny_full = df_peny_clean.iloc[0:1323].copy().reset_index(drop=True)
    df_peny_jan_only = df_peny_clean.iloc[1325:].copy().reset_index(drop=True)
    
    df_peny_full = standardize_columns(df_peny_full)
    df_peny_jan_only = standardize_columns(df_peny_jan_only)
    
    key_cols = ['kecamatan', 'nama_faskes_(rumah_sakit_dan_puskesmas)', 'jenis_penyakit']
    df_peny_full["key_merge"] = df_peny_full[key_cols].astype(str).agg('_'.join, axis=1).str.strip().str.lower()
    df_peny_jan_only["key_merge"] = df_peny_jan_only[key_cols].astype(str).agg('_'.join, axis=1).str.strip().str.lower()
    
    for idx, row in df_peny_jan_only.iterrows():
        key = row["key_merge"]
        jan_val = row["januari"]
        match = df_peny_full[df_peny_full["key_merge"] == key]
        if len(match) > 0:
            feb_val_full = match.iloc[0]["februari"]
            if str(jan_val) == str(feb_val_full):
                df_peny_jan_only.at[idx, "februari"] = jan_val
                df_peny_jan_only.at[idx, "januari"] = pd.NA
                log_cleaning_action("data penyakit", f"Row {idx}", "januari/februari", jan_val, jan_val, "suspected_shifted_february", "anomaly fix")
                
    df_peny_combined = pd.concat([df_peny_full, df_peny_jan_only], ignore_index=True)
    months_cols_clean = [m.lower() for m in months_cols_raw]
    df_peny_resolved = df_peny_combined.groupby(key_cols, as_index=False, dropna=False)[months_cols_clean].first()
    
    df_peny_long = df_peny_resolved.melt(id_vars=key_cols, value_vars=months_cols_clean, var_name="bulan", value_name="jumlah_kasus")
    df_peny_long["bulan"] = df_peny_long["bulan"].str.capitalize()
    df_peny_long = df_peny_long.rename(columns={"nama_faskes_(rumah_sakit_dan_puskesmas)": "nama_faskes"})
    df_peny_long["kecamatan"] = df_peny_long["kecamatan"].replace(KECAMATAN_MAPPING)
    df_peny_long["jumlah_kasus"] = pd.to_numeric(df_peny_long["jumlah_kasus"], errors="coerce")
    df_peny_long = df_peny_long[["kecamatan", "nama_faskes", "jenis_penyakit", "bulan", "jumlah_kasus"]]
    df_peny_long.to_csv(os.path.join(cleaned_dir, "clean_penyakit.csv"), index=False)
    
    dq_report_records.append({
        "dataset": "data penyakit", "total_rows": len(df_peny_long), "duplicate_rows": 0,
        "missing_values": df_peny_long.isna().sum().sum(), "invalid_values": 0,
        "unmatched_kecamatan": df_peny_long[~df_peny_long["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0],
        "unmatched_puskesmas": 0, "outlier_count": 0, "status": "READY"
    })
    
    # Write quality metrics
    pd.DataFrame(dq_report_records).to_csv("logs/data_quality_report.csv", index=False)
    pd.DataFrame(cleaning_log_entries).to_csv("logs/cleaning_log.csv", index=False)
    
    # -------------------------------------------------------------------------
    # MASTER COMPILATION
    # -------------------------------------------------------------------------
    print("Compiling master_heal_city.csv...")
    df_master = pd.DataFrame({"kecamatan": OFFICIAL_KECAMATAN})
    
    # Penduduk
    df_master = pd.merge(df_master, df_clean_pend[["kecamatan", "jumlah_penduduk", "kepadatan_penduduk"]], on="kecamatan", how="left")
    
    # Nakes
    nakes_cols = ["perawat", "bidan", "tenaga_medis"]
    df_master = pd.merge(df_master, df_clean_nakes[["kecamatan"] + nakes_cols], on="kecamatan", how="left")
    df_clean_nakes["total_tenaga_kesehatan"] = df_clean_nakes.drop(columns=["kecamatan"]).sum(axis=1)
    df_master = pd.merge(df_master, df_clean_nakes[["kecamatan", "total_tenaga_kesehatan"]], on="kecamatan", how="left")
    df_master = df_master.rename(columns={
        "perawat": "jumlah_perawat", "bidan": "jumlah_bidan", "tenaga_medis": "jumlah_tenaga_medis"
    })
    
    # Faskes
    pkm_counts = df_clean_pkm.groupby("kecamatan").size().rename("jumlah_puskesmas")
    pustu_counts = df_clean_faskes[df_clean_faskes["jenis_faskes"].str.lower() == "puskesmas pembantu"].groupby("kecamatan").size().rename("jumlah_pustu")
    faskes_counts = df_clean_faskes.groupby("kecamatan").size().rename("total_faskes")
    beds_capacity = df_clean_bed.groupby("kecamatan")["kapasitas_tempat_tidur"].sum().rename("total_tempat_tidur")
    
    df_master = pd.merge(df_master, pkm_counts, on="kecamatan", how="left").fillna({"jumlah_puskesmas": 0})
    df_master = pd.merge(df_master, pustu_counts, on="kecamatan", how="left").fillna({"jumlah_pustu": 0})
    df_master = pd.merge(df_master, faskes_counts, on="kecamatan", how="left").fillna({"total_faskes": 0})
    df_master = pd.merge(df_master, beds_capacity, on="kecamatan", how="left").fillna({"total_tempat_tidur": 0})
    
    # Visits
    visits_sum = df_kunj_resolved.groupby("kecamatan")["total_kunjungan"].sum().rename("total_kunjungan")
    df_master = pd.merge(df_master, visits_sum, on="kecamatan", how="left").fillna({"total_kunjungan": 0})
    
    # Disease Cases
    disease_sum = df_peny_long.groupby("kecamatan")["jumlah_kasus"].sum().rename("total_kasus_penyakit")
    df_master = pd.merge(df_master, disease_sum, on="kecamatan", how="left").fillna({"total_kasus_penyakit": 0})
    
    # Save master
    df_master.to_csv(os.path.join(processed_dir, "master_heal_city.csv"), index=False)
    print("Master compilation complete.")
    
    # -------------------------------------------------------------------------
    # DYNAMIC SPATIAL COORDINATES UPDATE FROM EXCEL
    # -------------------------------------------------------------------------
    try:
        faskes_path = os.path.join(config["data"]["spatial_dir"], "fasilitas_kesehatan.geojson")
        pkm_path = os.path.join(config["data"]["spatial_dir"], "puskesmas.geojson")
        
        if os.path.exists(faskes_path) and os.path.exists(pkm_path):
            print("Applying coordinates from Excel puskemas sheet to GeoJSON files...")
            pkm_coords = {}
            for idx, row in df_raw_pkm.iterrows():
                name = str(row.get("Puskesmas", "")).strip()
                coord_str = str(row.get("Koordinat", "")).strip()
                if "," in coord_str:
                    try:
                        parts = coord_str.split(",")
                        lat = float(parts[0].strip())
                        lon = float(parts[1].strip())
                        pkm_coords[name.lower()] = [lon, lat]
                    except ValueError:
                        pass
            
            if pkm_coords:
                import re
                def clean_name(n):
                    n = n.lower().replace("puskesmas", "").replace("pustu", "").strip()
                    return re.sub(r'[^a-z0-9]', '', n)
                
                clean_pkm_coords = {clean_name(k): v for k, v in pkm_coords.items()}
                
                # Update files
                with open(faskes_path, "r", encoding="utf-8") as f:
                    gj_faskes = json.load(f)
                with open(pkm_path, "r", encoding="utf-8") as f:
                    gj_pkm = json.load(f)
                
                # Map capacities
                bed_capacity_dict = {}
                for idx, row in df_clean_bed.iterrows():
                    f_name = str(row.get("nama_faskes", "")).strip().lower()
                    cap = row.get("kapasitas_tempat_tidur")
                    if pd.notna(cap):
                        bed_capacity_dict[f_name] = int(cap)

                # Update faskes coordinates and capacity
                for feat in gj_faskes["features"]:
                    p = feat["properties"]
                    
                    # Update coordinates if Puskesmas Induk
                    if p.get("jenis_faskes") == "Puskesmas Induk":
                        name = p.get("nama_puskesmas", p.get("nama_faskes", ""))
                        c_name = clean_name(name)
                        for k, v in clean_pkm_coords.items():
                            if c_name in k or k in c_name:
                                feat["geometry"]["coordinates"] = v
                                break
                    
                    # Add capacity
                    f_name = p.get("nama_faskes", p.get("nama_puskesmas", ""))
                    p["kapasitas_tempat_tidur"] = None
                    if f_name:
                        f_name_clean = str(f_name).strip().lower()
                        if f_name_clean in bed_capacity_dict:
                            p["kapasitas_tempat_tidur"] = bed_capacity_dict[f_name_clean]
                        else:
                            for k, v in bed_capacity_dict.items():
                                if k in f_name_clean or f_name_clean in k:
                                    p["kapasitas_tempat_tidur"] = v
                                    break
                                
                # Update puskesmas coordinates and capacity
                for feat in gj_pkm["features"]:
                    p = feat["properties"]
                    
                    # Update coordinates
                    name = p.get("nama_puskesmas", p.get("nama_faskes", ""))
                    c_name = clean_name(name)
                    for k, v in clean_pkm_coords.items():
                        if c_name in k or k in c_name:
                            feat["geometry"]["coordinates"] = v
                            break
                    
                    # Add capacity
                    f_name = p.get("nama_faskes", p.get("nama_puskesmas", ""))
                    p["kapasitas_tempat_tidur"] = None
                    if f_name:
                        f_name_clean = str(f_name).strip().lower()
                        if f_name_clean in bed_capacity_dict:
                            p["kapasitas_tempat_tidur"] = bed_capacity_dict[f_name_clean]
                        else:
                            for k, v in bed_capacity_dict.items():
                                if k in f_name_clean or f_name_clean in k:
                                    p["kapasitas_tempat_tidur"] = v
                                    break
                            
                # Save
                with open(faskes_path, "w", encoding="utf-8") as f:
                    json.dump(gj_faskes, f, indent=2)
                with open(pkm_path, "w", encoding="utf-8") as f:
                    json.dump(gj_pkm, f, indent=2)
                print("Successfully updated GeoJSON coordinates from Excel sheet 'puskemas'.")
    except Exception as e:
        print(f"Warning: Failed to apply Excel coordinates to GeoJSON files: {e}")

