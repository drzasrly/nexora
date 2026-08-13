import streamlit as st
from dashboard.components.cards import metric_card
from dashboard.components.charts import create_priority_chart, create_root_cause_chart

def show_page(df_gap, df_rca, df_features):
    st.markdown("## 🏙️ Surabaya City Overview")
    st.caption("Strategic high-level healthcare capacity and accessibility metrics.")
    st.markdown("---")
    
    # 1. KPIs Row
    total_districts = len(df_gap)
    total_facilities = int(df_features["total_faskes"].sum())
    total_workers = int(df_features["total_tenaga_kesehatan"].sum())
    avg_gap = df_gap["healthcare_gap_score"].mean()
    critical_count = (df_gap["priority_category"] == "Kritis").sum()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        metric_card("Districts", f"{total_districts}", color_bg="linear-gradient(135deg, #1e293b, #0f172a)")
    with col2:
        metric_card("Facilities", f"{total_facilities:,}", color_bg="linear-gradient(135deg, #0f766e, #115e59)")
    with col3:
        metric_card("Nakes (Staff)", f"{total_workers:,}", color_bg="linear-gradient(135deg, #0369a1, #075985)")
    with col4:
        metric_card("Avg Gap Score", f"{avg_gap:.1f}", color_bg="linear-gradient(135deg, #7c3aed, #6d28d9)")
    with col5:
        metric_card("Critical Gaps", f"{critical_count}", color_bg="linear-gradient(135deg, #b91c1c, #991b1b)")
        
    st.markdown("---")
    
    # 2. Charts & Top Priorities Row
    col_left, col_right = st.columns([7, 5])
    
    with col_left:
        st.markdown("#### 🚨 Top 5 Priority Districts")
        top_5 = df_gap.sort_values("healthcare_gap_score", ascending=False).head(5)
        # Merge with root cause
        top_5_merged = pd_merge = top_5.merge(df_rca[["kecamatan", "primary_root_cause"]], on="kecamatan", how="left")
        
        # Format table columns
        top_5_display = top_5_merged[[
            "priority_rank", "kecamatan", "healthcare_gap_score", "priority_category", "primary_root_cause"
        ]].copy()
        top_5_display.columns = ["Rank", "Kecamatan", "Gap Score", "Priority Level", "Primary Root Cause"]
        top_5_display["Kecamatan"] = top_5_display["Kecamatan"].str.title()
        top_5_display["Primary Root Cause"] = top_5_display["Primary Root Cause"].str.replace("_", " ").str.title()
        
        st.dataframe(top_5_display, use_container_width=True, hide_index=True)
        
    with col_right:
        st.markdown("#### 🎯 Priority Distribution")
        fig_pie = create_priority_chart(df_gap)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    st.markdown("---")
    
    # 3. Root Cause distributions
    col_rc_left, col_rc_right = st.columns([6, 6])
    with col_rc_left:
        st.markdown("#### 🔍 Primary Contributors Breakdown")
        fig_rc = create_root_cause_chart(df_rca)
        st.plotly_chart(fig_rc, use_container_width=True)
        
    with col_rc_right:
        st.markdown("#### ℹ️ Quick Diagnostic Summary")
        st.info(
            f"Kecamatan dengan gap kesehatan tertinggi saat ini adalah **{top_5.iloc[0]['kecamatan'].title()}** "
            f"dengan skor gap **{top_5.iloc[0]['healthcare_gap_score']:.1f} ({top_5.iloc[0]['priority_category']})**.\n\n"
            f"Secara makro, mayoritas kecamatan di Surabaya didominasi oleh isu ketimpangan **{df_rca['primary_root_cause'].value_counts().idxmax().replace('_', ' ').title()}** "
            f"diikuti dengan isu logistik/kapasitas fasilitas fisik."
        )
