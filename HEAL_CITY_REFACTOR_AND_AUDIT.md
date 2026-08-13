# HEAL-CITY — FINAL REFACTORING & CODE AUDIT PLAN

## GEMASTIK Smart City — Final Technical Validation

**Project:** HEAL-CITY  
**City:** Surabaya  
**Dataset Baseline:** 2024  
**Purpose:** Smart Decision Support System for Healthcare Gap Analysis  
**Audit Type:** Code Refactoring + Methodology Validation + Reproducibility Audit  
**Status:** FINAL REFACTORING REQUIRED

---

# 0. TUJUAN DOKUMEN

Dokumen ini digunakan sebagai pedoman untuk:

1. memperbaiki kode HEAL-CITY;
2. memastikan formula analisis benar;
3. memastikan seluruh dataset baseline konsisten tahun 2024;
4. menghilangkan double counting;
5. memastikan What-If Simulation benar-benar matematis;
6. memastikan Optimizer benar-benar melakukan optimasi;
7. memastikan GIS tidak hanya menjadi visualisasi;
8. memastikan seluruh hasil dapat direproduksi;
9. membuat sistem dapat dipertanggungjawabkan saat presentasi GEMASTIK;
10. melakukan audit ulang setelah seluruh refactoring selesai.

---

# 1. ATURAN UTAMA DATA

## 1.1 Tahun Dataset

Seluruh dataset statistik baseline HEAL-CITY menggunakan:

```text
TAHUN = 2024
```

Dataset yang termasuk:

* jumlah penduduk;
* kunjungan puskesmas;
* tenaga medis;
* perawat;
* bidan;
* fasilitas kesehatan;
* puskesmas;
* pustu;
* tempat tidur;
* data penyakit.

Jangan mencampurkan data statistik baseline dari tahun lain.

---

## 1.2 Data Spasial

Data spasial digunakan sebagai representasi geografis:

```text
Kecamatan
Puskesmas
Fasilitas kesehatan
Jaringan jalan
```

Pastikan metadata tahun sumber spasial terdokumentasi jika tersedia.

Jika tahun metadata spasial tidak diketahui:

```text
Jangan mengklaim bahwa seluruh data spasial berasal dari 2024.
```

Gunakan istilah:

```text
"Baseline statistical data: 2024"
```

dan jelaskan bahwa data spasial digunakan sebagai layer geografis.

---

# 2. PRIORITAS PERBAIKAN

Perbaikan harus dilakukan berdasarkan prioritas berikut.

## PRIORITY 1 — CRITICAL

* [ ] Perbaiki definisi dokter vs total nakes.
* [ ] Perbaiki optimizer agar benar-benar resource-constrained.
* [ ] Hilangkan kandidat yang melebihi budget.
* [ ] Perbaiki mapping resource dokter/perawat/bidan.
* [ ] Pastikan facility gap benar-benar menggunakan beds.
* [ ] Pastikan accessibility tidak dihitung secara palsu.
* [ ] Validasi seluruh bobot.

---

## PRIORITY 2 — HIGH

* [ ] Validasi Min-Max.
* [ ] Validasi semua rasio.
* [ ] Validasi 31 kecamatan.
* [ ] Validasi RCA.
* [ ] Validasi monotonicity simulation.
* [ ] Validasi score 0–100.
* [ ] Tambahkan automated tests.

---

## PRIORITY 3 — MEDIUM

* [ ] Rapikan konfigurasi.
* [ ] Hilangkan duplicate configuration.
* [ ] Tambahkan logging.
* [ ] Tambahkan metadata dataset.
* [ ] Tambahkan dokumentasi formula.

---

# 3. PERBAIKAN CONFIG.YAML

## 3.1 Masalah

Pastikan tidak ada konfigurasi yang duplikat.

Contoh konfigurasi yang sebaiknya tidak dibuat dua kali:

```yaml
gap_engine:
  demand_weight: 0.30
  workforce_weight: 0.30
  facility_weight: 0.20
  disease_weight: 0.20

weights:
  demand: 0.30
  workforce: 0.30
  facility: 0.20
  disease: 0.20
```

Gunakan satu sumber kebenaran.

---

## 3.2 Struktur yang Direkomendasikan

Gunakan:

