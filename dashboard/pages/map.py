import streamlit as st
from streamlit_folium import st_folium
from dashboard.components.maps import create_gap_map
from dashboard.components.district_detail import show_district_details

def show_page(gdf_spatial, df_gap, df_features, gdf_pkm, gdf_hospitals):
    st.markdown("## 🗺️ Healthcare Gap Map")
    st.caption("Interactive spatial mapping of Surabaya's subdistricts and geocoded facilities.")
    st.markdown("---")
    
    # 1. Map controls
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        show_pkm = st.checkbox("Show Puskesmas Pins 🏥", value=True)
    with col_c2:
        show_hosp = st.checkbox("Show Hospital Pins 🔴", value=True)
    with col_c3:
        # Dropdown selection fallback
        kec_options = ["None"] + sorted(df_gap["kecamatan"].str.title().tolist())
        default_idx = 0
        if st.session_state.selected_district:
            try:
                default_idx = kec_options.index(st.session_state.selected_district.title())
            except ValueError:
                default_idx = 0
                
        selected = st.selectbox("Select Kecamatan Profile", options=kec_options, index=default_idx)
        if selected != "None":
            st.session_state.selected_district = selected
        else:
            st.session_state.selected_district = None

    # Merge gap scores to spatial geodataframe (standardized case-insensitive)
    gdf_spatial_copy = gdf_spatial.copy()
    gdf_spatial_copy["kecamatan"] = gdf_spatial_copy["kecamatan"].str.strip().str.upper()
    df_gap_copy = df_gap.copy()
    df_gap_copy["kecamatan"] = df_gap_copy["kecamatan"].str.strip().str.upper()
    
    gdf_merged = gdf_spatial_copy.merge(
        df_gap_copy[["kecamatan", "healthcare_gap_score", "priority_category", "priority_rank"]],
        on="kecamatan",
        how="left"
    )
    
    # Map rendering
    gdf_pkm_overlay = gdf_pkm if show_pkm else None
    gdf_hosp_overlay = gdf_hospitals if show_hosp else None
    
    m = create_gap_map(
        gdf_merged, 
        score_col="healthcare_gap_score", 
        selected_district=st.session_state.selected_district,
        gdf_pkm=gdf_pkm_overlay,
        gdf_hospitals=gdf_hosp_overlay
    )
    
    col_map, col_details = st.columns([8, 4])
    
    with col_map:
        # Render map using streamlit-folium
        map_data = st_folium(m, width=800, height=500, key="gap_map")
        
        # Capture spatial clicks
        if map_data and map_data.get("last_active_drawing"):
            props = map_data["last_active_drawing"].get("properties", {})
            clicked_kec = props.get("kecamatan")
            if clicked_kec:
                st.session_state.selected_district = clicked_kec.title()
                st.rerun()

    with col_details:
        if st.session_state.selected_district:
            show_district_details(st.session_state.selected_district, df_gap, df_features)
        else:
            st.info("💡 Click on a subdistrict on the map or select from the dropdown to view detailed diagnostics.")
