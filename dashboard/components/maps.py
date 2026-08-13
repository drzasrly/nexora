import folium
from folium import Choropleth, GeoJson, Marker
import branca.colormap as cm

import pandas as pd

def get_choropleth_color(score):
    """
    Returns hex color for a gap score based on custom scale.
    """
    if pd.isna(score) or score is None:
        return "#475569" # fallback slate gray for unmatched districts
        
    if score <= 20.0:
        return "#10b981" # green
    elif score <= 40.0:
        return "#06b6d4" # cyan
    elif score <= 60.0:
        return "#f59e0b" # yellow/amber
    elif score <= 80.0:
        return "#f97316" # orange
    else:
        return "#ef4444" # red

def create_gap_map(gdf, score_col="healthcare_gap_score", selected_district=None, gdf_pkm=None, gdf_hospitals=None):
    """
    Generates a Folium Map showing choropleth boundaries and facility pins.
    """
    # Centroid of Surabaya
    m = folium.Map(location=[-7.279, 112.750], zoom_start=12, tiles="cartodb dark_matter")
    
    # Create colormap legend
    colormap = cm.LinearColormap(
        colors=["#10b981", "#06b6d4", "#f59e0b", "#f97316", "#ef4444"],
        index=[0, 25, 50, 75, 100],
        vmin=0, vmax=100,
        caption="Healthcare Gap Score"
    )
    colormap.add_to(m)
    
    # Render GeoJSON districts
    def style_function(feature):
        kec = feature["properties"].get("kecamatan", "").strip().upper()
        score = feature["properties"].get(score_col, 50.0)
        
        # Highlight selected
        is_selected = selected_district and selected_district.strip().upper() == kec
        weight = 3 if is_selected else 1
        color = "#ffffff" if is_selected else "#475569"
        
        return {
            "fillColor": get_choropleth_color(score),
            "color": color,
            "weight": weight,
            "fillOpacity": 0.7,
        }
        
    def highlight_function(feature):
        return {
            "weight": 3,
            "color": "#f8fafc",
            "fillOpacity": 0.85
        }

    # Prepare tooltips
    tooltip_fields = ["kecamatan", score_col]
    tooltip_aliases = ["Kecamatan:", "Gap Score:"]
    
    if "priority_category" in gdf.columns:
        tooltip_fields.append("priority_category")
        tooltip_aliases.append("Priority:")
    if "primary_root_cause" in gdf.columns:
        tooltip_fields.append("primary_root_cause")
        tooltip_aliases.append("Root Cause:")

    geojson = GeoJson(
        gdf,
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=True
        )
    )
    geojson.add_to(m)
    
    # Add Puskesmas pins (max 100 to prevent performance lag)
    if gdf_pkm is not None and not gdf_pkm.empty:
        pkm_group = folium.FeatureGroup(name="Puskesmas").add_to(m)
        for idx, row in gdf_pkm.head(100).iterrows():
            geom = row.geometry
            if geom and geom.geom_type == "Point":
                folium.Marker(
                    location=[geom.y, geom.x],
                    popup=f"<b>Puskesmas:</b> {row.get('nama_puskesmas', 'N/A')}<br>Kecamatan: {row.get('kecamatan', 'N/A')}",
                    icon=folium.Icon(color="cadetblue", icon="plus", prefix="fa")
                ).add_to(pkm_group)
                
    # Add Hospital pins
    if gdf_hospitals is not None and not gdf_hospitals.empty:
        hosp_group = folium.FeatureGroup(name="Rumah Sakit").add_to(m)
        for idx, row in gdf_hospitals.head(100).iterrows():
            geom = row.geometry
            if geom and geom.geom_type == "Point":
                folium.Marker(
                    location=[geom.y, geom.x],
                    popup=f"<b>Rumah Sakit:</b> {row.get('nama_faskes', 'N/A')}<br>Kecamatan: {row.get('kecamatan', 'N/A')}",
                    icon=folium.Icon(color="red", icon="heartbeat", prefix="fa")
                ).add_to(hosp_group)
                
    folium.LayerControl().add_to(m)
    return m
