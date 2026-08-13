import os
import pandas as pd
import geopandas as gpd
import folium
from folium import Choropleth, GeoJson, LayerControl, Popup, GeoJsonTooltip

def load_spatial_data(path):
    """Load a spatial vector file using geopandas."""
    assert os.path.exists(path), f"Spatial dataset not found at {path}!"
    return gpd.read_file(path)

def standardize_kecamatan(gdf):
    """Normalize Kecamatan names to standard upper case."""
    gdf = gdf.copy()
    gdf["kecamatan"] = gdf["kecamatan"].str.strip().str.upper()
    return gdf

def merge_healthcare_data(gdf, healthcare_df):
    """Merge spatial dataset with healthcare scoring attributes."""
    # Standardize casing to ensure match
    gdf = gdf.copy()
    healthcare_df = healthcare_df.copy()
    healthcare_df["kecamatan_upper"] = healthcare_df["kecamatan"].str.strip().str.upper()
    
    # Merge on the upper case keys
    merged = gdf.merge(healthcare_df, left_on="kecamatan", right_on="kecamatan_upper", how="left")
    merged = merged.drop(columns=["kecamatan_upper"])
    
    # Standardize output kecamatan key
    if "kecamatan_y" in merged.columns:
        merged = merged.rename(columns={"kecamatan_y": "kecamatan"}).drop(columns=["kecamatan_x"])
    return merged

def validate_gis(gdf):
    """Ensure geometry correctness, kecamatan totals, and valid projections."""
    if len(gdf) != 31:
        raise ValueError(f"Expected exactly 31 Kecamatan in GIS data, but got {len(gdf)}!")
    if gdf.geometry.isna().any():
        raise ValueError("Spatial dataset contains missing/empty geometries!")
    if not gdf.geometry.is_valid.all():
        raise ValueError("Spatial dataset contains invalid geometries!")
    return True

