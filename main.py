import os
import json
import logging
import datetime
import pandas as pd
from src.data_loader import load_config, load_csv
from src.preprocessing import run_preprocessing
from src.validation import validate_required_columns, validate_kecamatan, validate_numeric, validate_infinity
from src.feature_engineering import build_features
from src.gap_engine import calculate_healthcare_gap, create_priority_ranking
from src.root_cause import run_root_cause_analysis
from src.gis_analysis import run_gis_analysis

# Configure Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/heal_city.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filemode="w"
)

def main():
    print("=" * 60)
    print("RUNNING HEAL-CITY MODULAR DATA PIPELINE")
    print("=" * 60)
    logging.info("HEAL-CITY Pipeline Execution Started.")
    
    start_time = datetime.datetime.now()
    status = "SUCCESS"
    error_msg = ""
    
    try:
        # 1. Load config
        config = load_config("config/config.yaml")
        logging.info("Configuration loaded successfully.")
        
        # Ensure directories exist
        os.makedirs(config["data"]["cleaned_dir"], exist_ok=True)
        os.makedirs(config["data"]["processed_dir"], exist_ok=True)
        os.makedirs(config["output"]["reports"], exist_ok=True)
        
        # 2. Run Preprocessing
        run_preprocessing(config)
        logging.info("Pre-processing complete. Intermediate datasets generated.")
        
        # 3. Load Master and Validate
        master_path = os.path.join(config["data"]["processed_dir"], "master_heal_city.csv")
        df_master = load_csv(master_path)
        
        # Validation checks
        validate_kecamatan(df_master)
        validate_numeric(df_master, ["jumlah_penduduk", "jumlah_perawat", "jumlah_bidan", "total_tempat_tidur"])
        validate_infinity(df_master)
        logging.info("Baseline master validations passed.")
        
        # 4. Load clean disease for features
        peny_path = os.path.join(config["data"]["cleaned_dir"], "clean_penyakit.csv")
        df_peny = load_csv(peny_path)
        
        # 5. Run Feature Engineering
        df_feats = build_features(df_master, df_peny, config)
        logging.info("Feature engineering complete.")
        
        # 6. Run Gap Engine
        df_gap_raw = calculate_healthcare_gap(df_feats, config)
        df_gap = create_priority_ranking(df_gap_raw, config)
        logging.info("Healthcare gap calculations and rankings complete.")
        
        # 7. Run Root Cause Analysis (RCA)
        df_rca = run_root_cause_analysis(df_gap, df_feats, config)
        logging.info("Root Cause Analysis (RCA) complete.")
        
        # 8. Run GIS analysis mapping
        run_gis_analysis(df_rca, config)
        logging.info("GIS mapping overlays completed successfully.")
        
    except Exception as e:
        status = "FAIL"
        error_msg = str(e)
        logging.exception("HEAL-CITY pipeline execution failed!")
        print(f"\n[PIPELINE FAILURE]: {e}")
        
    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # 9. Output Manifest
    manifest = {
        "project": "HEAL-CITY",
        "city": "Surabaya",
        "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": duration,
        "status": status,
        "error_message": error_msg,
        "dataset_rows": 31,
        "random_state": 42,
        "weights_configured": {
            "demand": 0.30,
            "workforce": 0.30,
            "facility": 0.20,
            "disease": 0.20
        }
    }
    
    manifest_path = "outputs/reports/run_manifest.json"
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    logging.info(f"Pipeline finished with status: {status} in {duration:.2f} seconds.")
    print("=" * 60)
    print(f"HEAL-CITY PIPELINE COMPLETED WITH STATUS: {status}")
    print(f"Execution Manifest saved to {manifest_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
