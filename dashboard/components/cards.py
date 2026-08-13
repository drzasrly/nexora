import streamlit as st

def metric_card(label, value, delta=None, color_bg="linear-gradient(135deg, #1e293b, #0f172a)"):
    """
    Renders a premium metric card with drop-shadows and clean typography.
    """
    delta_html = ""
    if delta is not None:
        delta_color = "#34d399" if delta > 0 else "#f87171"
        delta_icon = "↑" if delta > 0 else "↓"
        delta_html = f'<div style="color: {delta_color}; font-size: 0.85rem; font-weight: bold; margin-top: 4px;">{delta_icon} {abs(delta):.1f}% improvement</div>'
        
    card_html = f"""
    <div style="
        background: {color_bg};
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        margin-bottom: 15px;
    ">
        <div style="color: #94a3b8; font-size: 0.9rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">{label}</div>
        <div style="color: #ffffff; font-size: 2.2rem; font-weight: 800; margin-top: 5px; font-family: 'Outfit', sans-serif;">{value}</div>
        {delta_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def priority_card(district, rank, score, category, root_cause):
    """
    Renders a specialized priority card showing rank, status badge, and primary root cause.
    """
    cat_colors = {
        "Kritis": "linear-gradient(135deg, #991b1b, #7f1d1d)",
        "Sangat Tinggi": "linear-gradient(135deg, #c2410c, #7c2d12)",
        "Tinggi": "linear-gradient(135deg, #b45309, #78350f)",
        "Sedang": "linear-gradient(135deg, #0e7490, #164e63)",
        "Rendah": "linear-gradient(135deg, #065f46, #064e3b)"
    }
    
    bg = cat_colors.get(category, "linear-gradient(135deg, #1e293b, #0f172a)")
    
    card_html = f"""
    <div style="
        background: {bg};
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        margin-bottom: 15px;
        color: #ffffff;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 1.5rem; font-weight: 800;">#{rank} {district.title()}</span>
            <span style="background: rgba(255,255,255,0.15); border-radius: 20px; padding: 4px 12px; font-size: 0.8rem; font-weight: bold; text-transform: uppercase;">{category}</span>
        </div>
        <div style="margin-top: 15px; font-size: 0.95rem; opacity: 0.9;">
            <strong>Gap Score:</strong> {score:.2f}
        </div>
        <div style="margin-top: 5px; font-size: 0.95rem; opacity: 0.9;">
            <strong>Primary Driver:</strong> {root_cause.replace('_', ' ').title()}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
