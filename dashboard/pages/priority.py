import streamlit as st
from dashboard.components.charts import create_gap_bar_chart, create_component_chart
from dashboard.components.district_detail import show_district_details

def show_page(df_gap, df_rca, df_features):
    st.markdown("## 🚨 Priority Ranking Index")
    st.caption("Detailed ranking of Surabaya's 31 subdistricts by their cumulative healthcare gaps.")
    st.markdown("---")
    
    # 1. Filter priority level
    levels = ["Semua", "Kritis", "Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
    selected_level = st.selectbox("Filter by Priority Level:", levels)
    
    # Merge datasets
    df_merged = df_gap.merge(df_rca[["kecamatan", "primary_root_cause"]], on="kecamatan", how="left")
    
    # Filter
    if selected_level != "Semua":
        df_filtered = df_merged[df_merged["priority_category"] == selected_level]
    else:
        df_filtered = df_merged.copy()
        
    col_list, col_chart = st.columns([6, 6])
    
    with col_list:
        st.markdown("#### Rank List")
        # Format display
        display_df = df_filtered[[
            "priority_rank", "kecamatan", "healthcare_gap_score", "priority_category", "primary_root_cause"
        ]].copy()
        display_df.columns = ["Rank", "Kecamatan", "Gap Score", "Category", "Root Cause"]
        display_df["Kecamatan"] = display_df["Kecamatan"].str.title()
        display_df["Root Cause"] = display_df["Root Cause"].str.replace("_", " ").str.title()
        
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=450)
        
    with col_chart:
        # Show gap chart
        fig_bar = create_gap_bar_chart(df_filtered)
        st.plotly_chart(fig_bar, use_container_width=True)
        
    st.markdown("---")
    
    # Selected Kecamatan details & subcomponents
    st.markdown("### 🔬 Sub-component Diagnostics")
    
    kec_list = sorted(df_gap["kecamatan"].str.title().tolist())
    selected_kec = st.selectbox("Select Kecamatan for Subcomponent Breakdown:", kec_list)
    
    if selected_kec:
        st.session_state.selected_district = selected_kec
        
        col_det, col_comp = st.columns([5, 7])
        with col_det:
            show_district_details(selected_kec, df_gap, df_features)
            
        with col_comp:
            row_gap = df_gap[df_gap["kecamatan"].str.strip().str.upper() == selected_kec.strip().upper()]
            if not row_gap.empty:
                fig_comp = create_component_chart(row_gap)
                st.plotly_chart(fig_comp, use_container_width=True)
