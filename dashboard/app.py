import streamlit as st
import sys
import os

# Resolve project root path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import yaml
from dashboard.components.data import load_gap_data, load_root_cause, load_features, load_spatial

# Set page config
st.set_page_config(
    page_title="HEAL-CITY — Surabaya Healthcare DSS",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load configuration
@st.cache_data
def load_config():
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)

config = load_config()

# Initialize session state variables
if "selected_district" not in st.session_state:
    st.session_state.selected_district = None
if "budget" not in st.session_state:
    st.session_state.budget = 5000000000

# Central Data Loader
st.sidebar.markdown("### 🛠️ Data Pipeline Loading")
try:
    gap_data = load_gap_data(config["data"]["gap"])
    rca_data = load_root_cause(config["data"]["root_cause"])
    features_data = load_features(config["data"]["features"])
    
    # Load spatial layers
    spatial_data = load_spatial(config["spatial"]["district"])
    pkm_spatial = load_spatial(config["spatial"]["puskesmas"])
    hosp_spatial = load_spatial(config["spatial"]["facilities"])
    # Filter only hospitals for pins mapping
    hosp_filtered = hosp_spatial[hosp_spatial["jenis_faskes"].str.contains("Rumah Sakit", na=False)]
    
    st.sidebar.success("✅ Datasets loaded successfully!")
except Exception as e:
    st.sidebar.error(f"❌ Error loading datasets: {e}")
    st.stop()

# App Header
st.title("🏥 HEAL-CITY Surabaya")
st.caption("Healthcare Equity & Access Intelligence for Smart City Decision Support")

# Sidebar navigation menu
st.sidebar.markdown("### 🧭 Navigation")
page = st.sidebar.radio(
    "Go to page:",
    [
        "City Overview",
        "Healthcare Gap Map",
        "Priority Ranking",
        "Root Cause Analysis",
        "Intervention Optimizer",
        "What-if Simulation",
        "AI Recommendation"
    ]
)

# Render specific page routing programmatically
if page == "City Overview":
    from dashboard.pages import overview
    overview.show_page(gap_data, rca_data, features_data)
    
elif page == "Healthcare Gap Map":
    from dashboard.pages import map as map_page
    map_page.show_page(spatial_data, gap_data, features_data, pkm_spatial, hosp_filtered)
    
elif page == "Priority Ranking":
    from dashboard.pages import priority
    priority.show_page(gap_data, rca_data, features_data)
    
elif page == "Root Cause Analysis":
    from dashboard.pages import root_cause
    root_cause.show_page(gap_data, rca_data, features_data)
    
elif page == "Intervention Optimizer":
    from dashboard.pages import optimizer
    optimizer.show_page(gap_data, rca_data, features_data, config)
    
elif page == "What-if Simulation":
    from dashboard.pages import simulation
    simulation.show_page(spatial_data, gap_data, features_data, config)
    
elif page == "AI Recommendation":
    from dashboard.pages import recommendation
    recommendation.show_page(gap_data, rca_data, features_data)

# Global footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #64748b; font-size: 0.85rem;'>"
    "HEAL-CITY Surabaya Smart City Decision Support System Prototype • Nexora Tech 2026"
    "</div>",
    unsafe_allow_html=True
)
