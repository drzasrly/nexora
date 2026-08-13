import streamlit as st
import pandas as pd
import geopandas as gpd

@st.cache_data
def load_gap_data(path):
    return pd.read_csv(path)

@st.cache_data
def load_root_cause(path):
    return pd.read_csv(path)

@st.cache_data
def load_spatial(path):
    # Geopandas read_file returns a GeoDataFrame
    return gpd.read_file(path)

@st.cache_data
def load_features(path):
    return pd.read_csv(path)
