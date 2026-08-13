import streamlit as st
from dashboard.components.charts import create_component_chart

def show_page(df_gap, df_rca, df_features):
    st.markdown("## 🔍 Root Cause Analysis")
    st.caption("Identify primary bottlenecks and key contributing factors for each district.")
    st.markdown("---")
    
    kec_list = sorted(df_gap["kecamatan"].str.title().tolist())
    
    # Sync with global session state selection
    default_idx = 0
    if st.session_state.selected_district:
        try:
            default_idx = kec_list.index(st.session_state.selected_district.title())
        except ValueError:
            default_idx = 0
            
    selected_kec = st.selectbox("Select Kecamatan for Root Cause Profile:", options=kec_list, index=default_idx)
    st.session_state.selected_district = selected_kec
    
    if selected_kec:
        kec_upper = selected_kec.strip().upper()
        row_gap = df_gap[df_gap["kecamatan"].str.strip().str.upper() == kec_upper]
        row_rca = df_rca[df_rca["kecamatan"].str.strip().str.upper() == kec_upper]
        row_feat = df_features[df_features["kecamatan"].str.strip().str.upper() == kec_upper]
        
        if row_gap.empty or row_rca.empty or row_feat.empty:
            st.error("No root cause data available for this district.")
            return
            
        gap_score = row_gap.iloc[0]["healthcare_gap_score"]
        priority = row_gap.iloc[0]["priority_category"]
        primary_rc = row_rca.iloc[0]["primary_root_cause"]
        
        col_text, col_chart = st.columns([6, 6])
        
        with col_text:
            st.markdown("#### Primary Contributor")
            
            rc_clean = primary_rc.replace("_", " ").title()
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, #1e1b4b, #311042);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 12px;
                    padding: 20px;
                    text-align: center;
                    margin-bottom: 20px;
                ">
                    <span style="color: #cbd5e1; font-size: 0.95rem; font-weight: 500;">PRIMARY BOTTLENECK</span>
                    <h2 style="color: #f43f5e; font-size: 1.8rem; font-weight: 800; margin-top: 5px;">{rc_clean}</h2>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Diagnostic narrative (Section 19: do not call it causal, use "faktor kontributor utama")
            st.markdown("#### Diagnostic Report")
            narrative = f"""
            Kecamatan **{selected_kec}** memiliki skor Healthcare Gap sebesar **{gap_score:.1f}**, yang termasuk dalam kategori prioritas **{priority}**. 
            
            Berdasarkan analisis statistik modular, **faktor kontributor utama** ketimpangan di wilayah ini teridentifikasi sebagai **{rc_clean}**.
            """
            st.write(narrative)
            
            # Sub-score details listing
            st.markdown("##### Resource Ratios Detail")
            st.write(f"- **Visits per 1000**: {row_feat.iloc[0]['visits_per_1000']:.3f} (demographic demand pressure)")
            st.write(f"- **Nakes per 1000**: {row_feat.iloc[0]['nakes_per_1000']:.3f} (workforce density ratio)")
            st.write(f"- **Faskes per 100k**: {row_feat.iloc[0]['faskes_per_100k']:.3f} (facility physical density)")
            st.write(f"- **Disease burden index**: {row_feat.iloc[0]['disease_per_1000']:.3f} (relative sickness volume)")
            
        with col_chart:
            fig_comp = create_component_chart(row_gap)
            st.plotly_chart(fig_comp, use_container_width=True)