```yaml
project:
  name: HEAL-CITY
  city: Surabaya
  baseline_year: 2024

data:
  raw_excel: dataset/data smart city.xlsx
  cleaned_dir: data/cleaned
  processed_dir: data/processed
  spatial_dir: data/spatial

spatial:
  district: data/spatial/kecamatan_surabaya.geojson
  puskesmas: data/spatial/puskesmas.geojson
  facilities: data/spatial/fasilitas_kesehatan.geojson
  roads: data/spatial/roads.geojson
  geojson_output: dataset/spatial/output/heal_city_gap.geojson

output:
  tables: outputs/tables
  figures: outputs/figures
  gis: outputs/gis
  reports: outputs/reports

model:
  random_state: 42

gap_engine:

  demand:
    population_weight: 0.50
    service_weight: 0.50

  workforce:
    doctors_weight: 0.40
    nurses_weight: 0.40
    midwives_weight: 0.20

  facility:
    facilities_weight: 0.30
    puskesmas_weight: 0.25
    pustu_weight: 0.15
    beds_weight: 0.30

  composite:
    demand_weight: 0.30
    workforce_weight: 0.30
    facility_weight: 0.20
    disease_weight: 0.20

root_cause:
  high_threshold: 0.80
  medium_threshold: 0.60

simulation:
  max_budget: 5000000000

optimizer:
  max_iterations: 10000
```

---

# 4. VALIDASI CONFIG

Buat fungsi:

```python
def validate_config(config):
    composite = config["gap_engine"]["composite"]

    total = (
        composite["demand_weight"]
        + composite["workforce_weight"]
        + composite["facility_weight"]
        + composite["disease_weight"]
    )

    assert abs(total - 1.0) < 1e-9

    workforce = config["gap_engine"]["workforce"]

    workforce_total = (
        workforce["doctors_weight"]
        + workforce["nurses_weight"]
        + workforce["midwives_weight"]
    )

    assert abs(workforce_total - 1.0) < 1e-9

    facility = config["gap_engine"]["facility"]

    facility_total = (
        facility["facilities_weight"]
        + facility["puskesmas_weight"]
        + facility["pustu_weight"]
        + facility["beds_weight"]
    )

    assert abs(facility_total - 1.0) < 1e-9
```

Jika assertion gagal:

```text
PIPELINE MUST STOP.
```

---

# 5. FEATURE ENGINEERING

## 5.1 Population

Pastikan:

```python
jumlah_penduduk > 0
```

Validasi:

```python
assert (df["jumlah_penduduk"] > 0).all()
```

---

# 6. DOKTER VS TOTAL NAKES

Ini merupakan bagian penting.

Jangan menggunakan:

```python
total_tenaga_kesehatan
```

sebagai:

```text
doctor count
```

Jika dataset memiliki:

```text
jumlah_tenaga_medis
jumlah_perawat
jumlah_bidan
```

maka:

```python
doctors_per_1000 = (
    jumlah_tenaga_medis / jumlah_penduduk
)
```

dan:

```python
nurses_per_1000 = (
    jumlah_perawat / jumlah_penduduk
)
```

```python
midwives_per_1000 = (
    jumlah_bidan / jumlah_penduduk
)
```

---

# 7. HINDARI DOUBLE COUNTING WORKFORCE

Jangan melakukan:

```text
nakes = dokter + perawat + bidan
```

kemudian menggunakan:

```text
nakes
dokter
perawat
bidan
```

secara bersamaan dalam satu score.

Gunakan:

```text
Doctor
Nurse
Midwife
```

sebagai tiga komponen workforce.

---

# 8. FORMULA WORKFORCE GAP

Gunakan:

```text
Doctor Gap
= 1 - normalized doctor ratio

Nurse Gap
= 1 - normalized nurse ratio

Midwife Gap
= 1 - normalized midwife ratio
```

Kemudian:

```text
Workforce Gap =
    doctor_weight * doctor_gap
  + nurse_weight * nurse_gap
  + midwife_weight * midwife_gap
```

Dengan:

```text
doctor_weight = 0.40
nurse_weight = 0.40
midwife_weight = 0.20
```

---

# 9. FACILITY GAP

Facility Gap harus menggunakan:

```text
Faskes
Puskesmas
Pustu
Beds
```

Formula:

```text
Facility Gap =
    facility_weight * facility_gap
  + puskesmas_weight * puskesmas_gap
  + pustu_weight * pustu_gap
  + beds_weight * beds_gap
```

Pastikan:

```text
0 <= facility_gap <= 1
```

---

# 10. BED RATIO

Gunakan:

```python
beds_per_1000 = (
    total_tempat_tidur / jumlah_penduduk
) * 1000
```