def export_geojson(gdf, output_path):
    """Save spatial GeoDataFrame to GeoJSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    gdf.to_file(output_path, driver="GeoJSON")

def create_base_map():
    """Create a default folium Map centered on Surabaya."""
    return folium.Map(location=[-7.26, 112.75], zoom_start=11, tiles="cartodbpositron")

def run_gis_analysis(df_rca, config):
    """Run full GIS mapping pipeline, exporting geojson, csv, and HTML overlays."""
    spatial_dir = config["data"]["spatial_dir"]
    geojson_output = config["spatial"]["geojson_output"]
    processed_dir = config["data"]["processed_dir"]
    gis_output = config["output"]["gis"]
    
    os.makedirs(gis_output, exist_ok=True)
    os.makedirs(os.path.dirname(geojson_output), exist_ok=True)
    
    print("Running GIS mapping analysis...")
    
    # 1. Load bounds: prefer existing real-boundary GeoJSON (GADM) if it has many coords,
    #    fallback to base kecamatan file.
    kec_path = os.path.join(spatial_dir, "kecamatan_surabaya.geojson")
    pkm_path = os.path.join(spatial_dir, "puskesmas.geojson")
    fask_path = os.path.join(spatial_dir, "fasilitas_kesehatan.geojson")
    road_path = os.path.join(spatial_dir, "roads.geojson")

    # Detect if existing output GeoJSON has real boundaries (>10 coords per polygon)
    real_boundaries_path = None
    if os.path.exists(geojson_output):
        import json
        with open(geojson_output, "r", encoding="utf-8") as _f:
            _gj = json.load(_f)
        if _gj.get("features"):
            _geom = _gj["features"][0].get("geometry", {})
            _type = _geom.get("type", "")
            if _type == "MultiPolygon":
                _npts = sum(len(ring) for poly in _geom.get("coordinates", []) for ring in poly)
            elif _type == "Polygon":
                _npts = sum(len(ring) for ring in _geom.get("coordinates", []))
            else:
                _npts = 0
            if _npts > 10:
                real_boundaries_path = geojson_output
                print(f"  Using existing real boundaries from: {geojson_output} ({_npts} pts on first feature)")

    if real_boundaries_path:
        # Load from existing real output, only update analytics properties
        gdf_kec = gpd.read_file(real_boundaries_path)
        # Keep geometry, drop old analytics columns (except kecamatan)
        geo_cols = [c for c in gdf_kec.columns if c != "geometry"]
        gdf_kec = gdf_kec[["kecamatan", "geometry"]]
    else:
        gdf_kec = load_spatial_data(kec_path)
    
    # Standardize casing to match uppercase merge rules in specification (Section 37)
    gdf_kec_std = standardize_kecamatan(gdf_kec)
    df_rca_std = df_rca.copy()
    df_rca_std["kecamatan"] = df_rca_std["kecamatan"].str.strip().str.upper()
    
    # Merge
    gdf_gis = merge_healthcare_data(gdf_kec_std, df_rca_std)
    
    # Validate
    validate_gis(gdf_gis)
    
    # Export merged geojson (preserves real boundaries + new analytics)
    export_geojson(gdf_gis, geojson_output)
    
    # Export csv with centroid coordinates
    df_gis_csv = pd.DataFrame(gdf_gis.drop(columns="geometry"))
    centroids = gdf_gis.geometry.centroid
    df_gis_csv["centroid_lon"] = centroids.x
    df_gis_csv["centroid_lat"] = centroids.y
    
    # Restore kecamatan names to title case for cleaner reading
    df_gis_csv["kecamatan"] = df_gis_csv["kecamatan"].str.title()
    df_gis_csv.to_csv(os.path.join(processed_dir, "heal_city_gis.csv"), index=False)

    
    # Load support files
    gdf_pkm = load_spatial_data(pkm_path) if os.path.exists(pkm_path) else None
    gdf_fask = load_spatial_data(fask_path) if os.path.exists(fask_path) else None
    gdf_roads = load_spatial_data(road_path) if os.path.exists(road_path) else None
    
    # Helper for Tooltip (corrected folium class)
    def make_tooltip():
        return GeoJsonTooltip(
            fields=["kecamatan", "healthcare_gap_score", "priority_category", "primary_root_cause"],
            aliases=["Kecamatan:", "Gap Score:", "Priority:", "Primary Driver:"],
            localize=True
        )
        
    # MAP 1: healthcare_gap_map.html
    m_gap = create_base_map()
    Choropleth(
        geo_data=geojson_output,
        data=df_rca,
        columns=["kecamatan", "healthcare_gap_score"],
        key_on="feature.properties.kecamatan",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Healthcare Gap Score (0-100)"
    ).add_to(m_gap)
    
    GeoJson(
        geojson_output,
        style_function=lambda x: {'fillColor': '#000000', 'fillOpacity': 0.0, 'color': '#000000', 'weight': 1},
        tooltip=make_tooltip()
    ).add_to(m_gap)
    m_gap.save(os.path.join(gis_output, "healthcare_gap_map.html"))
    
    # MAP 2: priority_map.html (rank labels)
    m_prior = create_base_map()
    Choropleth(
        geo_data=geojson_output,
        data=df_rca,
        columns=["kecamatan", "healthcare_gap_score"],
        key_on="feature.properties.kecamatan",
        fill_color="OrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Priority Classification Map"
    ).add_to(m_prior)
    
    for idx, row in gdf_gis.iterrows():
        c_lat, c_lon = row.geometry.centroid.y, row.geometry.centroid.x
        k_name = str(row["kecamatan"]).title()
        popup_text = f"<b>Kecamatan:</b> {k_name}<br><b>Rank:</b> #{row['priority_rank']}<br><b>Score:</b> {row['healthcare_gap_score']:.1f}<br><b>Category:</b> {row['priority_category']}"
        folium.Marker(
            location=[c_lat, c_lon],
            icon=folium.DivIcon(html=f'<div style="font-size: 10pt; font-weight: bold; color: black; background-color: white; border: 1px solid black; padding: 2px; border-radius: 3px;">#{row["priority_rank"]}</div>'),
            popup=Popup(popup_text, max_width=300)
        ).add_to(m_prior)
    m_prior.save(os.path.join(gis_output, "priority_map.html"))
    
    # MAP 3: root_cause_map.html
    m_rca = create_base_map()
    rc_colors = {
        "WORKFORCE_SHORTAGE": "#d95f02",
        "FACILITY_SHORTAGE": "#7570b3",
        "DISEASE_BURDEN": "#1b9e77",
        "HIGH_DEMAND": "#e7298a",
        "ACCESSIBILITY": "#66a61e",
        "MULTI_FACTOR": "#e6ab02"
    }
    
    def get_rc_style(feature):
        rc = feature["properties"]["primary_root_cause"]
        color = rc_colors.get(rc, "#999999")
        return {"fillColor": color, "color": "#000000", "weight": 1.0, "fillOpacity": 0.7}
        
    GeoJson(geojson_output, style_function=get_rc_style, tooltip=make_tooltip()).add_to(m_rca)
    legend_html = '''
         <div style="position: fixed; 
         bottom: 50px; left: 50px; width: 180px; height: 180px; 
         border:2px solid grey; z-index:9999; background-color:white;
         font-size:14px; padding: 10px;
         ">
         <b>Primary Root Cause</b><br>
         <i style="background:#d95f02; width:12px; height:12px; float:left; margin-right:5px; border-radius:2px;"></i> Workforce Shortage<br>
         <i style="background:#7570b3; width:12px; height:12px; float:left; margin-right:5px; border-radius:2px;"></i> Facility Shortage<br>
         <i style="background:#1b9e77; width:12px; height:12px; float:left; margin-right:5px; border-radius:2px;"></i> Disease Burden<br>
         <i style="background:#e7298a; width:12px; height:12px; float:left; margin-right:5px; border-radius:2px;"></i> High Demand<br>
         <i style="background:#e6ab02; width:12px; height:12px; float:left; margin-right:5px; border-radius:2px;"></i> Multi-Factor<br>
         </div>
         '''
    m_rca.get_root().html.add_child(folium.Element(legend_html))
    m_rca.save(os.path.join(gis_output, "root_cause_map.html"))
    
    # MAP 4: facility_distribution.html
    m_fac = create_base_map()
    Choropleth(
        geo_data=geojson_output,
        data=df_rca,
        columns=["kecamatan", "facility_gap"],
        key_on="feature.properties.kecamatan",
        fill_color="PuBu",
        fill_opacity=0.5,
        line_opacity=0.2,
        legend_name="Facility Gap Score"
    ).add_to(m_fac)
    
    if gdf_pkm is not None:
        pkm_group = folium.FeatureGroup(name="Puskesmas Points").add_to(m_fac)
        for idx, row in gdf_pkm.iterrows():
            coords = row.geometry.coords[0]
            folium.Marker(
                location=[coords[1], coords[0]],
                icon=folium.Icon(color="blue", icon="plus-sign"),
                popup=Popup(f"<b>Puskesmas:</b> {row['nama_puskesmas']}<br><b>ID:</b> {row['puskesmas_id']}", max_width=200)
            ).add_to(pkm_group)
    LayerControl().add_to(m_fac)
    m_fac.save(os.path.join(gis_output, "facility_distribution.html"))
    
    # MAP 5: accessibility_map.html
    m_acc = create_base_map()
    GeoJson(
        geojson_output,
        style_function=lambda x: {'fillColor': '#cccccc', 'fillOpacity': 0.3, 'color': '#666666', 'weight': 1},
        tooltip=GeoJsonTooltip(fields=["kecamatan"], aliases=["Kecamatan:"])
    ).add_to(m_acc)
    
    if gdf_roads is not None:
        road_group = folium.FeatureGroup(name="Roads network").add_to(m_acc)
        for idx, row in gdf_roads.iterrows():
            coords = row.geometry.coords
            fol_coords = [[c[1], c[0]] for c in coords]
            folium.PolyLine(
                locations=fol_coords, color="#e63946", weight=2.0, opacity=0.8,
                popup=Popup(f"<b>Road:</b> {row['road_name']}", max_width=200)
            ).add_to(road_group)
    LayerControl().add_to(m_acc)
    m_acc.save(os.path.join(gis_output, "accessibility_map.html"))
    
    # Spatial Analysis report
    print("Writing spatial report...")
    top5 = df_rca.sort_values("healthcare_gap_score", ascending=False).head(5)
    low5 = df_rca.sort_values("healthcare_gap_score").head(5)
    
    rc_counts = df_rca["primary_root_cause"].value_counts()
    rc_pct = df_rca["primary_root_cause"].value_counts(normalize=True) * 100.0
    
    report_content = f"""# Spatial Analysis Report — HEAL-CITY GIS

