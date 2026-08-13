import streamlit as st
from streamlit_folium import st_folium
from src.simulation_engine import simulate_intervention
from dashboard.components.charts import create_before_after_chart
from dashboard.components.maps import create_gap_map

def show_page(gdf_spatial, df_gap, df_features, config):
    st.markdown("## 🧪 What-if Simulation")
    st.caption("Manually adjust resource levels to simulate potential gap reductions before making actual policy decisions.")
    st.markdown("---")
    
    kec_list = sorted(df_gap["kecamatan"].str.title().tolist())
    
    # Sync selected kecamatan
    default_idx = 0
    if st.session_state.selected_district:
        try:
            default_idx = kec_list.index(st.session_state.selected_district.title())
        except ValueError:
            default_idx = 0
            
    selected_kec = st.selectbox("Select Kecamatan to Simulate:", options=kec_list, index=default_idx)
    st.session_state.selected_district = selected_kec
    
    st.markdown("#### Adjust Resource Parameters")
    col_d, col_n, col_f, col_a = st.columns(4)
    with col_d:
        add_docs = st.slider("Add Doctors", 0, 30, 0, step=1)
    with col_n:
        add_nurses = st.slider("Add Nurses", 0, 50, 0, step=1)
    with col_f:
        add_beds = st.slider("Add Inpatient Beds", 0, 20, 0, step=1)
    with col_a:
        add_acc = st.slider("Improve Accessibility Index", 0.0, 0.5, 0.0, step=0.05)
        
    if st.button("🧪 RUN SIMULATION", use_container_width=True):
        # Build deltas
        deltas = {
            "nakes": add_docs + add_nurses,
            "perawat": add_nurses,
            "bidan": 0,
            "beds": add_beds,
            "faskes": max(1, int(add_beds / 5)) if add_beds > 0 else 0,
            "accessibility_offset": add_acc
        }
        
        # Run simulation
        res = simulate_intervention(df_features, selected_kec, deltas, config)
        st.session_state.simulation_result = res
        
    if "simulation_result" in st.session_state:
        res = st.session_state.simulation_result
        before = res["before_gap"]
        after = res["after_gap"]
        red_abs = res["improvement_absolute"]
        red_pct = res["improvement_percent"]
        df_sim = res["simulated_df"]
        
        # Section 57: Enforce validation assert after_gap <= before_gap
        if after > before:
            st.error("🚨 Simulation Error: Simulated gap score cannot exceed original gap score.")
            return
            
        st.markdown("---")
        st.markdown("### 📊 Simulation Dashboard")
        
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Baseline Gap Score", f"{before:.2f}")
        with col_m2:
            st.metric("Simulated Gap Score", f"{after:.2f}", delta=f"-{red_abs:.2f}")
        with col_m3:
            st.metric("Improvement (%)", f"{red_pct:.2f}%")
            
        col_c, col_m = st.columns([5, 7])
        with col_c:
            fig_ba = create_before_after_chart(before, after)
            st.plotly_chart(fig_ba, use_container_width=True)
            
        with col_m:
            st.markdown("#### 🗺️ Spatial Visual Comparison")
            map_view = st.radio("Choose map representation view:", ["Baseline", "Simulated"])
            
            # Merge with spatial coordinates
            if map_view == "Baseline":
                gdf_map = gdf_spatial.merge(df_gap[["kecamatan", "healthcare_gap_score", "priority_category"]], on="kecamatan", how="left")
                m_ba = create_gap_map(gdf_map, score_col="healthcare_gap_score", selected_district=selected_kec)
            else:
                gdf_map = gdf_spatial.merge(df_sim[["kecamatan", "healthcare_gap_score", "priority_category"]], on="kecamatan", how="left")
                m_ba = create_gap_map(gdf_map, score_col="healthcare_gap_score", selected_district=selected_kec)
                
            st_folium(m_ba, width=450, height=350, key="sim_ba_map")
