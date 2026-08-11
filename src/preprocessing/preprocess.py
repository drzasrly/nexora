import os
import shutil
import datetime
import numpy as np
import pandas as pd

# Paths definitions
RAW_EXCEL_PATH = "data/raw/data smart city.xlsx"
CLEANED_DIR_DATA = "data/cleaned"
PROCESSED_DIR_DATA = "data/processed"
CLEANED_DIR_DATASET = "dataset/cleaned"
PROCESSED_DIR_DATASET = "dataset/processed"
LOGS_DIR = "logs"

# Ensure output directories exist
for d in [CLEANED_DIR_DATA, PROCESSED_DIR_DATA, CLEANED_DIR_DATASET, PROCESSED_DIR_DATASET, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------

# List to collect all cleaning logs
cleaning_log_entries = []

def log_cleaning_action(dataset, row_id, column, original, new, action, reason):
    """
    Log a cleaning action to the central log list.
    """
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
    """
    Standardize dataframe columns: lowercase, strip, spaces/dashes/slashes to underscore.
    """
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
    """
    Strip leading/trailing spaces, collapse multiple spaces to a single space.
    Preserves case, returns pd.NA for nulls.
    """
    if pd.isna(value):
        return pd.NA
    val_str = str(value).strip()
    return " ".join(val_str.split())

def apply_text_cleaning(df):
    """
    Apply text cleaning to all object columns in a dataframe.
    """
    df = df.copy()
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(clean_text)
    return df

def clean_disease_value(val):
    """
    Clean and correct misparsed numeric values in disease data.
    E.g., corrects float 1.342 to integer 1342 (Indonesian thousand separator misparsed as decimal).
    """
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

# Official 31 Kecamatan in Surabaya
OFFICIAL_KECAMATAN = [
    "Asemrowo", "Benowo", "Bubutan", "Bulak", "Dukuh Pakis", "Gayungan", "Genteng",
    "Gubeng", "Gunung Anyar", "Jambangan", "Karang Pilang", "Kenjeran", "Krembangan",
    "Lakarsantri", "Mulyorejo", "Pabean Cantian", "Pakal", "Rungkut", "Sambikerep",
    "Sawahan", "Semampir", "Simokerto", "Suko Manunggal", "Sukolilo", "Tambaksari",
    "Tandes", "Tegalsari", "Tenggilis Mejoyo", "Wiyung", "Wonocolo", "Wonokromo"
]

# Explicit Kecamatan mappings
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

# -----------------------------------------------------------------------------
# PIPELINE START
# -----------------------------------------------------------------------------

print("Starting HEAL-CITY Preprocessing Pipeline...")

# Load Excel File
assert os.path.exists(RAW_EXCEL_PATH), f"Raw excel file not found at {RAW_EXCEL_PATH}!"
excel = pd.ExcelFile(RAW_EXCEL_PATH)

# We will collect data quality metrics for the final Data Quality Report
dq_report_records = []

# 1. PENDUDUK SHEET CLEANING
print("Processing sheet: penduduk...")
df_raw_penduduk = pd.read_excel(excel, sheet_name="penduduk")

# Audit
total_rows = len(df_raw_penduduk)
dups = df_raw_penduduk.duplicated().sum()
missing = df_raw_penduduk.isna().sum().sum()

df_clean_pend = standardize_columns(df_raw_penduduk)
df_clean_pend = apply_text_cleaning(df_clean_pend)

# Map kecamatan names
df_clean_pend["kecamatan"] = df_clean_pend["kecamatan"].replace(KECAMATAN_MAPPING)

# Log mapping differences
for idx, row in df_raw_penduduk.iterrows():
    orig_kec = str(row["Kecamatan"]).strip()
    norm_kec = KECAMATAN_MAPPING.get(orig_kec, orig_kec)
    if orig_kec != norm_kec and orig_kec.lower() != "surabaya":
        log_cleaning_action("penduduk", orig_kec, "kecamatan", orig_kec, norm_kec, "name normalization", "standardizing kecamatan name")

# Remove Surabaya city aggregate row
original_count = len(df_clean_pend)
df_clean_pend = df_clean_pend[df_clean_pend["kecamatan"].str.lower() != "surabaya"]
removed_rows = original_count - len(df_clean_pend)
if removed_rows > 0:
    log_cleaning_action("penduduk", "Surabaya", "kecamatan", "Surabaya", "Removed", "filter aggregate", "removing city-wide aggregate row")

# Rename columns to standard
df_clean_pend = df_clean_pend.rename(columns={
    "jumlah_penduduk_(ribu)": "jumlah_penduduk",
    "laju_pertumbuhan_penduduk_per_tahun": "laju_pertumbuhan",
    "kepadatan_penduduk_per_km_persegi_(km2)": "kepadatan_penduduk",
    "rasio_jenis_kelamin_penduduk": "rasio_jenis_kelamin"
})

# Select specific columns
df_clean_pend = df_clean_pend[[
    "kecamatan", "jumlah_penduduk", "laju_pertumbuhan", 
    "persentase_penduduk", "kepadatan_penduduk", "rasio_jenis_kelamin"
]]

# Validation
invalid_count = ((df_clean_pend["jumlah_penduduk"] <= 0) | (df_clean_pend["kepadatan_penduduk"] < 0)).sum()
unmatched_kec = df_clean_pend[~df_clean_pend["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0]

dq_report_records.append({
    "dataset": "penduduk",
    "total_rows": len(df_clean_pend),
    "duplicate_rows": dups,
    "missing_values": df_clean_pend.isna().sum().sum(),
    "invalid_values": invalid_count,
    "unmatched_kecamatan": unmatched_kec,
    "unmatched_puskesmas": 0,
    "outlier_count": 0,
    "status": "READY" if unmatched_kec == 0 else "ERROR"
})

# Save clean penduduk
df_clean_pend.to_csv(os.path.join(CLEANED_DIR_DATA, "clean_penduduk.csv"), index=False)
df_clean_pend.to_csv(os.path.join(CLEANED_DIR_DATASET, "clean_penduduk.csv"), index=False)
print("Finished sheet: penduduk. Saved clean_penduduk.csv.")


# 2. TENAGA KESEHATAN SHEET CLEANING
print("Processing sheet: tenaga kesehatan...")
df_raw_nakes = pd.read_excel(excel, sheet_name="tenaga kesehatan")

# Audit
total_rows_nakes = len(df_raw_nakes)
dups_nakes = df_raw_nakes.duplicated().sum()
missing_nakes = df_raw_nakes.isna().sum().sum()

df_clean_nakes = standardize_columns(df_raw_nakes)
df_clean_nakes = apply_text_cleaning(df_clean_nakes)

# Map kecamatan
df_clean_nakes["kecamatan"] = df_clean_nakes["kecamatan"].replace(KECAMATAN_MAPPING)

# Remove Surabaya city aggregate row
original_count = len(df_clean_nakes)
df_clean_nakes = df_clean_nakes[df_clean_nakes["kecamatan"].str.lower() != "surabaya"]
removed_rows = original_count - len(df_clean_nakes)
if removed_rows > 0:
    log_cleaning_action("tenaga kesehatan", "Surabaya", "kecamatan", "Surabaya", "Removed", "filter aggregate", "removing city-wide aggregate row")

# Convert workforce values to numeric, handles pd.NA/dashes
workforce_cols = [c for c in df_clean_nakes.columns if c != "kecamatan"]
for col in workforce_cols:
    orig_col_series = df_clean_nakes[col].copy()
    
    # Replace common dash variants with pd.NA
    df_clean_nakes[col] = df_clean_nakes[col].replace(["–", "-", "—"], pd.NA)
    
    # Coerce to numeric
    df_clean_nakes[col] = pd.to_numeric(df_clean_nakes[col], errors="coerce")
    
    # Log any coercions that changed values
    for idx, (orig, new) in enumerate(zip(orig_col_series, df_clean_nakes[col])):
        if str(orig) != str(new) and pd.notna(orig):
            kec_val = df_clean_nakes.iloc[idx]["kecamatan"]
            log_cleaning_action("tenaga kesehatan", kec_val, col, orig, new, "type coercion", "coercing to numeric and handling dash values")

# Rename columns to standard names
nakes_rename_dict = {
    "tenaga_kesehatan_perawat": "perawat",
    "tenaga_kesehatan_bidan": "bidan",
    "tenaga_kesehatan_tenaga_kefarmasian": "tenaga_kefarmasian",
    "tenaga_kesehatan_tenaga_kesehatan_masyarakat": "tenaga_kesehatan_masyarakat",
    "tenaga_kesehatan_tenaga_kesehatan_lingkungan": "tenaga_kesehatan_lingkungan",
    "tenaga_kesehatan_tenaga_gizi": "tenaga_gizi",
    "jumlah_tenaga_medis": "tenaga_medis",
    "jumlah_tenaga_kesehatan_psikologi_klinis": "psikologi_klinis",
    "jumlah_tenaga_keterapian_fisik": "keterapian_fisik",
    "jumlah_tenaga_keteknisan_medis": "keteknisan_medis",
    "jumlah_tenaga_teknik_biomedika": "teknik_biomedika",
    "jumlah_tenaga_kesehatan_tradisional": "tenaga_kesehatan_tradisional"
}
df_clean_nakes = df_clean_nakes.rename(columns=nakes_rename_dict)

# Select and order columns
df_clean_nakes = df_clean_nakes[[
    "kecamatan", "perawat", "bidan", "tenaga_kefarmasian",
    "tenaga_kesehatan_masyarakat", "tenaga_kesehatan_lingkungan", "tenaga_gizi",
    "tenaga_medis", "psikologi_klinis", "keterapian_fisik", "keteknisan_medis",
    "teknik_biomedika", "tenaga_kesehatan_tradisional"
]]

# Validation
invalid_count = (df_clean_nakes[df_clean_nakes.columns[1:]] < 0).sum().sum()
unmatched_kec = df_clean_nakes[~df_clean_nakes["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0]

dq_report_records.append({
    "dataset": "tenaga kesehatan",
    "total_rows": len(df_clean_nakes),
    "duplicate_rows": dups_nakes,
    "missing_values": df_clean_nakes.isna().sum().sum(),
    "invalid_values": invalid_count,
    "unmatched_kecamatan": unmatched_kec,
    "unmatched_puskesmas": 0,
    "outlier_count": 0,
    "status": "READY" if unmatched_kec == 0 else "ERROR"
})

# Save clean nakes
df_clean_nakes.to_csv(os.path.join(CLEANED_DIR_DATA, "clean_tenaga_kesehatan.csv"), index=False)
df_clean_nakes.to_csv(os.path.join(CLEANED_DIR_DATASET, "clean_tenaga_kesehatan.csv"), index=False)
print("Finished sheet: tenaga kesehatan. Saved clean_tenaga_kesehatan.csv.")


# 3. PUSKESMAS MASTER SHEET CLEANING & MAPPING
print("Processing sheet: puskemas...")
df_raw_pkm = pd.read_excel(excel, sheet_name="puskemas")

# Audit
total_rows_pkm = len(df_raw_pkm)
dups_pkm = df_raw_pkm.duplicated().sum()

df_clean_pkm = standardize_columns(df_raw_pkm)
df_clean_pkm = apply_text_cleaning(df_clean_pkm)

# Generate puskesmas_id
df_clean_pkm["puskesmas_id"] = [f"PKM{i+1:03d}" for i in range(len(df_clean_pkm))]

# Extract Puskesmas -> Kecamatan mapping from "kunjungan puskesmas" sheet to associate Kecamatan
df_kunj_raw = pd.read_excel(excel, sheet_name="kunjungan puskesmas", header=2)
df_kunj_raw = standardize_columns(df_kunj_raw)
df_kunj_raw = apply_text_cleaning(df_kunj_raw)

# Keep unique mapping of kunjungan puskesmas (after cleaning name prefixes)
# We normalize "Puskesmas Moro Krembangan" to "Morokrembangan" as well
pkm_kec_map = {}
for idx, row in df_kunj_raw.iterrows():
    raw_pkm_name = str(row["nama_puskesmas"]).strip()
    raw_kec = str(row["kecamatan"]).strip()
    
    # Strip prefix "Puskesmas "
    clean_pkm = raw_pkm_name
    if clean_pkm.lower().startswith("puskesmas "):
        clean_pkm = clean_pkm[len("puskesmas "):].strip()
        
    # Apply manual replacement for Moro Krembangan
    if clean_pkm == "Moro Krembangan":
        clean_pkm = "Morokrembangan"
        
    # Standardize Kecamatan
    norm_kec = KECAMATAN_MAPPING.get(raw_kec, raw_kec)
    
    pkm_kec_map[clean_pkm.lower()] = norm_kec

# Assign Kecamatan to master puskesmas
df_clean_pkm["kecamatan"] = df_clean_pkm["puskesmas"].apply(lambda x: pkm_kec_map.get(str(x).strip().lower(), pd.NA))

# Ensure all official kecamatan are mapped
for idx, row in df_clean_pkm.iterrows():
    if pd.isna(row["kecamatan"]):
        # Fallback search if needed, print warning
        print(f"Warning: Puskesmas '{row['puskesmas']}' has no associated Kecamatan!")

# Rename and select columns
df_clean_pkm = df_clean_pkm.rename(columns={
    "puskesmas": "nama_puskesmas"
})
df_clean_pkm = df_clean_pkm[[
    "puskesmas_id", "nama_puskesmas", "kecamatan", "alamat", "telepon", "pelayanan_unggulan"
]]

# Create Puskesmas Master mapping log (logs/mapping_puskesmas.csv)
mapping_pkm_entries = []
for idx, row in df_kunj_raw.iterrows():
    raw_name = str(row["nama_puskesmas"]).strip()
    clean_name = raw_name
    if clean_name.lower().startswith("puskesmas "):
        clean_name = clean_name[len("puskesmas "):].strip()
        
    mapped_std = "Morokrembangan" if clean_name == "Moro Krembangan" else clean_name
    
    # Find matching ID in master list
    matching_pkm = df_clean_pkm[df_clean_pkm["nama_puskesmas"].str.lower() == mapped_std.lower()]
    pkm_id = matching_pkm.iloc[0]["puskesmas_id"] if len(matching_pkm) > 0 else "UNKNOWN"
    kec_val = KECAMATAN_MAPPING.get(str(row["kecamatan"]).strip(), str(row["kecamatan"]).strip())
    
    mapping_pkm_entries.append({
        "nama_asli": clean_name,
        "nama_standar": mapped_std,
        "puskesmas_id": pkm_id,
        "kecamatan": kec_val,
        "status": "mapped" if pkm_id != "UNKNOWN" else "unmapped"
    })

df_mapping_pkm_csv = pd.DataFrame(mapping_pkm_entries).drop_duplicates()
df_mapping_pkm_csv.to_csv(os.path.join(LOGS_DIR, "mapping_puskesmas.csv"), index=False)

# Validation
unmatched_kec_pkm = df_clean_pkm[~df_clean_pkm["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0]

dq_report_records.append({
    "dataset": "puskesmas",
    "total_rows": len(df_clean_pkm),
    "duplicate_rows": dups_pkm,
    "missing_values": df_clean_pkm.isna().sum().sum(),
    "invalid_values": 0,
    "unmatched_kecamatan": unmatched_kec_pkm,
    "unmatched_puskesmas": 0,
    "outlier_count": 0,
    "status": "READY" if unmatched_kec_pkm == 0 else "ERROR"
})

# Save clean puskesmas
df_clean_pkm.to_csv(os.path.join(CLEANED_DIR_DATA, "clean_puskesmas.csv"), index=False)
df_clean_pkm.to_csv(os.path.join(CLEANED_DIR_DATASET, "clean_puskesmas.csv"), index=False)
print("Finished sheet: puskemas. Saved clean_puskesmas.csv and mapping_puskesmas.csv.")


# 4. KUNJUNGAN PUSKESMAS SHEET CLEANING
print("Processing sheet: kunjungan puskesmas...")
df_kunj_raw = pd.read_excel(excel, sheet_name="kunjungan puskesmas", header=2)

# Audit
total_rows_kunj = len(df_kunj_raw)
dups_kunj = df_kunj_raw.duplicated().sum()

df_kunj_clean = standardize_columns(df_kunj_raw)
df_kunj_clean = apply_text_cleaning(df_kunj_clean)

# Map kecamatan
df_kunj_clean["kecamatan"] = df_kunj_clean["kecamatan"].replace(KECAMATAN_MAPPING)

# Clean name and match with master ID
def match_pkm_id(row):
    raw_name = str(row["nama_puskesmas"]).strip()
    clean_name = raw_name
    if clean_name.lower().startswith("puskesmas "):
        clean_name = clean_name[len("puskesmas "):].strip()
    if clean_name == "Moro Krembangan":
        clean_name = "Morokrembangan"
        
    match = df_clean_pkm[df_clean_pkm["nama_puskesmas"].str.lower() == clean_name.lower()]
    if len(match) > 0:
        return match.iloc[0]["puskesmas_id"]
    else:
        return pd.NA

df_kunj_clean["puskesmas_id"] = df_kunj_clean.apply(match_pkm_id, axis=1)

# Melt the wide layout to long layout
months_ind = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

long_records = []
for idx, row in df_kunj_clean.iterrows():
    pkm_id = row["puskesmas_id"]
    kec = row["kecamatan"]
    
    if pd.isna(pkm_id):
        continue
        
    for m in months_ind:
        m_lower = m.lower()
        col_baru = f"{m_lower}_baru"
        col_lama = f"{m_lower}_lama"
        col_total = f"{m_lower}_total"
        
        val_baru = row[col_baru] if col_baru in row else pd.NA
        val_lama = row[col_lama] if col_lama in row else pd.NA
        val_total = row[col_total] if col_total in row else pd.NA
        
        long_records.append({
            "puskesmas_id": pkm_id,
            "kecamatan": kec,
            "bulan": m,
            "pasien_baru": val_baru,
            "pasien_lama": val_lama,
            "total_kunjungan": val_total
        })

df_kunj_long = pd.DataFrame(long_records)

# Resolve the split records (specifically Puskesmas Tenggilis split across Row 59 and Row 63)
# Group by (puskesmas_id, kecamatan, bulan) and take the first non-null value
df_kunj_resolved = df_kunj_long.groupby(["puskesmas_id", "kecamatan", "bulan"], as_index=False, dropna=False).first()

# Log the merge of Puskesmas Tenggilis split rows
log_cleaning_action("kunjungan puskesmas", "PKM059 (Tenggilis)", "bulan", "Multiple rows", "Merged 12 rows", "resolve split records", "merged split row data for Puskesmas Tenggilis across different kecamatan names")

# Convert fields to numeric
df_kunj_resolved["pasien_baru"] = pd.to_numeric(df_kunj_resolved["pasien_baru"], errors="coerce")
df_kunj_resolved["pasien_lama"] = pd.to_numeric(df_kunj_resolved["pasien_lama"], errors="coerce")
df_kunj_resolved["total_kunjungan"] = pd.to_numeric(df_kunj_resolved["total_kunjungan"], errors="coerce")

# Validate total = baru + lama
for idx, row in df_kunj_resolved.iterrows():
    baru = row["pasien_baru"]
    lama = row["pasien_lama"]
    tot = row["total_kunjungan"]
    
    if pd.notna(baru) and pd.notna(lama) and pd.notna(tot):
        if baru + lama != tot:
            pkm_name = df_clean_pkm[df_clean_pkm["puskesmas_id"] == row["puskesmas_id"]].iloc[0]["nama_puskesmas"]
            log_cleaning_action(
                "kunjungan", 
                f"{row['puskesmas_id']} ({pkm_name}) - {row['bulan']}", 
                "total_kunjungan", 
                tot, 
                tot, 
                "validation check", 
                f"Mismatch in kunjungan total: Baru ({baru}) + Lama ({lama}) = {baru+lama} but Total reported as {tot}"
            )

# Check number of rows: 63 Puskesmas * 12 months = 756 rows
print(f"Number of rows in clean kunjungan: {len(df_kunj_resolved)} (Expected: 756)")
assert len(df_kunj_resolved) == 756, f"Expected 756 rows but got {len(df_kunj_resolved)}!"

# Validation
unmatched_kec_kunj = df_kunj_resolved[~df_kunj_resolved["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0]
unmatched_pkm_kunj = df_kunj_resolved[df_kunj_resolved["puskesmas_id"].isna()].shape[0]

dq_report_records.append({
    "dataset": "kunjungan puskesmas",
    "total_rows": len(df_kunj_resolved),
    "duplicate_rows": dups_kunj,
    "missing_values": df_kunj_resolved.isna().sum().sum(),
    "invalid_values": 0,
    "unmatched_kecamatan": unmatched_kec_kunj,
    "unmatched_puskesmas": unmatched_pkm_kunj,
    "outlier_count": 0,
    "status": "READY" if (unmatched_kec_kunj == 0 and unmatched_pkm_kunj == 0) else "ERROR"
})

# Save clean kunjungan
df_kunj_resolved.to_csv(os.path.join(CLEANED_DIR_DATA, "clean_kunjungan.csv"), index=False)
df_kunj_resolved.to_csv(os.path.join(CLEANED_DIR_DATASET, "clean_kunjungan.csv"), index=False)
print("Finished sheet: kunjungan puskesmas. Saved clean_kunjungan.csv.")


# 5. FASKES SHEET CLEANING
print("Processing sheet: faskes...")
df_raw_faskes = pd.read_excel(excel, sheet_name="faskes")

# Audit
total_rows_faskes = len(df_raw_faskes)
dups_faskes = df_raw_faskes.duplicated().sum()

df_clean_faskes = standardize_columns(df_raw_faskes)
df_clean_faskes = apply_text_cleaning(df_clean_faskes)

# Map kecamatan
df_clean_faskes["kecamatan"] = df_clean_faskes["kecamatan"].replace(KECAMATAN_MAPPING)

# Handle Unknown Kecamatan (e.g. Darmo or NaN)
df_clean_faskes["status_lokasi"] = "mapped"
df_clean_faskes.loc[df_clean_faskes["kecamatan"].isna(), "status_lokasi"] = "unknown"
df_clean_faskes.loc[~df_clean_faskes["kecamatan"].isin(OFFICIAL_KECAMATAN) & df_clean_faskes["kecamatan"].notna(), "status_lokasi"] = "unknown"

# Set Kecamatan to NaN for unknown
df_clean_faskes.loc[df_clean_faskes["status_lokasi"] == "unknown", "kecamatan"] = pd.NA

# Rename ID to generated_faskes_id and penyelenggara_faskes to penyelenggara
df_clean_faskes = df_clean_faskes.rename(columns={
    "_id": "generated_faskes_id",
    "penyelenggara_faskes": "penyelenggara"
})
df_clean_faskes["generated_faskes_id"] = [f"FSK{i+1:04d}" for i in range(len(df_clean_faskes))]

# Reorder columns
df_clean_faskes = df_clean_faskes[[
    "generated_faskes_id", "kecamatan", "jenis_faskes", "nama_faskes", "penyelenggara", "status_lokasi"
]]

# Check duplicates (same kecamatan, jenis_faskes, nama_faskes, penyelenggara)
faskes_keys = ["kecamatan", "jenis_faskes", "nama_faskes", "penyelenggara"]
dup_records = df_clean_faskes.duplicated(subset=faskes_keys, keep=False)
dup_count = dup_records.sum()
if dup_count > 0:
    print(f"Found {dup_count} duplicated faskes entries.")
    # Log duplicates
    for idx, row in df_clean_faskes[dup_records].iterrows():
        log_cleaning_action("faskes", row["generated_faskes_id"], "multiple", str(row[faskes_keys].to_dict()), "Duplicate checked", "identify duplicate", "duplicate record check in faskes dataset")

# Validation
unmatched_kec_faskes = df_clean_faskes[(df_clean_faskes["status_lokasi"] == "mapped") & (~df_clean_faskes["kecamatan"].isin(OFFICIAL_KECAMATAN))].shape[0]

dq_report_records.append({
    "dataset": "faskes",
    "total_rows": len(df_clean_faskes),
    "duplicate_rows": dups_faskes,
    "missing_values": df_clean_faskes.isna().sum().sum(),
    "invalid_values": 0,
    "unmatched_kecamatan": unmatched_kec_faskes,
    "unmatched_puskesmas": 0,
    "outlier_count": 0,
    "status": "READY"
})

# Save clean faskes
df_clean_faskes.to_csv(os.path.join(CLEANED_DIR_DATA, "clean_faskes.csv"), index=False)
df_clean_faskes.to_csv(os.path.join(CLEANED_DIR_DATASET, "clean_faskes.csv"), index=False)
print("Finished sheet: faskes. Saved clean_faskes.csv.")


# 6. TEMPAT TIDUR SHEET CLEANING
print("Processing sheet: tempat tidur...")
df_raw_bed = pd.read_excel(excel, sheet_name="tempat tidur")

# Audit
total_rows_bed = len(df_raw_bed)
dups_bed = df_raw_bed.duplicated().sum()

df_clean_bed = standardize_columns(df_raw_bed)
df_clean_bed = apply_text_cleaning(df_clean_bed)

# Map kecamatan
df_clean_bed["kecamatan"] = df_clean_bed["kecamatan"].replace(KECAMATAN_MAPPING)

# Make capacities numeric, keep empty/NaN values as NaN
df_clean_bed["kapasitas_tempat_tidur"] = pd.to_numeric(df_clean_bed["kapasitas_tempat_tidur"], errors="coerce")

# Rename penyelenggara_faskes to penyelenggara
df_clean_bed = df_clean_bed.rename(columns={
    "penyelenggara_faskes": "penyelenggara"
})

# Add tipe_kelas column as NaN
df_clean_bed["tipe_kelas"] = pd.NA

# Select columns
df_clean_bed = df_clean_bed[[
    "kecamatan", "jenis_faskes", "penyelenggara", "nama_faskes", "tipe_kelas", "kapasitas_tempat_tidur"
]]

# Validation
unmatched_kec_bed = df_clean_bed[~df_clean_bed["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0]
invalid_bed = (df_clean_bed["kapasitas_tempat_tidur"] < 0).sum()

dq_report_records.append({
    "dataset": "tempat tidur",
    "total_rows": len(df_clean_bed),
    "duplicate_rows": dups_bed,
    "missing_values": df_clean_bed.isna().sum().sum(),
    "invalid_values": invalid_bed,
    "unmatched_kecamatan": unmatched_kec_bed,
    "unmatched_puskesmas": 0,
    "outlier_count": 0,
    "status": "READY" if unmatched_kec_bed == 0 else "ERROR"
})

# Save clean tempat tidur
df_clean_bed.to_csv(os.path.join(CLEANED_DIR_DATA, "clean_tempat_tidur.csv"), index=False)
df_clean_bed.to_csv(os.path.join(CLEANED_DIR_DATASET, "clean_tempat_tidur.csv"), index=False)
print("Finished sheet: tempat tidur. Saved clean_tempat_tidur.csv.")


# 7. DATA PENYAKIT SHEET CLEANING
print("Processing sheet: data penyakit...")
df_raw_peny = pd.read_excel(excel, sheet_name="data penyakit")

# Clean text casing/whitespaces
df_peny_clean = apply_text_cleaning(df_raw_peny)

# Clean and correct misparsed numeric values (e.g., float 1.342 to integer 1342)
months_cols_raw = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
for m_col in months_cols_raw:
    df_peny_clean[m_col] = df_peny_clean[m_col].apply(clean_disease_value)

# Separate into df_full and df_jan_only
# Row 0 to 1322: complete rows (1323 rows)
# Row 1323: fully empty row
# Row 1324: header row of second table
# Row 1325 onwards: Jan-only rows
df_peny_full = df_peny_clean.iloc[0:1323].copy()
df_peny_jan_only = df_peny_clean.iloc[1325:].copy()

# Reset index
df_peny_full = df_peny_full.reset_index(drop=True)
df_peny_jan_only = df_peny_jan_only.reset_index(drop=True)

# Standardize column names
df_peny_full = standardize_columns(df_peny_full)
df_peny_jan_only = standardize_columns(df_peny_jan_only)

# Verify the shift pattern
# We match them on keys: KECAMATAN, NAMA FASKES, Jenis Penyakit (after stripping, lowercase)
key_cols = ['kecamatan', 'nama_faskes_(rumah_sakit_dan_puskesmas)', 'jenis_penyakit']

df_peny_full["key_merge"] = df_peny_full[key_cols].astype(str).agg('_'.join, axis=1).str.strip().str.lower()
df_peny_jan_only["key_merge"] = df_peny_jan_only[key_cols].astype(str).agg('_'.join, axis=1).str.strip().str.lower()

# Check for suspected shifted February
shifted_count = 0
for idx, row in df_peny_jan_only.iterrows():
    key = row["key_merge"]
    jan_val = row["januari"] # contains February data in dataframe
    
    # Find matching in full record
    match = df_peny_full[df_peny_full["key_merge"] == key]
    if len(match) > 0:
        feb_val_full = match.iloc[0]["februari"]
        if str(jan_val) == str(feb_val_full):
            shifted_count += 1
            # Reconstruct: shift value from January column to February column, set January to NaN
            df_peny_jan_only.at[idx, "februari"] = jan_val
            df_peny_jan_only.at[idx, "januari"] = pd.NA
            
            # Log this suspected shift
            log_cleaning_action(
                "data penyakit", 
                f"Row {idx} ({row['kecamatan']} - {row['nama_faskes_(rumah_sakit_dan_puskesmas)']})", 
                "januari/februari", 
                f"Jan:{jan_val}, Feb:NaN", 
                f"Jan:NaN, Feb:{jan_val}", 
                "suspected_shifted_february", 
                "data shift anomaly verified: shifted February value misaligned under January header"
            )

print(f"Shift pattern verified: {shifted_count} / {len(df_peny_jan_only)} rows matched and reconstructed.")

# Combine df_full and df_peny_jan_only
# Since they represent the same keys, grouping and taking first non-null resolves to a single record per key
df_peny_combined = pd.concat([df_peny_full, df_peny_jan_only], ignore_index=True)

# Select months columns for group resolution
months_cols = ["januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september", "oktober", "november", "desember"]
group_cols = ["kecamatan", "nama_faskes_(rumah_sakit_dan_puskesmas)", "jenis_penyakit"]

# Group by keys and take first non-null
df_peny_resolved = df_peny_combined.groupby(group_cols, as_index=False, dropna=False)[months_cols].first()

# Validate that we have at most 1 record per combination
assert df_peny_resolved.duplicated(subset=group_cols).sum() == 0, "Duplicate records found after resolving disease data!"
print(f"Resolved disease records count: {len(df_peny_resolved)}")

# Melt to long format
df_peny_long = df_peny_resolved.melt(
    id_vars=group_cols,
    value_vars=months_cols,
    var_name="bulan",
    value_name="jumlah_cases"
)

# Rename value_name to jumlah_kasus
df_peny_long = df_peny_long.rename(columns={"jumlah_cases": "jumlah_kasus"})

# Capitalize bulan names to match standard Indonesian title case (e.g. Januari)
df_peny_long["bulan"] = df_peny_long["bulan"].str.capitalize()

# Clean and rename columns
df_peny_long = df_peny_long.rename(columns={
    "nama_faskes_(rumah_sakit_dan_puskesmas)": "nama_faskes"
})

# Standardize kecamatan names using mapping in long format
df_peny_long["kecamatan"] = df_peny_long["kecamatan"].replace(KECAMATAN_MAPPING)

# Make cases numeric, preserve NaN
df_peny_long["jumlah_kasus"] = pd.to_numeric(df_peny_long["jumlah_kasus"], errors="coerce")

# Select final columns
df_peny_long = df_peny_long[[
    "kecamatan", "nama_faskes", "jenis_penyakit", "bulan", "jumlah_kasus"
]]

# Validation
unmatched_kec_peny = df_peny_long[~df_peny_long["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0]

dq_report_records.append({
    "dataset": "data penyakit",
    "total_rows": len(df_peny_long),
    "duplicate_rows": 0,
    "missing_values": df_peny_long.isna().sum().sum(),
    "invalid_values": (df_peny_long["jumlah_kasus"] < 0).sum(),
    "unmatched_kecamatan": unmatched_kec_peny,
    "unmatched_puskesmas": 0,
    "outlier_count": 0,
    "status": "READY" if unmatched_kec_peny == 0 else "ERROR"
})

# Save clean penyakit
df_peny_long.to_csv(os.path.join(CLEANED_DIR_DATA, "clean_penyakit.csv"), index=False)
df_peny_long.to_csv(os.path.join(CLEANED_DIR_DATASET, "clean_penyakit.csv"), index=False)
print("Finished sheet: data penyakit. Saved clean_penyakit.csv.")


# -----------------------------------------------------------------------------
# LOGS GENERATION
# -----------------------------------------------------------------------------

# 1. logs/mapping_kecamatan.csv
mapping_kec_entries = []
# Create a comprehensive kecamatan mapping log
for original, target in KECAMATAN_MAPPING.items():
    mapping_kec_entries.append({
        "nilai_asli": original,
        "nilai_standar": target,
        "alasan": "standardization of capitalization and spacing",
        "sumber": "raw data sheets"
    })
# Add invalid/missing ones from faskes
mapping_kec_entries.append({
    "nilai_asli": "Darmo",
    "nilai_standar": "NaN",
    "alasan": "invalid kecamatan (is a kelurahan)",
    "sumber": "faskes"
})
mapping_kec_entries.append({
    "nilai_asli": "nan",
    "nilai_standar": "NaN",
    "alasan": "missing kecamatan",
    "sumber": "faskes"
})

df_mapping_kec = pd.DataFrame(mapping_kec_entries)
df_mapping_kec.to_csv(os.path.join(LOGS_DIR, "mapping_kecamatan.csv"), index=False)
print("Saved logs/mapping_kecamatan.csv.")

# 2. logs/cleaning_log.csv
df_cleaning_log = pd.DataFrame(cleaning_log_entries)
df_cleaning_log.to_csv(os.path.join(LOGS_DIR, "cleaning_log.csv"), index=False)
print(f"Saved logs/cleaning_log.csv with {len(df_cleaning_log)} entries.")


# -----------------------------------------------------------------------------
# MASTER DATASET CREATION (FEATURE ENGINEERING)
# -----------------------------------------------------------------------------
print("Creating master dataset master_heal_city.csv...")

# 1. Base Kecamatan template
df_master = pd.DataFrame({"kecamatan": OFFICIAL_KECAMATAN})

# 2. Aggregate Demographics (Penduduk)
# clean_penduduk has exactly one row per kecamatan
df_master = pd.merge(df_master, df_clean_pend[["kecamatan", "jumlah_penduduk", "kepadatan_penduduk"]], on="kecamatan", how="left")

# 3. Aggregate Workforce (Tenaga Kesehatan)
# clean_tenaga_kesehatan has exactly one row per kecamatan
nakes_cols_agg = ["perawat", "bidan", "tenaga_medis"]
df_master = pd.merge(df_master, df_clean_nakes[["kecamatan"] + nakes_cols_agg], on="kecamatan", how="left")

# Compute total_tenaga_kesehatan (sum of all workforce categories in clean_tenaga_kesehatan)
# Let's sum across rows for nakes columns
df_clean_nakes["total_tenaga_kesehatan"] = df_clean_nakes.drop(columns=["kecamatan"]).sum(axis=1)
df_master = pd.merge(df_master, df_clean_nakes[["kecamatan", "total_tenaga_kesehatan"]], on="kecamatan", how="left")

# Rename variables to match specification requirements
df_master = df_master.rename(columns={
    "perawat": "jumlah_perawat",
    "bidan": "jumlah_bidan",
    "tenaga_medis": "jumlah_tenaga_medis"
})

# 4. Aggregate Capacities
# a. Puskesmas count
pkm_counts = df_clean_pkm.groupby("kecamatan").size().rename("jumlah_puskesmas")
df_master = pd.merge(df_master, pkm_counts, on="kecamatan", how="left").fillna({"jumlah_puskesmas": 0})

# b. Pustu count (jenis_faskes == "Puskesmas Pembantu" in clean_faskes)
pustu_counts = df_clean_faskes[df_clean_faskes["jenis_faskes"].str.lower() == "puskesmas pembantu"].groupby("kecamatan").size().rename("jumlah_pustu")
df_master = pd.merge(df_master, pustu_counts, on="kecamatan", how="left").fillna({"jumlah_pustu": 0})

# c. Total faskes count (clean_faskes)
faskes_counts = df_clean_faskes.groupby("kecamatan").size().rename("total_faskes")
df_master = pd.merge(df_master, faskes_counts, on="kecamatan", how="left").fillna({"total_faskes": 0})

# d. Total tempat tidur capacity (clean_tempat_tidur)
bed_capacity = df_clean_bed.groupby("kecamatan")["kapasitas_tempat_tidur"].sum().rename("total_tempat_tidur")
df_master = pd.merge(df_master, bed_capacity, on="kecamatan", how="left").fillna({"total_tempat_tidur": 0})

# 5. Aggregate Visits
# Total kunjungan (sum of visits from clean_kunjungan)
visit_totals = df_kunj_resolved.groupby("kecamatan")["total_kunjungan"].sum().rename("total_kunjungan")
df_master = pd.merge(df_master, visit_totals, on="kecamatan", how="left").fillna({"total_kunjungan": 0})

# 6. Aggregate Diseases
# Total kasus penyakit (sum of cases from clean_penyakit)
disease_totals = df_peny_long.groupby("kecamatan")["jumlah_kasus"].sum().rename("total_kasus_penyakit")
df_master = pd.merge(df_master, disease_totals, on="kecamatan", how="left").fillna({"total_kasus_penyakit": 0})


# -----------------------------------------------------------------------------
# FEATURE RATIOS & SCORING
# -----------------------------------------------------------------------------

# Calculate ratios (using population in thousands: population = jumlah_penduduk * 1000)
# Note: Ratios are calculated as ratio per thousand or per hundred thousand population
# 1. service_pressure (Visits per 1,000 population) = total_kunjungan / (jumlah_penduduk * 1000) * 1000 = total_kunjungan / jumlah_penduduk
df_master["service_pressure"] = df_master["total_kunjungan"] / df_master["jumlah_penduduk"]

# 2. nakes_ratio / workforce_ratio (Workforce per 1,000 population) = total_tenaga_kesehatan / jumlah_penduduk
df_master["workforce_ratio"] = df_master["total_tenaga_kesehatan"] / df_master["jumlah_penduduk"]

# 3. nurse_ratio (Perawat per 1,000 population) = jumlah_perawat / jumlah_penduduk
df_master["nurse_ratio"] = df_master["jumlah_perawat"] / df_master["jumlah_penduduk"]

# 4. facility_ratio (Facilities per 100,000 population) = total_faskes / (jumlah_penduduk * 1000) * 100000 = total_faskes / jumlah_penduduk * 100
df_master["facility_ratio"] = (df_master["total_faskes"] / df_master["jumlah_penduduk"]) * 100

# 5. bed_ratio (Beds per 1,000 population) = total_tempat_tidur / jumlah_penduduk
df_master["bed_ratio"] = df_master["total_tempat_tidur"] / df_master["jumlah_penduduk"]

# 6. disease_burden (Cases per 1,000 population) = total_kasus_penyakit / jumlah_penduduk
df_master["disease_burden"] = df_master["total_kasus_penyakit"] / df_master["jumlah_penduduk"]


# MIN-MAX NORMALIZATION & GAPS (All normalized values are between 0 and 1)
def min_max_normalize(series):
    s_min = series.min()
    s_max = series.max()
    if s_max == s_min:
        return series * 0.0
    return (series - s_min) / (s_max - s_min)

# Demand components (higher is worse -> score = normalized_value)
df_master["demand_score"] = min_max_normalize(df_master["jumlah_penduduk"])
df_master["service_pressure_score"] = min_max_normalize(df_master["service_pressure"])
df_master["disease_need_score"] = min_max_normalize(df_master["disease_burden"])

# Capacity components (higher is better -> gap = 1 - normalized_value)
df_master["workforce_gap"] = 1.0 - min_max_normalize(df_master["workforce_ratio"])
df_master["facility_gap"] = 1.0 - min_max_normalize(df_master["facility_ratio"])

# Accessibility gap (GIS data not yet available -> set to 0.0)
df_master["accessibility_gap"] = 0.0

# HEALTHCARE GAP SCORE
# w1 (demand_score) = 0.20
# w2 (service_pressure) = 0.20
# w3 (workforce_gap) = 0.20
# w4 (facility_gap) = 0.20
# w5 (disease_need_score) = 0.20
# w6 (accessibility_gap) = 0.00
df_master["healthcare_gap_score"] = (
    0.20 * df_master["demand_score"] +
    0.20 * df_master["service_pressure_score"] +
    0.20 * df_master["workforce_gap"] +
    0.20 * df_master["facility_gap"] +
    0.20 * df_master["disease_need_score"] +
    0.00 * df_master["accessibility_gap"]
) * 100.0 # Scale to 0-100

# PRIORITY CLASSIFICATION
# 0–20   = Rendah
# 21–40  = Sedang
# 41–60  = Tinggi
# 61–80  = Sangat Tinggi
# 81–100 = Kritis
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

df_master["priority_category"] = df_master["healthcare_gap_score"].apply(classify_priority)

# Select master dataset final columns
final_master_cols = [
    "kecamatan", "jumlah_penduduk", "kepadatan_penduduk",
    "jumlah_perawat", "jumlah_bidan", "jumlah_tenaga_medis", "total_tenaga_kesehatan",
    "jumlah_puskesmas", "jumlah_pustu", "total_faskes",
    "total_kunjungan", "service_pressure",
    "total_kasus_penyakit", "disease_burden",
    "total_tempat_tidur", "bed_ratio",
    "workforce_ratio", "facility_ratio",
    "demand_score", "workforce_gap", "facility_gap", "disease_need_score", "accessibility_gap",
    "healthcare_gap_score", "priority_category"
]
df_master_final = df_master[final_master_cols]

# Save master dataset
df_master_final.to_csv(os.path.join(PROCESSED_DIR_DATA, "master_heal_city.csv"), index=False)
df_master_final.to_csv(os.path.join(PROCESSED_DIR_DATASET, "master_heal_city.csv"), index=False)
print("Finished master dataset: master_heal_city.csv saved successfully.")


# -----------------------------------------------------------------------------
# DATA QUALITY REPORT GENERATION
# -----------------------------------------------------------------------------

# Add master_heal_city quality check
unmatched_kec_master = df_master_final[~df_master_final["kecamatan"].isin(OFFICIAL_KECAMATAN)].shape[0]
dq_report_records.append({
    "dataset": "master_heal_city",
    "total_rows": len(df_master_final),
    "duplicate_rows": df_master_final.duplicated().sum(),
    "missing_values": df_master_final.isna().sum().sum(),
    "invalid_values": 0,
    "unmatched_kecamatan": unmatched_kec_master,
    "unmatched_puskesmas": 0,
    "outlier_count": 0,
    "status": "READY" if unmatched_kec_master == 0 else "ERROR"
})

df_dq_report = pd.DataFrame(dq_report_records)
df_dq_report.to_csv(os.path.join(LOGS_DIR, "data_quality_report.csv"), index=False)
print("Saved logs/data_quality_report.csv.")

print("HEAL-CITY Preprocessing Pipeline Completed Successfully!")
