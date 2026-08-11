import os
import yaml
import pandas as pd
import geopandas as gpd

def load_config(config_path="config/config.yaml"):
    """Load configuration dictionary from YAML file."""
    assert os.path.exists(config_path), f"Configuration file not found at {config_path}!"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config

def load_csv(path):
    """Load a CSV file into a pandas DataFrame."""
    assert os.path.exists(path), f"CSV file not found at {path}!"
    return pd.read_csv(path)

def load_excel(path, sheet_name=None):
    """Load an Excel workbook or a specific sheet into a pandas DataFrame."""
    assert os.path.exists(path), f"Excel workbook not found at {path}!"
    return pd.read_excel(path, sheet_name=sheet_name)

def load_geojson(path):
    """Load a GeoJSON spatial boundary file into a GeoDataFrame."""
    assert os.path.exists(path), f"GeoJSON file not found at {path}!"
    return gpd.read_file(path)
