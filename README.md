# HEAL-CITY — Data Analytics & Spatial Pipeline

HEAL-CITY is a modular smart city decision support tool designed to analyze demographic demand, healthcare workforce deficits, facility constraints, and disease caseloads to identify priority gaps across the 31 Kecamatan of Surabaya.

## 1. Project Architecture

The system is structured as follows:
- **`config/config.yaml`**: Configurable paths, thresholds, and weighting parameters.
- **`src/`**: Central package files:
  - `data_loader.py`: Helpers to load Excel sheets, CSV, and spatial data.
  - `preprocessing.py`: Handles raw data cleaning, text normalization, and master table compilation.
  - `validation.py`: Runs baseline schema and type validations.
  - `feature_engineering.py`: Formulates ratios, scales indicators, and dominant diseases.
  - `gap_engine.py`: Scores composite gaps using configuration-defined weights.
  - `root_cause.py`: Analyzes margins, dominance, and generates Indonesian explanations.
  - `gis_analysis.py`: Joins spatial vectors and exports 5 interactive HTML maps.
- **`main.py`**: Central pipeline coordinator that logs runs to `logs/heal_city.log` and exports `outputs/reports/run_manifest.json`.
- **`tests/`**: Unit test suite verifying columns, numeric bounds, and logic limits.

## 2. Installation

1. Create and activate a python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 3. Running the Pipeline

To run the complete data processing, scoring, root cause analysis, and GIS mapping:
```bash
python main.py
```

## 4. Running the Test Suite

Validate features and formulas:
```bash
pytest tests/
```
