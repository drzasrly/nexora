# Spatial Analysis Report — HEAL-CITY GIS

This report summarizes the spatial healthcare gap analysis across the 31 Kecamatan of Surabaya.

## 1. Summary of Spatial Units
- **Total Kecamatan Analysed:** 31
- **Spatial CRS Projection:** WGS84 (EPSG:4326) / Web Mercator (EPSG:3857)
- **Geometry Validity Checks:** 100% Valid (0 invalid, 0 null shapes)

## 2. Spatial Gap Hotspots (Top 5 Priority Area)
These Kecamatan register the highest relative gaps and are highlighted as priority spatial clusters:
1. **Kenjeran** (Score: 82.65, Priority: Kritis)
2. **Krembangan** (Score: 74.78, Priority: Sangat Tinggi)
3. **Semampir** (Score: 73.86, Priority: Sangat Tinggi)
4. **Sawahan** (Score: 72.99, Priority: Sangat Tinggi)
5. **Tandes** (Score: 72.24, Priority: Sangat Tinggi)

## 3. Spatial Gap Coldspots (Lowest 5 Areas)
These Kecamatan register the lowest healthcare gap deficits:
1. **Mulyorejo** (Score: 33.56, Priority: Sedang)
2. **Gubeng** (Score: 37.97, Priority: Sedang)
3. **Pabean Cantian** (Score: 40.41, Priority: Tinggi)
4. **Dukuh Pakis** (Score: 44.19, Priority: Tinggi)
5. **Tenggilis Mejoyo** (Score: 44.72, Priority: Tinggi)

## 4. Geographic Distribution of Root Causes
The primary gap drivers show clear geographical segregation:
- **WORKFORCE_SHORTAGE:** Primary driver in **16 Kecamatan** (51.6% of districts).
- **FACILITY_SHORTAGE:** Primary driver in **12 Kecamatan** (38.7% of districts).
- **DISEASE_BURDEN:** Primary driver in **3 Kecamatan** (9.7% of districts).

## 5. Descriptive Spatial Autocorrelation (Moran's I)
Based on visual inspection of the choropleth maps:
- A high positive spatial autocorrelation is suggested as high gap scores (e.g. Kenjeran and Krembangan) cluster in the northern coastal districts of Surabaya, whereas lower gap scores are located in central-east zones.
- This positive spatial clustering indicates that regional-scale interventions (e.g., sharing healthcare workforce or setting up primary clinics servicing adjacent districts) will have a compounding positive effect.

## 6. Access and Infrastructures Overlay
- **Puskesmas Points:** Map overlay shows points are distributed across all cells, but density varies heavily.
- **Road network:** Connects all Kecamatan centroids, serving as the basis for travel time analyses once GIS network Analyst buffers are integrated.
