import streamlit as st

def show_district_details(district_name, df_gap, df_features):
    """
    Renders detailed information and KPIs for a selected district.
    """
    kec_clean = district_name.strip().upper()
    row_gap = df_gap[df_gap["kecamatan"].str.strip().str.upper() == kec_clean]
    row_feat = df_features[df_features["kecamatan"].str.strip().str.upper() == kec_clean]
    
    if row_gap.empty or row_feat.empty:
        st.warning(f"Data details for Kecamatan {district_name} are unavailable.")
        return
        
    score = row_gap.iloc[0]["healthcare_gap_score"]
    rank = row_gap.iloc[0]["priority_rank"]
    category = row_gap.iloc[0]["priority_category"]
    
    st.markdown(f"### Kecamatan {district_name.title()} Detailed Analytics")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Healthcare Gap Score", f"{score:.2f}")
    with col2:
        st.metric("City Priority Rank", f"#{rank} of 31")
    with col3:
        st.metric("Classification", category)
        
    st.markdown("---")
    
    # Show Demographics & Facilities count
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("##### 👥 Demographic Profile")
        st.write(f"- **Population size**: {row_feat.iloc[0]['jumlah_penduduk'] * 1000:,.0f} people")
        st.write(f"- **Density index**: {row_feat.iloc[0]['kepadatan_penduduk']:.2f} per km²")
        st.write(f"- **Dominant Disease**: {row_feat.iloc[0]['jenis_penyakit_dominan']}")
        st.write(f"- **Total Disease Cases**: {row_feat.iloc[0]['total_kasus_penyakit']:,} cases")
    with col_b:
        st.markdown("##### 🏥 Health Infrastructure")
        st.write(f"- **Total Facilities**: {int(row_feat.iloc[0]['total_faskes'])}")
        st.write(f"- **Puskesmas (Primary Care)**: {int(row_feat.iloc[0]['jumlah_puskesmas'])}")
        st.write(f"- **Healthcare Workers**: {int(row_feat.iloc[0]['total_tenaga_kesehatan'])} practitioners")
        st.write(f"- **Total Hospital Beds**: {int(row_feat.iloc[0]['total_tempat_tidur'])} beds")
        
    st.markdown("---")
    kec_name_lower = kec_clean.lower().replace(" ", "_")
    map_url = f"http://localhost:8000/outputs/gis/kecamatan_maps/{kec_name_lower}.html"
    st.markdown(
        f'<a href="{map_url}" target="_blank" style="text-decoration: none;">'
        f'<button style="width: 100%; padding: 10px; background-color: #6366f1; color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;">'
        f'🗺️ Open Focused GIS Map'
        f'</button>'
        f'</a>', 
        unsafe_allow_html=True
    )
    st.caption("💡 Opens in a new tab (requires the serve.py server to be running on port 8000).")

