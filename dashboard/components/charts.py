import plotly.graph_objects as go
import plotly.express as px

def create_gap_bar_chart(df):
    """
    Renders a sorted bar chart of subdistrict gap scores.
    """
    df_sorted = df.sort_values("healthcare_gap_score", ascending=True)
    
    fig = px.bar(
        df_sorted,
        y="kecamatan",
        x="healthcare_gap_score",
        color="healthcare_gap_score",
        color_continuous_scale="Reds",
        orientation="h",
        labels={"healthcare_gap_score": "Gap Score", "kecamatan": "Kecamatan"},
        title="Healthcare Gap Score by Kecamatan"
    )
    
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#cbd5e1",
        xaxis=dict(showgrid=True, gridcolor="#334155"),
        yaxis=dict(showgrid=False),
        coloraxis_showscale=False,
        height=600,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    return fig

def create_component_chart(df_row):
    """
    Renders a bar chart showing the sub-component gap index scores for a single district.
    """
    components = ["Demand Score", "Workforce Gap", "Facility Gap", "Disease Need"]
    values = [
        float(df_row["demand_score"].iloc[0]),
        float(df_row["workforce_gap"].iloc[0]),
        float(df_row["facility_gap"].iloc[0]),
        float(df_row["disease_need_score"].iloc[0])
    ]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=components,
        y=values,
        marker_color=["#38bdf8", "#fb7185", "#fbbf24", "#a78bfa"],
        text=[f"{v:.2f}" for v in values],
        textposition="auto"
    ))
    
    fig.update_layout(
        title=f"Sub-component Scores Breakdown",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#cbd5e1",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#334155", range=[0, 1.05]),
        height=350,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    return fig

def create_before_after_chart(before, after):
    """
    Renders a side-by-side comparison chart for what-if simulations.
    """
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Before Intervention", "After Intervention"],
        y=[before, after],
        marker_color=["#ef4444", "#10b981"],
        text=[f"{before:.2f}", f"{after:.2f}"],
        textposition="auto",
        width=0.4
    ))
    
    fig.update_layout(
        title="Simulation Impact: Gap Score Comparison",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#cbd5e1",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#334155", range=[0, 105]),
        height=350,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    return fig

def create_priority_chart(df):
    """
    Renders a pie/doughnut chart of priority category distributions.
    """
    counts = df["priority_category"].value_counts().reset_index()
    counts.columns = ["Priority", "Count"]
    
    # Custom color map
    color_map = {
        "Kritis": "#ef4444",
        "Sangat Tinggi": "#f97316",
        "Tinggi": "#f59e0b",
        "Sedang": "#06b6d4",
        "Rendah": "#10b981"
    }
    
    fig = px.pie(
        counts,
        names="Priority",
        values="Count",
        hole=0.4,
        color="Priority",
        color_discrete_map=color_map,
        title="Priority Classification Distribution"
    )
    
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#cbd5e1",
        margin=dict(l=0, r=0, t=40, b=0),
        height=300
    )
    return fig

def create_root_cause_chart(df_rca):
    """
    Renders a horizontal bar chart showing primary root causes distribution.
    """
    counts = df_rca["primary_root_cause"].value_counts().reset_index()
    counts.columns = ["Root Cause", "Count"]
    
    # Clean name labels
    counts["Root Cause"] = counts["Root Cause"].apply(lambda x: x.replace("_", " ").title())
    
    fig = px.bar(
        counts,
        y="Root Cause",
        x="Count",
        color="Count",
        color_continuous_scale="Blues",
        orientation="h",
        title="Primary Root Cause Distribution"
    )
    
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#cbd5e1",
        xaxis=dict(showgrid=True, gridcolor="#334155", dtick=1),
        yaxis=dict(showgrid=False),
        coloraxis_showscale=False,
        height=300,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    return fig
