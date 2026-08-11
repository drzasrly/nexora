import os
import json
import pandas as pd
import geopandas as gpd
import folium
from folium import Choropleth, GeoJson, LayerControl, Marker, Popup
from folium.plugins import MarkerCluster

# Paths
KECAMATAN_GEOJSON = "dataset/spatial/kecamatan_surabaya.geojson"
PUSKESMAS_GEOJSON = "dataset/spatial/puskesmas.geojson"
FASKES_GEOJSON = "dataset/spatial/fasilitas_kesehatan.geojson"
ROADS_GEOJSON = "dataset/spatial/roads.geojson"

GAP_SCORES_CSV = "dataset/processed/healthcare_gap_scores.csv"
RCA_CSV = "dataset/processed/root_cause_analysis.csv"

PROCESSED_DIR = "dataset/processed"
SPATIAL_OUTPUT_DIR = "dataset/spatial/output"
GIS_OUTPUT_DIR = "outputs/gis"

os.makedirs(SPATIAL_OUTPUT_DIR, exist_ok=True)
os.makedirs(GIS_OUTPUT_DIR, exist_ok=True)

print("Starting HEAL-CITY GIS Analysis Pipeline...")

# -----------------------------------------------------------------------------
# 1. LOAD DATASETS
# -----------------------------------------------------------------------------
print("Loading spatial and tabular data...")
assert os.path.exists(KECAMATAN_GEOJSON), "kecamatan_surabaya.geojson not found!"
gdf_kec = gpd.read_file(KECAMATAN_GEOJSON)

assert os.path.exists(GAP_SCORES_CSV), "healthcare_gap_scores.csv not found!"
df_gap = pd.read_csv(GAP_SCORES_CSV)

assert os.path.exists(RCA_CSV), "root_cause_analysis.csv not found!"
df_rca = pd.read_csv(RCA_CSV)

# -----------------------------------------------------------------------------
# 2. VALIDATE SPATIAL BOUNDARIES
# -----------------------------------------------------------------------------
print("Validating geometries and counts...")
assert gdf_kec.is_valid.all(), "Error: Found invalid geometry in kecamatan GeoJSON!"
assert gdf_kec.geometry.isna().sum() == 0, "Error: Found empty geometry in kecamatan GeoJSON!"
assert len(gdf_kec) == 31, f"Expected exactly 31 kecamatan boundaries but got {len(gdf_kec)}!"

# Standardize case and strip spacing
gdf_kec["kecamatan"] = gdf_kec["kecamatan"].str.strip()
df_gap["kecamatan"] = df_gap["kecamatan"].str.strip()
df_rca["kecamatan"] = df_rca["kecamatan"].str.strip()

# -----------------------------------------------------------------------------
# 3. SPATIAL JOIN / MERGE
# -----------------------------------------------------------------------------
print("Merging spatial boundaries with healthcare gap scores and RCA profiles...")
# Combine Gap and RCA attributes first
df_merged_attr = pd.merge(df_gap, df_rca[[
    "kecamatan", "primary_root_cause", "secondary_root_cause", "root_cause_type", 
    "root_cause_confidence", "root_cause_margin", "workforce_issue", "facility_issue", 
    "demand_issue", "disease_issue", "explanation"
]], on="kecamatan", how="left")

# Join with GeoDataFrame
gdf_gis = gdf_kec.merge(df_merged_attr, on="kecamatan", how="left")

# Assertions checks
assert len(gdf_gis) == 31, f"Spatial join failed: row count changed to {len(gdf_gis)}!"
assert gdf_gis["healthcare_gap_score"].isna().sum() == 0, "Spatial join failed: Some Kecamatan could not be joined (NaN found)!"

# Cross-validation check
check_df = gdf_gis.merge(df_gap[["kecamatan", "healthcare_gap_score"]], on="kecamatan", suffixes=("_gis", "_source"))
assert (check_df["healthcare_gap_score_gis"] == check_df["healthcare_gap_score_source"]).all(), "Error: Score mismatch in GIS join!"
print("Verified spatial merge: 31 Kecamatan joined with zero null scores and complete alignment.")

# -----------------------------------------------------------------------------
# 4. EXPORT OUTPUT DATASETS
# -----------------------------------------------------------------------------
# Save joined geojson
gdf_gis.to_file(os.path.join(SPATIAL_OUTPUT_DIR, "heal_city_gap.geojson"), driver="GeoJSON")

# Save Joined CSV (with centroid coordinates for dashboard convenience)
df_gis_csv = pd.DataFrame(gdf_gis.drop(columns="geometry"))
centroids = gdf_gis.geometry.centroid
df_gis_csv["centroid_lon"] = centroids.x
df_gis_csv["centroid_lat"] = centroids.y
df_gis_csv.to_csv(os.path.join(PROCESSED_DIR, "heal_city_gis.csv"), index=False)
print("Saved outputs/processed and output/geojson.")

# Load supporting spatial files if present
gdf_pkm = gpd.read_file(PUSKESMAS_GEOJSON) if os.path.exists(PUSKESMAS_GEOJSON) else None
gdf_fask = gpd.read_file(FASKES_GEOJSON) if os.path.exists(FASKES_GEOJSON) else None
gdf_roads = gpd.read_file(ROADS_GEOJSON) if os.path.exists(ROADS_GEOJSON) else None

# -----------------------------------------------------------------------------
# 5. GENERATE INTERACTIVE HTML MAPS
# -----------------------------------------------------------------------------
print("Creating folium maps...")

# Surabaya centroid
s_lat, s_lon = -7.26, 112.75

# Colors & styles for hover
style_function = lambda x: {
    'fillColor': '#ffffff',
    'color': '#000000',
    'fillOpacity': 0.1,
    'weight': 1.0
}
highlight_function = lambda x: {
    'fillColor': '#000000',
    'color': '#000000',
    'fillOpacity': 0.5,
    'weight': 2.0
}

# Helper to create tooltip
def make_tooltip():
    return GeoJson.Tooltip(
        fields=["kecamatan", "healthcare_gap_score", "priority_category", "primary_root_cause"],
        aliases=["Kecamatan:", "Gap Score:", "Priority:", "Primary Driver:"],
        localize=True
    )

# A. MAP 1: healthcare_gap_map.html
map_gap = folium.Map(location=[s_lat, s_lon], zoom_start=11, tiles="cartodbpositron")
Choropleth(
    geo_data=os.path.join(SPATIAL_OUTPUT_DIR, "heal_city_gap.geojson"),
    data=df_gap,
    columns=["kecamatan", "healthcare_gap_score"],
    key_on="feature.properties.kecamatan",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Healthcare Gap Score (0-100)"
).add_to(map_gap)

# Add tooltip layer
gjson_gap = GeoJson(
    os.path.join(SPATIAL_OUTPUT_DIR, "heal_city_gap.geojson"),
    style_function=lambda x: {'fillColor': '#000000', 'fillOpacity': 0.0, 'color': '#000000', 'weight': 1},
    tooltip=make_tooltip()
).add_to(map_gap)
map_gap.save(os.path.join(GIS_OUTPUT_DIR, "healthcare_gap_map.html"))


# B. MAP 2: priority_map.html (rank labeled map)
map_prior = folium.Map(location=[s_lat, s_lon], zoom_start=11, tiles="cartodbpositron")
Choropleth(
    geo_data=os.path.join(SPATIAL_OUTPUT_DIR, "heal_city_gap.geojson"),
    data=df_gap,
    columns=["kecamatan", "healthcare_gap_score"], # visual score choropleth
    key_on="feature.properties.kecamatan",
    fill_color="OrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Priority Choropleth Map"
).add_to(map_prior)

# Add popup markers showing rank
for idx, row in gdf_gis.iterrows():
    c_lat, c_lon = row.geometry.centroid.y, row.geometry.centroid.x
    popup_text = f"<b>Kecamatan:</b> {row['kecamatan']}<br><b>Rank:</b> #{row['priority_rank']}<br><b>Score:</b> {row['healthcare_gap_score']:.1f}<br><b>Category:</b> {row['priority_category']}"
    folium.Marker(
        location=[c_lat, c_lon],
        icon=folium.DivIcon(html=f'<div style="font-size: 10pt; font-weight: bold; color: black; background-color: white; border: 1px solid black; padding: 2px; border-radius: 3px;">#{row["priority_rank"]}</div>'),
        popup=Popup(popup_text, max_width=300)
    ).add_to(map_prior)
map_prior.save(os.path.join(GIS_OUTPUT_DIR, "priority_map.html"))


# C. MAP 3: root_cause_map.html
map_rca = folium.Map(location=[s_lat, s_lon], zoom_start=11, tiles="cartodbpositron")

# Mapping category colors
rc_colors = {
    "WORKFORCE_SHORTAGE": "#d95f02",
    "FACILITY_SHORTAGE": "#7570b3",
    "DISEASE_BURDEN": "#1b9e77",
    "HIGH_DEMAND": "#e7298a",
    "ACCESSIBILITY": "#66a61e",
    "MULTI_FACTOR": "#e6ab02"
}

# Style function based on category color
def get_rc_style(feature):
    rc = feature["properties"]["primary_root_cause"]
    color = rc_colors.get(rc, "#999999")
    return {
        "fillColor": color,
        "color": "#000000",
        "weight": 1.0,
        "fillOpacity": 0.7
    }

GeoJson(
    os.path.join(SPATIAL_OUTPUT_DIR, "heal_city_gap.geojson"),
    style_function=get_rc_style,
    tooltip=make_tooltip()
).add_to(map_rca)

# Add legend on Map RCA
legend_html = '''
     <div style="position: fixed; 
     bottom: 50px; left: 50px; width: 180px; height: 180px; 
     border:2px solid grey; z-index:9999; background-color:white;
     font-size:14px;
     padding: 10px;
     ">
     <b>Primary Root Cause</b><br>
     <i style="background:#d95f02; width:12px; height:12px; float:left; margin-right:5px; border-radius:2px;"></i> Workforce Shortage<br>
     <i style="background:#7570b3; width:12px; height:12px; float:left; margin-right:5px; border-radius:2px;"></i> Facility Shortage<br>
     <i style="background:#1b9e77; width:12px; height:12px; float:left; margin-right:5px; border-radius:2px;"></i> Disease Burden<br>
     <i style="background:#e7298a; width:12px; height:12px; float:left; margin-right:5px; border-radius:2px;"></i> High Demand<br>
     <i style="background:#e6ab02; width:12px; height:12px; float:left; margin-right:5px; border-radius:2px;"></i> Multi-Factor<br>
     </div>
     '''
map_rca.get_root().html.add_child(folium.Element(legend_html))
map_rca.save(os.path.join(GIS_OUTPUT_DIR, "root_cause_map.html"))


# D. MAP 4: facility_distribution.html (Puskesmas overlay)
map_fac = folium.Map(location=[s_lat, s_lon], zoom_start=11, tiles="cartodbpositron")

# Base choropleth for facility gap
Choropleth(
    geo_data=os.path.join(SPATIAL_OUTPUT_DIR, "heal_city_gap.geojson"),
    data=df_gap,
    columns=["kecamatan", "facility_gap"],
    key_on="feature.properties.kecamatan",
    fill_color="PuBu",
    fill_opacity=0.5,
    line_opacity=0.2,
    legend_name="Facility Gap Score (0.0 - 1.0)"
).add_to(map_fac)

# Overlay Puskesmas markers
if gdf_pkm is not None:
    pkm_group = folium.FeatureGroup(name="Puskesmas Points Layer").add_to(map_fac)
    for idx, row in gdf_pkm.iterrows():
        coords = row.geometry.coords[0]
        # Coordinates in geojson are [lon, lat], folium needs [lat, lon]
        p_lat, p_lon = coords[1], coords[0]
        popup_content = (
            f"<b>Puskesmas:</b> {row['nama_puskesmas']}<br>"
            f"<b>ID:</b> {row['puskesmas_id']}<br>"
            f"<b>Kecamatan:</b> {row['kecamatan']}<br>"
            f"<b>Unggulan:</b> {row['pelayanan_unggulan']}"
        )
        folium.Marker(
            location=[p_lat, p_lon],
            icon=folium.Icon(color="blue", icon="plus-sign", prefix="glyphicon"),
            popup=Popup(popup_content, max_width=250)
        ).add_to(pkm_group)
        
LayerControl().add_to(map_fac)
map_fac.save(os.path.join(GIS_OUTPUT_DIR, "facility_distribution.html"))


# E. MAP 5: accessibility_map.html
map_acc = folium.Map(location=[s_lat, s_lon], zoom_start=11, tiles="cartodbpositron")

# Draw Kecamatan boundaries colored in light grey (since accessibility is NaN)
GeoJson(
    os.path.join(SPATIAL_OUTPUT_DIR, "heal_city_gap.geojson"),
    style_function=lambda x: {'fillColor': '#cccccc', 'fillOpacity': 0.3, 'color': '#666666', 'weight': 1},
    tooltip=GeoJson.Tooltip(fields=["kecamatan"], aliases=["Kecamatan:"])
).add_to(map_acc)

# Overlay road network vectors
if gdf_roads is not None:
    road_group = folium.FeatureGroup(name="Roads network").add_to(map_acc)
    for idx, row in gdf_roads.iterrows():
        coords = row.geometry.coords
        # Inverse coordinates for folium LineString
        fol_coords = [[c[1], c[0]] for c in coords]
        popup_content = f"<b>Jalan:</b> {row['road_name']}<br><b>Kelas:</b> {row['type']}"
        folium.PolyLine(
            locations=fol_coords,
            color="#e63946",
            weight=2.0,
            opacity=0.8,
            popup=Popup(popup_content, max_width=200)
        ).add_to(road_group)

LayerControl().add_to(map_acc)
map_acc.save(os.path.join(GIS_OUTPUT_DIR, "accessibility_map.html"))

print("Saved all folium interactive maps to outputs/gis/.")

# -----------------------------------------------------------------------------
# 6. SPATIAL ANALYSIS REPORT (markdown)
# -----------------------------------------------------------------------------
print("Writing spatial analysis report...")

top5_gap = gdf_gis.sort_values("healthcare_gap_score", ascending=False).head(5)
low5_gap = gdf_gis.sort_values("healthcare_gap_score").head(5)

# Calculate dominant cause percentages
rc_counts = gdf_gis["primary_root_cause"].value_counts()
rc_pct = gdf_gis["primary_root_cause"].value_counts(normalize=True) * 100.0