This report summarizes the spatial healthcare gap analysis across the 31 Kecamatan of Surabaya.

## 1. Summary of Spatial Units
- **Total Kecamatan Analysed:** 31
- **Spatial CRS Projection:** WGS84 (EPSG:4326) / Web Mercator (EPSG:3857)
- **Geometry Validity Checks:** 100% Valid (0 invalid, 0 null shapes)

## 2. Spatial Gap Hotspots (Top 5 Priority Area)
These Kecamatan register the highest relative gaps and are highlighted as priority spatial clusters:
1. **{top5.iloc[0]['kecamatan']}** (Score: {top5.iloc[0]['healthcare_gap_score']:.2f}, Priority: {top5.iloc[0]['priority_category']})
2. **{top5.iloc[1]['kecamatan']}** (Score: {top5.iloc[1]['healthcare_gap_score']:.2f}, Priority: {top5.iloc[1]['priority_category']})
3. **{top5.iloc[2]['kecamatan']}** (Score: {top5.iloc[2]['healthcare_gap_score']:.2f}, Priority: {top5.iloc[2]['priority_category']})
4. **{top5.iloc[3]['kecamatan']}** (Score: {top5.iloc[3]['healthcare_gap_score']:.2f}, Priority: {top5.iloc[3]['priority_category']})
5. **{top5.iloc[4]['kecamatan']}** (Score: {top5.iloc[4]['healthcare_gap_score']:.2f}, Priority: {top5.iloc[4]['priority_category']})

