import streamlit as st
import os
from src.recommendation_engine import generate_recommendation_report
from src.ai_engine import get_ai_justification

def show_page(df_gap, df_rca, df_features):
    st.markdown("## 🧠 AI Recommendation Engine")
    st.caption("Generate structured expert briefs and policy justification reports based on model analysis.")
    st.markdown("---")
    
    kec_list = sorted(df_gap["kecamatan"].str.title().tolist())
    
    # Sync selected kecamatan
    default_idx = 0
    if st.session_state.selected_district:
        try:
            default_idx = kec_list.index(st.session_state.selected_district.title())
        except ValueError:
            default_idx = 0
            
    selected_kec = st.selectbox("Select Kecamatan for AI Recommendation:", options=kec_list, index=default_idx)
    st.session_state.selected_district = selected_kec
    
    if selected_kec:
        kec_upper = selected_kec.strip().upper()
        row_rca = df_rca[df_rca["kecamatan"].str.strip().str.upper() == kec_upper]
        primary_rc = row_rca.iloc[0]["primary_root_cause"] if not row_rca.empty else "WORKFORCE_SHORTAGE"
        
        # Check if we have optimizer candidates from the session state
        top_cand = None
        if "optimizer_candidates" in st.session_state:
            top_cand = st.session_state.optimizer_candidates[0]
        else:
            # Generate a default candidate based on root cause if optimizer was not run yet (defensive fallback)
            if primary_rc == "WORKFORCE_SHORTAGE":
                top_cand = {
                    "intervention_id": "I01",
                    "intervention_name": "Redistribute Healthcare Workers",
                    "quantity": 10,
                    "unit": "person",
                    "cost": 500000000,
                    "projected_gap": max(0.0, float(df_gap[df_gap["kecamatan"].str.strip().str.upper() == kec_upper]["healthcare_gap_score"].iloc[0]) - 15.0),
                    "gap_reduction": 15.0,
                    "feasibility": "HIGH",
                    "alignment": "HIGH",
                    "resources_used": {"nakes": 10, "perawat": 6, "bidan": 4}
                }
            elif primary_rc == "FACILITY_LIMITS":
                top_cand = {
                    "intervention_id": "I03",
                    "intervention_name": "Add Facility Capacity",
                    "quantity": 4,
                    "unit": "bed",
                    "cost": 1000000000,
                    "projected_gap": max(0.0, float(df_gap[df_gap["kecamatan"].str.strip().str.upper() == kec_upper]["healthcare_gap_score"].iloc[0]) - 10.0),
                    "gap_reduction": 10.0,
                    "feasibility": "HIGH",
                    "alignment": "HIGH",
                    "resources_used": {"beds": 4, "faskes": 1}
                }
            else:
                top_cand = {
                    "intervention_id": "I05",
                    "intervention_name": "Combined Intervention",
                    "quantity": 2,
                    "unit": "package",
                    "cost": 1500000000,
                    "projected_gap": max(0.0, float(df_gap[df_gap["kecamatan"].str.strip().str.upper() == kec_upper]["healthcare_gap_score"].iloc[0]) - 16.0),
                    "gap_reduction": 16.0,
                    "feasibility": "HIGH",
                    "alignment": "HIGH",
                    "resources_used": {"nakes": 4, "beds": 6}
                }
                
        # Generate the report details
        budget = st.session_state.get("budget", 5000000000)
        report_data = generate_recommendation_report(selected_kec, primary_rc, top_cand, budget)
        
        # Display the report card
        st.markdown("### 📋 Executive Summary")
        col_rec1, col_rec2 = st.columns([6, 6])
        
        with col_rec1:
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, #1e1b4b, #0f172a);
                    border: 1px solid rgba(255,255,255,0.05);
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                    margin-bottom: 15px;
                ">
                    <div style="font-size: 0.85rem; font-weight: bold; text-transform: uppercase; color: #a78bfa;">AI CONFIDENCE LEVEL</div>
                    <div style="font-size: 2.2rem; font-weight: 800; color: #ffffff; margin-top: 5px;">{report_data["confidence"]}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        with col_rec2:
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, #062033, #082d47);
                    border: 1px solid rgba(255,255,255,0.05);
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                    margin-bottom: 15px;
                ">
                    <div style="font-size: 0.85rem; font-weight: bold; text-transform: uppercase; color: #38bdf8;">PROJECTED REDUCTION</div>
                    <div style="font-size: 2.2rem; font-weight: 800; color: #ffffff; margin-top: 5px;">-{report_data["improvement"]:.2f}%</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        # Display AI Justification
        st.markdown("---")
        ai_just = get_ai_justification(selected_kec, primary_rc, top_cand)
        st.markdown(ai_just)
        
        st.markdown("---")
        
        # Read the generated report markdown to show and provide download button
        report_path = report_data["report_path"]
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                report_content = f.read()
                
            st.markdown("### 📃 Full Recommendation Report Preview")
            st.text_area("Markdown Report Content", report_content, height=250)
            
            st.download_button(
                label="📥 DOWNLOAD RECOMMENDATION REPORT (markdown)",
                data=report_content,
                file_name=f"recommendation_report_{selected_kec.lower().replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )
