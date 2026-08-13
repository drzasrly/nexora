import streamlit as st
import pandas as pd
from src.intervention_optimizer import optimize_interventions

def show_page(df_gap, df_rca, df_features, config):
    st.markdown("## 🎯 Intervention Optimizer")
    st.caption("Identify resource allocation plans aligned with subdistrict bottlenecks under budget constraints.")
    st.markdown("---")
    
    kec_list = sorted(df_gap["kecamatan"].str.title().tolist())
    
    # Sync selected kecamatan
    default_idx = 0
    if st.session_state.selected_district:
        try:
            default_idx = kec_list.index(st.session_state.selected_district.title())
        except ValueError:
            default_idx = 0
            
    selected_kec = st.selectbox("Select Kecamatan for Optimization:", options=kec_list, index=default_idx)
    st.session_state.selected_district = selected_kec
    
    st.markdown("#### Input Allocation & Budget Constraints")
    col_b, col_r1, col_r2, col_r3 = st.columns(4)
    with col_b:
        budget = st.number_input("Budget Limit (IDR)", min_value=100000000, max_value=10000000000, value=5000000000, step=100000000, format="%d")
    with col_r1:
        doctors_avail = st.slider("Doctors Available", 0, 50, 10)
    with col_r2:
        nurses_avail = st.slider("Nurses Available", 0, 100, 20)
    with col_r3:
        beds_avail = st.slider("Facilities (Beds) Available", 0, 30, 5)
        
    resources_available = {
        "nakes": doctors_avail + nurses_avail,
        "doctors": doctors_avail,
        "nurses": nurses_avail,
        "beds": beds_avail
    }
    
    if selected_kec:
        kec_upper = selected_kec.strip().upper()
        row_rca = df_rca[df_rca["kecamatan"].str.strip().str.upper() == kec_upper]
        primary_rc = row_rca.iloc[0]["primary_root_cause"] if not row_rca.empty else "WORKFORCE_SHORTAGE"
        
        if st.button("🚀 FIND BEST INTERVENTION", use_container_width=True):
            # Run optimizer
            candidates = optimize_interventions(df_features, selected_kec, budget, resources_available, config)
            
            if not candidates:
                st.warning("No feasible intervention candidates found within constraints.")
                return
                
            # Store in session state for cross-page utilization
            st.session_state.optimizer_candidates = candidates
            
        if "optimizer_candidates" in st.session_state:
            candidates = st.session_state.optimizer_candidates
            top_opt = candidates[0]
            
            st.markdown("---")
            st.markdown("### 🏆 Recommended Optimal Plan")
            
            col_o1, col_o2 = st.columns([5, 7])
            with col_o1:
                # Custom recommended display box
                cost = top_opt["cost"]
                qty = top_opt["quantity"]
                unit = top_opt["unit"]
                name = top_opt["intervention_name"]
                red = top_opt["gap_reduction"]
                proj = top_opt["projected_gap"]
                feas = top_opt["feasibility"]
                
                feas_color = "#10b981" if feas == "HIGH" else ("#f59e0b" if feas == "MEDIUM" else "#ef4444")
                
                st.markdown(
                    f"""
                    <div style="
                        background: linear-gradient(135deg, #022c22, #064e3b);
                        border: 1px solid #10b981;
                        border-radius: 12px;
                        padding: 24px;
                        color: #ffffff;
                    ">
                        <span style="color: #34d399; font-size: 0.85rem; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em;">RECOMMENDED ACTION</span>
                        <h3 style="margin-top: 5px; color: #ffffff; font-weight: 800; font-size: 1.5rem;">{name}</h3>
                        <hr style="border-color: rgba(16,185,129,0.2); margin: 15px 0;">
                        <p style="margin: 5px 0; font-size: 0.95rem;"><b>Quantity:</b> {qty} {unit}(s)</p>
                        <p style="margin: 5px 0; font-size: 0.95rem;"><b>Est. Cost:</b> Rp {cost:,.0f}</p>
                        <p style="margin: 5px 0; font-size: 0.95rem;"><b>Projected Gap:</b> {proj:.2f} (reduced by {red:.2f}%)</p>
                        <p style="margin: 5px 0; font-size: 0.95rem;"><b>Feasibility:</b> <span style="color: {feas_color}; font-weight:bold;">{feas}</span></p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            with col_o2:
                st.markdown("#### Plan Rationale & Strategy")
                st.write(
                    f"Intervensi **{name}** direkomendasikan karena memberikan dampak optimal terhadap skor gap "
                    f"Kecamatan **{selected_kec}** dengan pengurangan skor gap sebesar **{red:.2f}%**.\n\n"
                    f"Intervensi ini dipilih karena memiliki keselarasan tinggi dengan akar masalah utama "
                    f"(**{primary_rc.replace('_', ' ').title()}**) dan memiliki tingkat kelayakan (**Feasibility: {feas}**) "
                    f"yang dinilai aman terhadap ketersediaan anggaran serta alokasi sumber daya tenaga kesehatan / fasilitas fisik kota."
                )
                
            st.markdown("---")
            st.markdown("#### 🔄 Alternative Scenarios & Sensitivity Analysis")
            
            # Format alternatives table
            alt_records = []
            for i, cand in enumerate(candidates[1:]):
                alt_records.append({
                    "Alternative ID": f"Alt {i+1}",
                    "Intervention Option": cand["intervention_name"],
                    "Quantity": f"{cand['quantity']} {cand['unit']}",
                    "Cost (IDR)": f"Rp {cand['cost']:,.0f}",
                    "Projected Gap": f"{cand['projected_gap']:.2f}",
                    "Reduction Impact": f"{cand['gap_reduction']:.2f}%",
                    "Feasibility": cand["feasibility"]
                })
            df_alt = pd.DataFrame(alt_records)
            if not df_alt.empty:
                st.dataframe(df_alt, use_container_width=True, hide_index=True)
            else:
                st.write("No alternative packages meet budget and resource constraints.")