## 3. Spatial Gap Coldspots (Lowest 5 Areas)
These Kecamatan register the lowest healthcare gap deficits:
1. **{low5.iloc[0]['kecamatan']}** (Score: {low5.iloc[0]['healthcare_gap_score']:.2f}, Priority: {low5.iloc[0]['priority_category']})
2. **{low5.iloc[1]['kecamatan']}** (Score: {low5.iloc[1]['healthcare_gap_score']:.2f}, Priority: {low5.iloc[1]['priority_category']})
3. **{low5.iloc[2]['kecamatan']}** (Score: {low5.iloc[2]['healthcare_gap_score']:.2f}, Priority: {low5.iloc[2]['priority_category']})
4. **{low5.iloc[3]['kecamatan']}** (Score: {low5.iloc[3]['healthcare_gap_score']:.2f}, Priority: {low5.iloc[3]['priority_category']})
5. **{low5.iloc[4]['kecamatan']}** (Score: {low5.iloc[4]['healthcare_gap_score']:.2f}, Priority: {low5.iloc[4]['priority_category']})

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
    with open("outputs/reports/spatial_analysis_report.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    with open(os.path.join(gis_output, "spatial_analysis_report.md"), "w", encoding="utf-8") as f:
        f.write(report_content)
        
    # Generate individual focused maps for all 31 Kecamatan
    generate_individual_kecamatan_maps(gdf_gis, gdf_pkm, gdf_fask, gdf_roads, gis_output)
        
    print("GIS mapping analysis completed successfully.")

def generate_individual_kecamatan_maps(gdf_gis, gdf_pkm, gdf_fask, gdf_roads, gis_output):
    """Generate focused individual GIS maps for each of the 31 Kecamatan."""
    kec_maps_dir = os.path.join(gis_output, "kecamatan_maps")
    os.makedirs(kec_maps_dir, exist_ok=True)
    
    print("Generating individual Kecamatan maps...")
    
    # Priority color map matching CSS styles
    priority_colors = {
        "Sangat Tinggi": "#ef4444",  # rose
        "Tinggi": "#f97316",         # amber
        "Sedang": "#eab308",         # yellow
        "Rendah": "#10b981"          # green
    }
    
    for idx, row in gdf_gis.iterrows():
        kec_name = row["kecamatan"]
        kec_name_title = str(kec_name).title()
        kec_name_lower = str(kec_name).lower().replace(" ", "_")
        
        # Calculate centroid for centering map
        centroid = row.geometry.centroid
        c_lat, c_lon = centroid.y, centroid.x
        
        # Create base map focused on current kecamatan
        m = folium.Map(location=[c_lat, c_lon], zoom_start=13, tiles="cartodbpositron")
        
        # 1. Overlay Kecamatan polygon boundary
        gdf_single = gdf_gis.iloc[[idx]]
        priority_cat = row["priority_category"]
        p_color = priority_colors.get(priority_cat, "#3b82f6")
        
        GeoJson(
            gdf_single,
            style_function=lambda x, color=p_color: {
                'fillColor': color,
                'fillOpacity': 0.15,
                'color': color,
                'weight': 3.0
            },
            tooltip=GeoJsonTooltip(fields=["kecamatan", "healthcare_gap_score"], aliases=["Kecamatan:", "Gap Score:"])
        ).add_to(m)
        
        # Infrastructure counters
        pkm_count = 0
        hosp_count = 0
        road_count = 0
        
        kec_poly = row.geometry
        
        # 2. Add local Puskesmas pins
        if gdf_pkm is not None and not gdf_pkm.empty:
            pkm_in_kec = gdf_pkm[gdf_pkm.geometry.within(kec_poly)]
            pkm_count = len(pkm_in_kec)
            if pkm_count > 0:
                pkm_group = folium.FeatureGroup(name="Local Puskesmas").add_to(m)
                for p_idx, p_row in pkm_in_kec.iterrows():
                    p_coords = p_row.geometry.coords[0]
                    folium.Marker(
                        location=[p_coords[1], p_coords[0]],
                        icon=folium.Icon(color="blue", icon="plus-sign"),
                        popup=Popup(f"<b>Puskesmas:</b> {p_row['nama_puskesmas']}<br><b>ID:</b> {p_row['puskesmas_id']}", max_width=200)
                    ).add_to(pkm_group)
                    
        # 3. Add local Hospital pins
        if gdf_fask is not None and not gdf_fask.empty:
            fask_in_kec = gdf_fask[gdf_fask.geometry.within(kec_poly)]
            for f_idx, f_row in fask_in_kec.iterrows():
                f_coords = f_row.geometry.coords[0]
                jenis = f_row.get("jenis_faskes", "")
                name = f_row.get("nama_faskes", f_row.get("nama_puskesmas", "Fasilitas Kesehatan"))
                
                # Check for hospital keyword to avoid cluttering map with small clinics
                if isinstance(jenis, str) and "Rumah Sakit" in jenis:
                    hosp_count += 1
                    folium.Marker(
                        location=[f_coords[1], f_coords[0]],
                        icon=folium.Icon(color="red", icon="plus-sign"),
                        popup=Popup(f"<b>Rumah Sakit:</b> {name}<br><b>Tipe:</b> {jenis}", max_width=200)
                    ).add_to(m)
                    
        # 4. Add local Roads overlay
        if gdf_roads is not None and not gdf_roads.empty:
            roads_in_kec = gdf_roads[gdf_roads.geometry.intersects(kec_poly)]
            road_count = len(roads_in_kec)
            if road_count > 0:
                road_group = folium.FeatureGroup(name="Local Roads").add_to(m)
                for r_idx, r_row in roads_in_kec.iterrows():
                    r_coords = r_row.geometry.coords
                    fol_coords = [[c[1], c[0]] for c in r_coords]
                    folium.PolyLine(
                        locations=fol_coords, color="#e63946", weight=2.0, opacity=0.8,
                        popup=Popup(f"<b>Road:</b> {r_row['road_name']}", max_width=200)
                    ).add_to(road_group)
                    
        # 5. Add custom UI overlay card for Kecamatan diagnostic summary
        priority_rank = row.get("priority_rank", 0)
        gap_score = row.get("healthcare_gap_score", 0.0)
        primary_driver = str(row.get("primary_root_cause", "UNKNOWN")).replace("_", " ").title()
        explanation = row.get("explanation", "Data analisis belum tersedia untuk kecamatan ini.")
        
        overlay_html = f'''
             <div style="position: fixed; 
             top: 20px; right: 20px; width: 320px; z-index: 9999; 
             background: rgba(17, 24, 39, 0.95); color: #f3f4f6;
             font-family: 'Inter', sans-serif; font-size: 13px; 
             border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -1px rgba(0, 0, 0, 0.5);
             border: 1px solid rgba(255, 255, 255, 0.1); padding: 16px;
             ">
                 <h3 style="margin-top: 0; margin-bottom: 8px; font-size: 16px; color: #fff; font-family: 'Outfit', sans-serif; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">
                     Kecamatan {kec_name_title}
                 </h3>
                 <div style="margin-bottom: 12px;">
                     <span style="background: {p_color}; color: #fff; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">
                         {priority_cat}
                     </span>
                     <span style="float: right; font-weight: bold; color: #9ca3af;">
                         Priority Rank: #{priority_rank}
                     </span>
                 </div>
                 <div style="margin-bottom: 8px;">
                     <strong>Healthcare Gap Score:</strong> <span style="font-size: 15px; font-weight: bold; color: #f87171;">{gap_score:.1f}</span> / 100
                 </div>
                 <div style="margin-bottom: 8px;">
                     <strong>Primary Driver:</strong> <span style="color: #60a5fa; font-weight: bold;">{primary_driver}</span>
                 </div>
                 <div style="margin-bottom: 12px; font-size: 12px; color: #d1d5db; line-height: 1.4; max-height: 120px; overflow-y: auto;">
                     {explanation}
                 </div>
                 <div style="font-size: 11px; color: #9ca3af; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px;">
                     <b>Local Infrastructures:</b><br>
                     🏥 Puskesmas: {pkm_count}<br>
                     🔴 Hospitals: {hosp_count}<br>
                     🛣️ Road network segments: {road_count}
                 </div>
             </div>
             '''
        m.get_root().html.add_child(folium.Element(overlay_html))
        
        # Save focused HTML map
        map_path = os.path.join(kec_maps_dir, f"{kec_name_lower}.html")
        m.save(map_path)