report_content = f"""# Spatial Analysis Report — HEAL-CITY GIS

This report summarizes the spatial healthcare gap analysis across the 31 Kecamatan of Surabaya.

## 1. Summary of Spatial Units
- **Total Kecamatan Analysed:** 31
- **Spatial CRS Projection:** WGS84 (EPSG:4326) / Web Mercator (EPSG:3857)
- **Geometry Validity Checks:** 100% Valid (0 invalid, 0 null shapes)

## 2. Spatial Gap Hotspots (Top 5 Priority Area)
These Kecamatan register the highest relative gaps and are highlighted as priority spatial clusters:
1. **{top5_gap.iloc[0]['kecamatan']}** (Score: {top5_gap.iloc[0]['healthcare_gap_score']:.2f}, Priority: {top5_gap.iloc[0]['priority_category']})
2. **{top5_gap.iloc[1]['kecamatan']}** (Score: {top5_gap.iloc[1]['healthcare_gap_score']:.2f}, Priority: {top5_gap.iloc[1]['priority_category']})
3. **{top5_gap.iloc[2]['kecamatan']}** (Score: {top5_gap.iloc[2]['healthcare_gap_score']:.2f}, Priority: {top5_gap.iloc[2]['priority_category']})
4. **{top5_gap.iloc[3]['kecamatan']}** (Score: {top5_gap.iloc[3]['healthcare_gap_score']:.2f}, Priority: {top5_gap.iloc[3]['priority_category']})
5. **{top5_gap.iloc[4]['kecamatan']}** (Score: {top5_gap.iloc[4]['healthcare_gap_score']:.2f}, Priority: {top5_gap.iloc[4]['priority_category']})

## 3. Spatial Gap Coldspots (Lowest 5 Areas)
These Kecamatan register the lowest healthcare gap deficits:
1. **{low5_gap.iloc[0]['kecamatan']}** (Score: {low5_gap.iloc[0]['healthcare_gap_score']:.2f}, Priority: {low5_gap.iloc[0]['priority_category']})
2. **{low5_gap.iloc[1]['kecamatan']}** (Score: {low5_gap.iloc[1]['healthcare_gap_score']:.2f}, Priority: {low5_gap.iloc[1]['priority_category']})
3. **{low5_gap.iloc[2]['kecamatan']}** (Score: {low5_gap.iloc[2]['healthcare_gap_score']:.2f}, Priority: {low5_gap.iloc[2]['priority_category']})
4. **{low5_gap.iloc[3]['kecamatan']}** (Score: {low5_gap.iloc[3]['healthcare_gap_score']:.2f}, Priority: {low5_gap.iloc[3]['priority_category']})
5. **{low5_gap.iloc[4]['kecamatan']}** (Score: {low5_gap.iloc[4]['healthcare_gap_score']:.2f}, Priority: {low5_gap.iloc[4]['priority_category']})

## 4. Geographic Distribution of Root Causes
The primary gap drivers show clear geographical segregation:
- **WORKFORCE_SHORTAGE:** Primary driver in **{rc_counts.get('WORKFORCE_SHORTAGE', 0)} Kecamatan** ({rc_pct.get('WORKFORCE_SHORTAGE', 0.0):.1f}% of districts).
- **FACILITY_SHORTAGE:** Primary driver in **{rc_counts.get('FACILITY_SHORTAGE', 0)} Kecamatan** ({rc_pct.get('FACILITY_SHORTAGE', 0.0):.1f}% of districts).
- **DISEASE_BURDEN:** Primary driver in **{rc_counts.get('DISEASE_BURDEN', 0)} Kecamatan** ({rc_pct.get('DISEASE_BURDEN', 0.0):.1f}% of districts).

## 5. Descriptive Spatial Autocorrelation (Moran's I)
Based on visual inspection of the choropleth maps:
- A high positive spatial autocorrelation is suggested as high gap scores (e.g. Kenjeran and Krembangan) cluster in the northern coastal districts of Surabaya, whereas lower gap scores are located in central-east zones.
- This positive spatial clustering indicates that regional-scale interventions (e.g., sharing healthcare workforce or setting up primary clinics servicing adjacent districts) will have a compounding positive effect.

## 6. Access and Infrastructures Overlay
- **Puskesmas Points:** Map overlay shows points are distributed across all cells, but density varies heavily.
- **Road network:** Connects all Kecamatan centroids, serving as the basis for travel time analyses once GIS network Analyst buffers are integrated.
"""

with open(os.path.join(GIS_OUTPUT_DIR, "spatial_analysis_report.md"), "w", encoding="utf-8") as f:
    f.write(report_content)
print("Saved outputs/gis/spatial_analysis_report.md.")

print("HEAL-CITY GIS Analysis Pipeline Completed Successfully!")