Pastikan multiplier konsisten.

Jangan menggunakan:

```python
total_tempat_tidur / jumlah_penduduk
```

jika nama fitur menyatakan:

```text
beds_per_1000
```

---

# 11. FASKES RATIO

Gunakan:

```python
faskes_per_100k = (
    total_faskes / jumlah_penduduk
) * 100000
```

Jangan menggunakan multiplier yang tidak sesuai dengan nama fitur.

---

# 12. PUSKESMAS RATIO

Gunakan:

```python
puskesmas_per_100k = (
    total_puskesmas / jumlah_penduduk
) * 100000
```

---

# 13. PUSTU RATIO

Gunakan:

```python
pustu_per_100k = (
    total_pustu / jumlah_penduduk
) * 100000
```

---

# 14. MIN-MAX NORMALIZATION

Gunakan:

```python
def minmax(series):
    min_value = series.min()
    max_value = series.max()

    if max_value == min_value:
        return pd.Series(
            0.0,
            index=series.index
        )

    return (
        (series - min_value)
        / (max_value - min_value)
    ).clip(0.0, 1.0)
```

Validasi:

```python
assert normalized.min() >= 0
assert normalized.max() <= 1
```

---

# 15. DEMAND SCORE

Demand Score hanya menggunakan:

```text
Population
Service Visits
```

Jangan memasukkan:

```text
Disease
```

Formula:

```text
Demand =
    0.50 * population_norm
  + 0.50 * visits_norm
```

---

# 16. DISEASE SCORE

Disease dihitung terpisah:

```python
disease_need_score = minmax(
    df["disease_per_1000"]
)
```

Kemudian masuk ke composite score.

---

# 17. COMPOSITE HEALTHCARE GAP

Formula utama:

```text
Healthcare Gap =
    0.30 * Demand
  + 0.30 * Workforce Gap
  + 0.20 * Facility Gap
  + 0.20 * Disease Need
```

Kemudian:

```python
healthcare_gap_score = (
    composite_score * 100
)
```

Validasi:

```python
assert (
    df["healthcare_gap_score"].between(0, 100)
).all()
```

---

# 18. PRIORITY CLASSIFICATION

Gunakan:

```python
def classify_priority(score):

    if score <= 20:
        return "Rendah"

    if score <= 40:
        return "Sedang"

    if score <= 60:
        return "Tinggi"

    if score <= 80:
        return "Sangat Tinggi"

    return "Kritis"
```

Boundary test:
```text
0, 20, 20.01, 40, 40.01, 60, 60.01, 80, 80.01, 100
```
Semua harus memiliki kategori.

---

# 19. ROOT CAUSE ANALYSIS

Root Cause harus menggunakan komponen yang benar-benar tersedia.

Komponen utama:

```text
WORKFORCE_SHORTAGE
FACILITY_SHORTAGE
DISEASE_BURDEN
HIGH_DEMAND
ACCESS_BARRIERS
MULTI_FACTOR
```

Jangan menggunakan:

```text
FACILITY_LIMITS
```

jika vocabulary final menggunakan:

```text
FACILITY_SHORTAGE
```

---

# 20. ROOT CAUSE CONSISTENCY

Buat constant:

```python
VALID_ROOT_CAUSES = {
    "WORKFORCE_SHORTAGE",
    "FACILITY_SHORTAGE",
    "DISEASE_BURDEN",
    "HIGH_DEMAND",
    "ACCESS_BARRIERS",
    "MULTI_FACTOR",
}
```

Kemudian:

```python
assert result in VALID_ROOT_CAUSES
```

---

# 21. CONFIDENCE SCORE

Confidence harus mempunyai dasar matematis.

Misalnya:

```text
margin =
highest_component - second_highest_component
```

Kemudian:

```text
HIGH
MEDIUM
LOW
```

berdasarkan threshold yang terdokumentasi.

Jangan menentukan confidence secara subjektif.

---

# 22. ACCESSIBILITY

Ini merupakan bagian penting.

Jika accessibility belum benar-benar masuk ke composite model:

```python
accessibility_gap = 0.0
```

boleh digunakan hanya sebagai placeholder internal.

Tetapi jangan mengklaim:

```text
Healthcare Gap mempertimbangkan aksesibilitas geografis
```

jika accessibility belum masuk ke formula.

---

# 23. GIS ACCESSIBILITY

Jika ingin accessibility benar-benar menjadi indikator:

Gunakan:
```text
centroid kecamatan -> fasilitas kesehatan -> jarak / travel distance -> nearest healthcare facility -> accessibility score
```

Lebih baik menggunakan:

```text
road network distance
```

daripada hanya:

```text
Euclidean distance
```

jika data jalan tersedia.

---

# 24. WHAT-IF SIMULATION

What-If harus:

1. mengubah resource;
2. menghitung ulang rasio;
3. menghitung ulang normalisasi;
4. menghitung ulang sub-score;
5. menghitung ulang composite score.

Urutan:
```text
BASELINE -> ADD RESOURCE -> RECALCULATE RATIOS -> RECALCULATE NORMALIZATION -> RECALCULATE GAP -> COMPARE BEFORE vs AFTER
```

---

# 25. SIMULATION — DOKTER

Jika:

```text
+1 doctor
```

maka hanya:

```text
doctor count
```

yang berubah.

Jangan otomatis:

```text
perawat += 0.6
bidan += 0.4
```

kecuali memang ada dasar kebijakan/model yang menyatakan demikian.

Jika intervensi adalah redistribusi tenaga:
```text
doctor -> doctor, nurse -> nurse, midwife -> midwife
```
harus dipisahkan.

---

# 26. SIMULATION — NURSE

Jika:

```text
+1 nurse
```

maka:

```python
jumlah_perawat += 1
```

dan:

```python
perawat_per_1000 = (
    jumlah_perawat / jumlah_penduduk * 1000
)
```

---

# 27. SIMULATION — MIDWIFE

Jika:

```text
+1 midwife
```

maka:

```python
jumlah_bidan += 1
```

---

# 28. SIMULATION — FACILITY

Jika:

```text
+1 facility
```

ubah:

```python
total_faskes += 1
```

Kemudian hitung ulang:

```text
faskes_per_100k
facility_gap
healthcare_gap
```

---

# 29. SIMULATION — BEDS

Jika:

```text
+1 bed
```

maka:

```python
total_tempat_tidur += 1
```

Kemudian:

```text
beds_per_1000
beds_gap
facility_gap
healthcare_gap
```

harus dihitung ulang.

---

# 30. SIMULATION MONOTONICITY

Test:
```text
baseline -> baseline + 1 doctor -> baseline + 2 doctors -> baseline + 3 doctors -> ...
```
Expected:
```text
Gap(+1) <= Gap(baseline)
Gap(+2) <= Gap(+1)
Gap(+3) <= Gap(+2)
```
Jika gap naik:

```text
FAIL
```

---

# 31. MASALAH PENTING INI DALAM NORMALISASI SIMULASI

Perhatikan bahwa Min-Max yang dihitung ulang setelah intervensi dapat mengubah skala seluruh kecamatan.

Contoh:
```text
Baseline: A = 0.2, B = 0.5, C = 0.8
```
Jika A mendapat resource besar:
```text
A = 0.9
```
maka nilai normalisasi B dan C juga dapat berubah.

Karena itu tentukan secara eksplisit apakah HEAL-CITY menggunakan:

```text
Baseline normalization
```

atau:

```text
Dynamic normalization
```

Untuk What-If yang stabil dan mudah dijelaskan, rekomendasi:

```text
Gunakan baseline normalization.
```

Artinya parameter Min-Max ditentukan dari baseline 2024 dan tidak berubah ketika simulasi dilakukan.

---

# 32. SIMULATION RECOMMENDATION

Implementasikan:

```python
normalization_reference
```

yang berasal dari baseline.

Contoh:
```text
min_value, max_value
```
disimpan dari dataset baseline.

Simulation hanya mengubah:

```text
resource
```

bukan:

```text
normalization scale
```

---

# 33. OPTIMIZER — MASALAH UTAMA

Optimizer saat ini harus benar-benar memenuhi:

```text
budget constraint
resource constraint
intervention constraint
```

Tidak boleh membuat kandidat:

```text
cost > budget
```

kemudian tetap menjalankan simulation.

---

# 34. FEASIBILITY

Gunakan:

```python
if cost > budget:
    return "NOT_FEASIBLE"
```

Kemudian:

```python
for resource, required in resources_used.items():

    available = resources_available.get(resource, 0)

    if required > available:
        return "NOT_FEASIBLE"
```

Jangan gunakan default `999` karena dapat menyembunyikan resource constraint. Gunakan `0` atau raise error jika resource tidak diketahui.

---

# 35. OPTIMIZER RESOURCE MAPPING

Jangan gunakan:

```python
used_res["nakes"] = qty
```

jika sistem sebenarnya memiliki:

```text
doctors
nurses
midwives
```

Gunakan:

```python
used_res = {
    "doctors": ...,
    "nurses": ...,
    "midwives": ...,
    "beds": ...
}
```

---

# 36. INTERVENTION DATABASE

Gunakan database intervensi:

```text
interventions.csv
```

dengan struktur:
```text
intervention_id, intervention_name, target_component, resource_type, unit, cost_per_unit, max_units, impact_type
```

Contoh:
```csv
I01,Redistribute Doctors,workforce,doctors,person,50000000,20,recalculate
I02,Redistribute Nurses,workforce,nurses,person,40000000,30,recalculate
I03,Redistribute Midwives,workforce,midwives,person,40000000,20,recalculate
I04,Add Beds,facility,beds,bed,250000000,100,recalculate
I05,Add Facility,facility,facilities,facility,1000000000,5,recalculate
```

---

# 37. JANGAN GUNAKAN IMPACT PER UNIT SEBAGAI HASIL FINAL

Jika ada:

```text
impact_per_unit
```

jangan langsung:

```python
improvement = qty * impact_per_unit
```

sebagai healthcare gap final.

Impact harus berasal dari:

```text
simulation engine
```

yaitu:
```text
before gap vs after gap
```

---

# 38. OPTIMIZER SEBAIKNYA MEMAKAI SIMULASI

Untuk setiap kandidat:
```text
Candidate -> Check budget -> Check resources -> Apply intervention -> Simulation -> Calculate gap reduction -> Calculate cost efficiency -> Calculate alignment -> Rank
```

---

# 39. OPTIMIZER SCORE

Gunakan score yang dapat dijelaskan.

Contoh:
```text
Impact Score + Alignment Score + Feasibility Score + Cost Efficiency
```
atau gunakan formula sederhana:

```text
optimizer_score = gap_reduction / cost
```

Kemudian tambahkan:

```text
alignment multiplier
```

jika diperlukan.

Yang paling penting:

```text
Score harus terdokumentasi.
```

---

# 40. GREEDY VS COMBINATORIAL OPTIMIZATION

Jika optimizer hanya:

```text
menguji satu paket per intervensi
```

jangan menyebutnya:

```text
AI Optimizer
```

secara berlebihan.

Lebih tepat:

```text
Resource-Constrained Intervention Optimizer
```

Jika ingin benar-benar optimasi:

gunakan pencarian kombinasi:
```text
doctor, nurse, midwife, beds, facility
```
dengan batas:
```text
budget, resources, maximum intervention
```
Contoh:
```text
Doctor 0..10, Nurse 0..20, Midwife 0..10, Beds 0..100, Facility 0..5
```
Kemudian cari kombinasi terbaik.

---

# 41. OPTIMIZER OBJECTIVE

Tujuan utama:

```text
Minimize Healthcare Gap Score
```

subject to:

```text
Total Cost <= Budget
```

dan:

```text
Doctors Used <= Available Doctors
Nurses Used <= Available Nurses
Midwives Used <= Available Midwives
Beds Used <= Available Beds
Facilities Used <= Available Facilities
```

---

# 42. OUTPUT OPTIMIZER

Setiap rekomendasi harus mempunyai:

```text
intervention_id
intervention_name
quantity
cost
resources_used
before_gap
after_gap
gap_reduction
gap_reduction_percent
feasibility
alignment
optimizer_score
```

---

# 43. DATA QUALITY STATUS

Jangan selalu:

```python
df["data_quality_status"] = "COMPLETE"
```

Jika sistem belum benar-benar memeriksa kualitas data.

Buat:

```python
def evaluate_data_quality(row):
    checks = [
        row["jumlah_penduduk"] > 0,
        pd.notna(row["nakes_per_1000"]),
        pd.notna(row["perawat_per_1000"]),
        pd.notna(row["bidan_per_1000"]),
        pd.notna(row["faskes_per_100k"])
    ]

    return (
        "COMPLETE"
        if all(checks)
        else "INCOMPLETE"
    )
```

---

# 44. VALIDASI 31 KECAMATAN

Setelah preprocessing:

```python
EXPECTED_DISTRICTS = 31

assert df["kecamatan"].nunique() == EXPECTED_DISTRICTS
```

Selain jumlah:

```text
Pastikan nama kecamatan valid.
```

Gunakan daftar resmi kecamatan Surabaya sebagai reference list.

---

# 45. MERGE VALIDATION

Setiap merge harus diperiksa.

Gunakan:

```python
before = set(df["kecamatan"])

merged = df.merge(
    other,
    on="kecamatan",
    how="left",
    validate="one_to_one"
)
```

Kemudian:

```python
assert len(merged) == len(df)
```

dan:

```python
assert merged["kecamatan"].notna().all()
```

---

# 46. GIS VALIDATION

Pastikan:

```text
31 polygon
```

dan:

```python
assert geo_df["kecamatan"].nunique() == 31
```

Setelah merge:

```python
assert len(geo_df) == 31
```

---

# 47. FACILITY COORDINATE VALIDATION

Pastikan:

```text
latitude valid
longitude valid
```

Contoh:

```python
assert facilities["latitude"].between(
    -8.0, -7.0
).all()
```

```python
assert facilities["longitude"].between(
    112.0, 113.5
).all()
```

Gunakan range geografis yang sesuai dataset aktual dan dokumentasikan.

---

# 48. NO HARDCODE AUDIT

Cari:
```text
31, 0.30, 0.20, 0.40, 0.50, 2024
```
di source code.

Nilai konfigurasi harus berasal dari:

```text
config.yaml
```

kecuali nilai tersebut merupakan invariant struktural.

---

# 49. RANDOM STATE

Jika tidak ada algoritma stochastic:

```text
random_state tidak diperlukan untuk perhitungan deterministik.
```

Jika digunakan:

```python
random_state = 42
```

harus berasal dari:

```yaml
model:
  random_state: 42
```

---

# 50. REPRODUCIBILITY TEST

Hapus:
```text
data/processed/
outputs/
logs/
```
Jalankan:
```bash
python main.py
```
Expected:
```text
Pipeline SUCCESS
```
Kemudian jalankan kembali:
```bash
python main.py
```
Output harus identik.

---

# 51. AUTOMATED TESTING

Buat:
```text
tests/
```
Struktur:
```text
tests/
├── test_preprocessing.py
├── test_features.py
├── test_gap_engine.py
├── test_root_cause.py
├── test_simulation.py
├── test_optimizer.py
└── test_gis.py
```

---

# 52. TEST GAP SCORE

Test:

```python
def test_gap_score_range():

    result = calculate_healthcare_gap(
        df,
        config
    )

    assert result["healthcare_gap_score"].between(
        0,
        100
    ).all()
```

---

# 53. TEST WEIGHTS

```python
def test_weights():

    total = (
        demand
        + workforce
        + facility
        + disease
    )

    assert abs(total - 1.0) < 1e-9
```

---

# 54. TEST 31 DISTRICTS

```python
def test_district_count():

    assert df["kecamatan"].nunique() == 31
```

---

# 55. TEST NORMALIZATION

```python
def test_minmax():

    normalized = minmax(series)

    assert normalized.min() >= 0
    assert normalized.max() <= 1
```

---

# 56. TEST SIMULATION

```python
def test_doctor_intervention():

    baseline = simulate_intervention(
        df,
        district,
        {"doctors": 0},
        config
    )

    intervention = simulate_intervention(
        df,
        district,
        {"doctors": 1},
        config
    )

    assert (
        intervention["after_gap"]
        <=
        baseline["after_gap"]
    )
```

---

# 57. TEST OPTIMIZER

Pastikan:

```python
for candidate in candidates:

    assert candidate["cost"] <= budget

    for resource, used in candidate["resources_used"].items():

        assert used <= resources_available[resource]
```

---

# 58. TEST ROOT CAUSE

```python
VALID_ROOT_CAUSES = {
    "WORKFORCE_SHORTAGE",
    "FACILITY_SHORTAGE",
    "DISEASE_BURDEN",
    "HIGH_DEMAND",
    "ACCESS_BARRIERS",
    "MULTI_FACTOR",
}
```

Kemudian:

```python
assert result in VALID_ROOT_CAUSES
```

---

# 59. LOGGING

Pipeline harus menghasilkan:
```text
logs/
├── heal_city.log
├── healthcare_gap_weights.csv
├── data_quality_report.csv
└── run_manifest.json
```

---

# 60. RUN MANIFEST

`run_manifest.json` minimal harus mencatat:

```json
{
  "project": "HEAL-CITY",
  "city": "Surabaya",
  "baseline_year": 2024,
  "district_count": 31,
  "pipeline_status": "SUCCESS",
  "config_version": "final",
  "random_state": 42
}
```

---

# 61. DATA QUALITY REPORT

Buat:
```text
data_quality_report.csv
```
dengan:
```text
dataset, rows, columns, missing_values, duplicate_rows, year, status
```

---

# 62. DASHBOARD VALIDATION

Dashboard harus menampilkan:

## Overview
```text
31 Kecamatan
Average Gap Score
Highest Priority District
Lowest Priority District
```

---

## Map

Harus tersedia:
```text
Healthcare Gap
Priority
Root Cause
Healthcare Facilities
```

---

## Simulation

Input:
```text
Doctors, Nurses, Midwives, Beds, Facilities
```
Output:
```text
Before Gap, After Gap, Gap Reduction, Gap Reduction %
```

---

# 63. OPTIMIZER DASHBOARD

Input:
```text
Kecamatan, Budget, Available Doctors, Available Nurses, Available Midwives, Available Beds, Available Facilities
```
Output:
```text
Recommended Intervention, Cost, Resources Used, Before Gap, After Gap, Gap Reduction, Feasibility
```

---

# 64. DASHBOARD — JANGAN MENAMPILKAN KLAIM PALSU

Jangan menampilkan:

```text
AI predicts future healthcare demand
```

jika model tidak melakukan forecasting.

Gunakan:

```text
AI-assisted/resource-constrained intervention recommendation
```

jika memang optimizer menggunakan mekanisme tersebut.

---

# 65. DOKUMENTASI FORMULA

Buat:
```text
docs/methodology.md
```
Berisi:
```text
1. Dataset
2. Preprocessing
3. Feature Engineering
4. Normalization
5. Demand Score
6. Workforce Gap
7. Facility Gap
8. Disease Need
9. Composite Gap
10. Root Cause
11. Simulation
12. Optimization
13. GIS
```

---

# 66. FINAL PIPELINE

Pipeline final harus:
```text
RAW DATA -> VALIDATION -> PREPROCESSING -> MASTER DATA -> FEATURE ENGINEERING -> BASELINE NORMALIZATION -> GAP ENGINE -> ROOT CAUSE ANALYSIS -> GIS INTEGRATION -> SIMULATION ENGINE -> RESOURCE OPTIMIZER -> OUTPUT -> DASHBOARD
```

---

# 67. FINAL OUTPUT FILES

Pipeline minimal menghasilkan:
```text
data/processed/
├── master_heal_city.csv
├── heal_city_features.csv
├── healthcare_gap_scores.csv
├── root_cause_analysis.csv
├── heal_city_gis.csv
└── interventions.csv
```
dan:
```text
outputs/
├── gis/
├── tables/
├── figures/
└── reports/
```
serta:
```text
logs/
├── heal_city.log
├── healthcare_gap_weights.csv
├── data_quality_report.csv
└── run_manifest.json
```

---

# 68. FINAL AUDIT CHECKLIST

## Dataset
* [ ] Dataset baseline seluruhnya 2024
* [ ] 31 kecamatan
* [ ] Tidak ada duplicate
* [ ] Tidak ada missing critical value
* [ ] Metadata dataset tersedia

## Preprocessing
* [ ] Column standardized
* [ ] Kecamatan standardized
* [ ] Merge validated
* [ ] No silent row loss

## Feature Engineering
* [ ] Doctor ratio benar
* [ ] Nurse ratio benar
* [ ] Midwife ratio benar
* [ ] Facility ratio benar
* [ ] Puskesmas ratio benar
* [ ] Pustu ratio benar
* [ ] Bed ratio benar

## Normalization
* [ ] Semua normalized features 0–1
* [ ] Baseline normalization terdokumentasi
* [ ] Simulation menggunakan reference normalization

## Gap Engine
* [ ] Demand = population + visits
* [ ] Disease terpisah
* [ ] Workforce = doctor + nurse + midwife
* [ ] Facility = facility + puskesmas + pustu + beds
* [ ] Composite weights = 1
* [ ] Gap = 0–100

## Root Cause
* [ ] Vocabulary konsisten
* [ ] Primary driver terukur
* [ ] Confidence terukur

## Simulation
* [ ] Doctor intervention benar
* [ ] Nurse intervention benar
* [ ] Midwife intervention benar
* [ ] Bed intervention benar
* [ ] Facility intervention benar
* [ ] No arbitrary offset
* [ ] Monotonicity test PASS

## Optimizer
* [ ] Budget constraint
* [ ] Doctor constraint
* [ ] Nurse constraint
* [ ] Midwife constraint
* [ ] Bed constraint
* [ ] Facility constraint
* [ ] Infeasible candidate dibuang
* [ ] Candidate ranking reproducible
* [ ] Gap reduction berasal dari simulation

## GIS
* [ ] 31 polygon
* [ ] Join berdasarkan key
* [ ] Facility marker valid
* [ ] Coordinate validation
* [ ] Accessibility methodology documented

## Reproducibility
* [ ] Output lama dapat dihapus
* [ ] Pipeline dapat dijalankan ulang
* [ ] Output konsisten
* [ ] Manifest tersedia
* [ ] Config terpusat

## Testing
* [ ] Unit tests
* [ ] Integration tests
* [ ] Simulation tests
* [ ] Optimizer tests
* [ ] GIS tests

---

# 69. FINAL ACCEPTANCE CRITERIA

HEAL-CITY hanya boleh diberi status:

```text
COMPETITION READY
```

jika seluruh kondisi berikut terpenuhi:

```text
[PASS] Dataset validation
[PASS] 31 district validation
[PASS] Feature validation
[PASS] Normalization validation
[PASS] Gap engine validation
[PASS] Root cause validation
[PASS] Simulation validation
[PASS] Optimizer validation
[PASS] GIS validation
[PASS] Dashboard validation
[PASS] Reproducibility validation
[PASS] Automated testing
```

Jika salah satu bagian:

```text
CRITICAL FAIL
```

maka status:

```text
NOT READY
```

---

# 70. TARGET AKHIR

Target akhir HEAL-CITY:
```text
Data -> Evidence -> Gap Detection -> Root Cause -> What-If -> Optimization -> Actionable Recommendation
```

HEAL-CITY bukan hanya:
```text
"menampilkan peta kesehatan"
```
tetapi:
```text
"mengidentifikasi kesenjangan,
menjelaskan penyebabnya,
mensimulasikan intervensi,
dan memilih rekomendasi yang feasible
berdasarkan keterbatasan sumber daya."
```

---

# 71. PERINTAH AUDIT FINAL

Setelah seluruh perbaikan selesai, jalankan:

```bash
python main.py
```

Kemudian:

```bash
pytest -q
```

Kemudian hapus:

```text
data/processed/
outputs/
logs/
```

dan jalankan kembali:

```bash
python main.py
```

Kemudian:

```bash
pytest -q
```

Expected:

```text
PIPELINE: PASS
TESTS: PASS
REPRODUCIBILITY: PASS
DATA VALIDATION: PASS
OPTIMIZER VALIDATION: PASS
SIMULATION VALIDATION: PASS
GIS VALIDATION: PASS
```

Jika seluruhnya PASS:

```text
HEAL-CITY = READY FOR FINAL GEMASTIK VALIDATION
```

---

# 72. CATATAN PENTING UNTUK GEMASTIK

Jangan mengejar:

```text
100/100
```

hanya dengan checklist.

Yang harus dikejar adalah:

```text
CORRECT + EXPLAINABLE + REPRODUCIBLE + DEFENSIBLE
```

Juri kemungkinan besar akan bertanya:

1. "Mengapa kecamatan ini menjadi prioritas?"
2. "Dari mana skor 73.2 berasal?"
3. "Mengapa root cause-nya workforce?"
4. "Jika ditambah 5 dokter, apa yang berubah?"
5. "Mengapa rekomendasi ini dipilih?"
6. "Apakah rekomendasi tersebut masih feasible jika anggaran terbatas?"
7. "Data yang digunakan tahun berapa?"
8. "Apakah data penyakit dihitung dua kali?"
9. "Bagaimana Anda menentukan bobot?"
10. "Apakah hasil dapat direproduksi?"
11. "Apa bedanya What-If dan Optimizer?"
12. "Apakah sistem benar-benar menggunakan AI atau hanya rule-based?"

Seluruh jawaban terhadap pertanyaan tersebut harus dapat ditemukan
secara konsisten di:

```text
CODE + CONFIG + DATA + DOCUMENTATION
```

---

# FINAL STATUS

Current status:

```text
REFACTORING REQUIRED
```

Target status:

```text
COMPETITION READY
```

Jangan mengubah status menjadi `COMPETITION READY`
sebelum automated audit selesai.
