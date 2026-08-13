# Spatial Analysis Report — HEAL-CITY GIS

This report summarizes the spatial healthcare gap analysis across the 31 Kecamatan of Surabaya.

## 1. Summary of Spatial Units
- **Total Kecamatan Analysed:** 31
- **Spatial CRS Projection:** WGS84 (EPSG:4326) / Web Mercator (EPSG:3857)
- **Geometry Validity Checks:** 100% Valid (0 invalid, 0 null shapes)

## 2. Spatial Gap Hotspots (Top 5 Priority Area)
These Kecamatan register the highest relative gaps and are highlighted as priority spatial clusters:
1. **Kenjeran** (Score: 81.15, Priority: Kritis)
2. **Krembangan** (Score: 73.28, Priority: Sangat Tinggi)
3. **Semampir** (Score: 72.36, Priority: Sangat Tinggi)
4. **Sawahan** (Score: 71.49, Priority: Sangat Tinggi)
5. **Tandes** (Score: 70.74, Priority: Sangat Tinggi)

## 3. Spatial Gap Coldspots (Lowest 5 Areas)
These Kecamatan register the lowest healthcare gap deficits:
1. **Mulyorejo** (Score: 32.06, Priority: Sedang)
2. **Gubeng** (Score: 36.47, Priority: Sedang)
3. **Pabean Cantian** (Score: 38.91, Priority: Sedang)
4. **Dukuh Pakis** (Score: 42.69, Priority: Tinggi)
5. **Tenggilis Mejoyo** (Score: 43.22, Priority: Tinggi)

## 4. Geographic Distribution of Root Causes
The primary gap drivers show clear geographical segregation:
- **WORKFORCE_SHORTAGE:** Primary driver in **19 Kecamatan** (61.3% of districts).
- **FACILITY_SHORTAGE:** Primary driver in **8 Kecamatan** (25.8% of districts).
- **DISEASE_BURDEN:** Primary driver in **3 Kecamatan** (9.7% of districts).

## 5. Descriptive Spatial Autocorrelation (Moran's I)
Based on visual inspection of the choropleth maps:
- A high positive spatial autocorrelation is suggested as high gap scores (e.g. Kenjeran and Krembangan) cluster in the northern coastal districts of Surabaya, whereas lower gap scores are located in central-east zones.
- This positive spatial clustering indicates that regional-scale interventions (e.g., sharing healthcare workforce or setting up primary clinics servicing adjacent districts) will have a compounding positive effect.

## 6. Access and Infrastructures Overlay
- **Puskesmas Points:** Map overlay shows points are distributed across all cells, but density varies heavily.
- **Road network:** Connects all Kecamatan centroids, serving as the basis for travel time analyses once GIS network Analyst buffers are integrated.
