// ============================================================
// NEXORA — HEAL-CITY Dashboard App.js
// Full SPA with: GIS Map, Priority Map Toggle, Overview,
// Analytics, What-if Simulation, AI Optimizer + Resource Engine
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    // ============================================================
    // GLOBAL STATE
    // ============================================================
    let mainMap, overviewMap, simMapBefore, simMapAfter;
    let mainGeojsonLayer, overviewGeojsonLayer;
    let simBeforeLayer, simAfterLayer;
    let hospitalLayer, puskesmasLayer, clinicLayer;
    let rawKecamatanData = null;
    let rawFacilityData = null;
    let activeKecamatanLayer = null;
    let currentMapMode = 'gap'; // 'gap' or 'priority'
    let currentSelectedKec = null;
    let charts = {};
    let mapsInitialized = { main: false, overview: false, simBefore: false, simAfter: false };

    const SURABAYA_CENTER = [-7.265, 112.74];
    const DEFAULT_ZOOM = 11.5;

    const COLORS = {
        rose: '#ef4444', amber: '#f97316', yellow: '#eab308',
        green: '#10b981', blue: '#3b82f6', indigo: '#6366f1',
        purple: '#a855f7', slate: '#9ca3af'
    };

    const PRIORITY_MAP_COLORS = {
        'Sangat Tinggi': '#dc2626',
        'Tinggi':        '#ea580c',
        'Sedang':        '#ca8a04',
        'Rendah':        '#16a34a'
    };

    const ROOT_CAUSE_COLORS = {
        'WORKFORCE_SHORTAGE': COLORS.rose,
        'FACILITY_SHORTAGE':  COLORS.blue,
        'DISEASE_BURDEN':     COLORS.purple,
        'HIGH_DEMAND':        COLORS.amber,
        'ACCESS_BARRIERS':    COLORS.green,
        'MULTI_FACTOR':       COLORS.yellow
    };

    // Sensitivity config for what-if simulation
    const SENSITIVITY = {
        doctor:   0.09,  // per doctor added, per population 1000
        nurse:    0.06,
        midwife:  0.04,
        facility: 0.12,
        beds:     0.02
    };

    // Cost config (Rp Juta per unit)
    const COST = {
        doctor:   150,  // Rp 150 juta/year per doctor
        nurse:    80,
        midwife:  70,
        facility: 2500, // Rp 2.5 miliar per new facility
        beds:     10
    };

    // ============================================================
    // TAB NAVIGATION
    // ============================================================
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            switchPage(btn.dataset.page);
        });
    });

    window.switchPage = function(pageName) {
        // Hide all pages
        document.querySelectorAll('.page-content').forEach(p => p.classList.add('hidden'));
        // Remove active from all tabs
        tabs.forEach(t => t.classList.remove('active'));

        // Show target page
        const page = document.getElementById(`page-${pageName}`);
        const tab = document.getElementById(`tab-${pageName}`);
        if (page) page.classList.remove('hidden');
        if (tab) tab.classList.add('active');

        // Lazy-init maps when their tab is first shown
        setTimeout(() => {
            if (pageName === 'map' && !mapsInitialized.main) {
                initMainMap();
                mapsInitialized.main = true;
            }
            if (pageName === 'overview' && !mapsInitialized.overview) {
                initOverviewMap();
                mapsInitialized.overview = true;
            }
            if (pageName === 'analytics') {
                renderAnalyticsPage();
            }

            // Invalidate size to handle layout changes dynamically
            if (pageName === 'map' && mainMap) {
                mainMap.invalidateSize();
            }
            if (pageName === 'overview' && overviewMap) {
                overviewMap.invalidateSize();
            }
            if (pageName === 'simulation') {
                if (simMapBefore) simMapBefore.invalidateSize();
                if (simMapAfter) simMapAfter.invalidateSize();
            }
        }, 50);
    };

    // ============================================================
    // DATA LOADING
    // ============================================================
    async function loadAllData() {
        try {
            const [kecRes, facRes] = await Promise.all([
                fetch('/dataset/spatial/output/heal_city_gap.geojson'),
                fetch('/data/spatial/fasilitas_kesehatan.geojson')
            ]);

            rawKecamatanData = await kecRes.json();
            rawFacilityData  = await facRes.json();

            // Populate selects
            populateKecamatanSelects();

            // Init overview (default page)
            initOverviewMap();
            mapsInitialized.overview = true;
            populateOverviewStats();
            populateOverviewPriorityTable();

        } catch (err) {
            console.error("Error loading data:", err);
        }
    }

    function populateKecamatanSelects() {
        if (!rawKecamatanData) return;
        const sorted = [...rawKecamatanData.features]
            .sort((a, b) => a.properties.kecamatan.localeCompare(b.properties.kecamatan));

        const selects = ['sim-kecamatan', 'opt-kecamatan'];
        selects.forEach(id => {
            const sel = document.getElementById(id);
            if (!sel) return;
            sel.innerHTML = '<option value="">— Choose District —</option>';
            sorted.forEach(f => {
                const opt = document.createElement('option');
                opt.value = f.properties.kecamatan;
                opt.textContent = titleCase(f.properties.kecamatan);
                sel.appendChild(opt);
            });
        });
    }

    // ============================================================
    // OVERVIEW PAGE
    // ============================================================
    function populateOverviewStats() {
        if (!rawKecamatanData) return;
        const features = rawKecamatanData.features;

        // Count critical (Sangat Tinggi)
        const critical = features.filter(f => f.properties.priority_category === 'Sangat Tinggi').length;
        const avgGap = features.reduce((s, f) => s + f.properties.healthcare_gap_score, 0) / features.length;

        document.getElementById('ov-districts').textContent = '31';
        document.getElementById('ov-critical').textContent = critical;
        document.getElementById('ov-equity').textContent = avgGap.toFixed(1);

        // Facility and worker counts from facility data
        if (rawFacilityData) {
            document.getElementById('ov-facilities').textContent = rawFacilityData.features.length;
        }

        // Workers: try to get from properties or default
        document.getElementById('ov-workers').textContent = '2,340+';

        // Overview donut
        renderOverviewDonut(features);
    }

    function renderOverviewDonut(features) {
        const counts = { 'Sangat Tinggi': 0, 'Tinggi': 0, 'Sedang': 0, 'Rendah': 0 };
        features.forEach(f => { counts[f.properties.priority_category] = (counts[f.properties.priority_category] || 0) + 1; });

        const ctx = document.getElementById('overview-donut-chart');
        if (!ctx) return;
        if (charts.overviewDonut) charts.overviewDonut.destroy();

        charts.overviewDonut = new Chart(ctx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: Object.keys(counts),
                datasets: [{
                    data: Object.values(counts),
                    backgroundColor: ['#dc2626', '#ea580c', '#ca8a04', '#16a34a'],
                    borderWidth: 1,
                    borderColor: '#111827',
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#9ca3af', font: { size: 9 }, padding: 6, boxWidth: 8 }
                    }
                },
                cutout: '60%'
            }
        });
    }

    function populateOverviewPriorityTable() {
        if (!rawKecamatanData) return;
        const sorted = [...rawKecamatanData.features]
            .sort((a, b) => a.properties.priority_rank - b.properties.priority_rank)
            .slice(0, 10);

        const tbody = document.getElementById('overview-priority-body');
        tbody.innerHTML = '';
        sorted.forEach(f => {
            const p = f.properties;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="rank-num ${p.priority_rank <= 3 ? 'rank-'+p.priority_rank : ''}">#${p.priority_rank}</span></td>
                <td class="kec-name-cell">${titleCase(p.kecamatan)}</td>
                <td class="gap-score-cell" style="color:${PRIORITY_MAP_COLORS[p.priority_category]}">${p.healthcare_gap_score.toFixed(1)}</td>
                <td><span class="badge badge-${p.priority_category.toLowerCase().replace(' ','-')}">${p.priority_category}</span></td>
            `;
            tbody.appendChild(tr);
        });
    }

    // ============================================================
    // MAP INITIALIZATION HELPERS
    // ============================================================
    function createBaseMap(containerId, zoom) {
        const m = L.map(containerId, {
            zoomSnap: 0.1, zoomDelta: 0.5, attributionControl: false
        }).setView(SURABAYA_CENTER, zoom);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(m);
        return m;
    }

    function getGapStyle(score) {
        let fillColor = '#4292c6';
        if (score >= 70) fillColor = '#7f0000';
        else if (score >= 60) fillColor = '#d7301f';
        else if (score >= 50) fillColor = '#ef6548';
        else if (score >= 40) fillColor = '#fc8d59';
        else if (score >= 30) fillColor = '#fdd49e';
        else if (score >= 20) fillColor = '#d1e5f0';
        else if (score >= 10) fillColor = '#9ecae1';
        return { fillColor, weight: 1.5, opacity: 0.8, color: '#1e293b', fillOpacity: 0.65 };
    }

    function getPriorityStyle(priorityCategory) {
        return {
            fillColor: PRIORITY_MAP_COLORS[priorityCategory] || '#64748b',
            weight: 1.5, opacity: 0.8, color: '#1e293b', fillOpacity: 0.70
        };
    }

    function getPriorityColor(cat) {
        if (cat === 'Sangat Tinggi') return COLORS.rose;
        if (cat === 'Tinggi') return COLORS.amber;
        if (cat === 'Sedang') return COLORS.yellow;
        return COLORS.green;
    }

    function titleCase(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
    }

    function getPriorityClass(cat) {
        const map = { 'Sangat Tinggi': 'sangat-tinggi', 'Tinggi': 'tinggi', 'Sedang': 'sedang', 'Rendah': 'rendah' };
        return map[cat] || 'rendah';
    }

    // ============================================================
    // OVERVIEW MAP
    // ============================================================
    function initOverviewMap() {
        if (!rawKecamatanData) return;
        overviewMap = createBaseMap('overview-map', 11);

        overviewGeojsonLayer = L.geoJSON(rawKecamatanData, {
            style: f => getGapStyle(f.properties.healthcare_gap_score),
            onEachFeature: (feature, layer) => {
                const p = feature.properties;
                layer.bindTooltip(`<strong>${titleCase(p.kecamatan)}</strong><br/>Gap: ${p.healthcare_gap_score.toFixed(1)} — ${p.priority_category}`, {
                    className: 'leaflet-tooltip-own', sticky: true
                });
                layer.on('click', () => { switchPage('map'); setTimeout(() => zoomToKecamatanByName(p.kecamatan), 300); });
            }
        }).addTo(overviewMap);

        setTimeout(() => overviewMap.invalidateSize(), 100);
    }

    // ============================================================
    // MAIN MAP
    // ============================================================
    function initMainMap() {
        if (!rawKecamatanData) return;

        mainMap = createBaseMap('map', DEFAULT_ZOOM);
        hospitalLayer = L.featureGroup().addTo(mainMap);
        puskesmasLayer = L.featureGroup().addTo(mainMap);
        clinicLayer = L.featureGroup().addTo(mainMap);

        renderMainKecamatanLayer();
        if (rawFacilityData) renderFacilityMarkers();

        // Filter controls
        document.getElementById('search-kecamatan').addEventListener('input', applyFilters);
        document.getElementById('clear-search').addEventListener('click', () => {
            document.getElementById('search-kecamatan').value = '';
            document.getElementById('clear-search').style.display = 'none';
            applyFilters(); resetMapView();
        });
        document.getElementById('search-kecamatan').addEventListener('input', e => {
            document.getElementById('clear-search').style.display = e.target.value ? 'block' : 'none';
        });
        document.getElementById('filter-priority').addEventListener('change', applyFilters);
        document.getElementById('filter-cause').addEventListener('change', applyFilters);

        // Facility toggles
        document.getElementById('toggle-hospitals').addEventListener('change', e => {
            e.target.checked ? mainMap.addLayer(hospitalLayer) : mainMap.removeLayer(hospitalLayer);
        });
        document.getElementById('toggle-puskesmas').addEventListener('change', e => {
            e.target.checked ? mainMap.addLayer(puskesmasLayer) : mainMap.removeLayer(puskesmasLayer);
        });
        document.getElementById('toggle-clinics').addEventListener('change', e => {
            e.target.checked ? mainMap.addLayer(clinicLayer) : mainMap.removeLayer(clinicLayer);
        });

        // Map mode toggle
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentMapMode = btn.dataset.mode;
                renderMainKecamatanLayer();
                updateMapLegend(currentMapMode);
            });
        });

        initMainCharts();
        setTimeout(() => mainMap.invalidateSize(), 100);
    }

    function renderMainKecamatanLayer() {
        if (!rawKecamatanData) return;
        if (mainGeojsonLayer) mainMap.removeLayer(mainGeojsonLayer);

        mainGeojsonLayer = L.geoJSON(rawKecamatanData, {
            style: f => currentMapMode === 'priority'
                ? getPriorityStyle(f.properties.priority_category)
                : getGapStyle(f.properties.healthcare_gap_score),
            onEachFeature: (feature, layer) => {
                const p = feature.properties;
                layer.bindTooltip(`
                    <div style="font-family:Inter,sans-serif;">
                        <strong style="color:#fff;">${titleCase(p.kecamatan)}</strong><br/>
                        <span style="color:#9ca3af;">Gap Score: <strong>${p.healthcare_gap_score.toFixed(1)}</strong></span><br/>
                        <span style="color:${PRIORITY_MAP_COLORS[p.priority_category]}">● ${p.priority_category}</span>
                    </div>`, { className: 'leaflet-tooltip-own', sticky: true, direction: 'right' });

                layer.on({
                    mouseover: e => { if (e.target !== activeKecamatanLayer) e.target.setStyle({ weight: 3, color: '#fff', fillOpacity: 0.85 }); },
                    mouseout: e => { if (e.target !== activeKecamatanLayer) mainGeojsonLayer.resetStyle(e.target); },
                    click: e => selectKecamatan(e.target, p)
                });
            }
        }).addTo(mainMap);
    }

    function updateMapLegend(mode) {
        const gapScale = document.getElementById('legend-scale-gap');
        const gapLabels = document.getElementById('legend-labels-gap');
        const priorityLegend = document.getElementById('legend-priority');
        const title = document.getElementById('legend-title');

        if (mode === 'priority') {
            gapScale.style.display = 'none';
            gapLabels.style.display = 'none';
            priorityLegend.style.display = 'flex';
            title.textContent = 'Priority Category';
        } else {
            gapScale.style.display = 'flex';
            gapLabels.style.display = 'flex';
            priorityLegend.style.display = 'none';
            title.textContent = 'Healthcare Gap Score';
        }
    }

    // ============================================================
    // FACILITY MARKERS
    // ============================================================
    function renderFacilityMarkers() {
        hospitalLayer.clearLayers();
        puskesmasLayer.clearLayers();
        clinicLayer.clearLayers();
        let hCount = 0, pkCount = 0, cCount = 0;

        rawFacilityData.features.forEach(feature => {
            const p = feature.properties;
            const g = feature.geometry;
            if (!g || g.type !== 'Point') return;
            const coords = [g.coordinates[1], g.coordinates[0]];
            const name = p.nama_faskes || p.nama_puskesmas || 'Fasilitas Kesehatan';
            const jenis = p.jenis_faskes || '';
            const capacityStr = p.kapasitas_tempat_tidur ? `${p.kapasitas_tempat_tidur} beds` : 'N/A';
            const popup = `<div class="popup-title">${name}</div>
                <div class="popup-detail"><strong>Type:</strong> ${jenis}</div>
                <div class="popup-detail"><strong>Kecamatan:</strong> ${p.kecamatan || 'N/A'}</div>
                <div class="popup-detail"><strong>Operator:</strong> ${p.penyelenggara || 'N/A'}</div>
                <div class="popup-detail"><strong>Capacity:</strong> ${capacityStr}</div>
                <div class="popup-detail"><strong>Coordinates:</strong> ${coords[0].toFixed(5)}, ${coords[1].toFixed(5)}</div>`;

            if (jenis.includes('Rumah Sakit')) {
                hCount++;
                L.marker(coords, { icon: L.divIcon({ className: 'custom-marker custom-marker-hospital', html: '<i class="fa-solid fa-hospital" style="font-size:10px;"></i>', iconSize: [22,22], iconAnchor: [11,11] }) })
                    .bindPopup(popup).addTo(hospitalLayer);
            } else if (jenis.includes('Puskesmas') || jenis.includes('Pustu')) {
                pkCount++;
                L.marker(coords, { icon: L.divIcon({ className: 'custom-marker custom-marker-puskesmas', html: '<i class="fa-solid fa-house-medical" style="font-size:10px;"></i>', iconSize: [20,20], iconAnchor: [10,10] }) })
                    .bindPopup(popup).addTo(puskesmasLayer);
            } else if (jenis.includes('Klinik')) {
                cCount++;
                L.marker(coords, { icon: L.divIcon({ className: 'custom-marker custom-marker-clinic', html: '<i class="fa-solid fa-clinic-medical" style="font-size:10px;"></i>', iconSize: [20,20], iconAnchor: [10,10] }) })
                    .bindPopup(popup).addTo(clinicLayer);
            }
        });

        const cRS = document.getElementById('count-rs');
        const cPKM = document.getElementById('count-pkm');
        const cCLI = document.getElementById('count-clinics');
        if (cRS) cRS.textContent = `(${hCount})`;
        if (cPKM) cPKM.textContent = `(${pkCount})`;
        if (cCLI) cCLI.textContent = `(${cCount})`;
        if (document.getElementById('ov-facilities')) document.getElementById('ov-facilities').textContent = hCount + pkCount + cCount;
    }

    // ============================================================
    // MAP INTERACTION
    // ============================================================
    function selectKecamatan(layer, props) {
        if (activeKecamatanLayer && activeKecamatanLayer !== layer) mainGeojsonLayer.resetStyle(activeKecamatanLayer);
        activeKecamatanLayer = layer;
        currentSelectedKec = props.kecamatan;

        mainMap.fitBounds(layer.getBounds(), { maxZoom: 13.5, padding: [30, 30] });
        layer.setStyle({ weight: 4, color: '#6366f1', fillOpacity: 0.88 });
        layer.bringToFront();

        populateSidebar(props);
        highlightBarInChart(props.kecamatan);
    }

    function resetMapView() {
        if (activeKecamatanLayer) { mainGeojsonLayer.resetStyle(activeKecamatanLayer); activeKecamatanLayer = null; }
        mainMap.setView(SURABAYA_CENTER, DEFAULT_ZOOM);
        document.getElementById('details-placeholder').style.display = 'flex';
        document.getElementById('details-content').style.display = 'none';
    }

    function zoomToKecamatanByName(name) {
        if (!mainGeojsonLayer) { setTimeout(() => zoomToKecamatanByName(name), 200); return; }
        mainGeojsonLayer.eachLayer(layer => {
            if (layer.feature.properties.kecamatan.toUpperCase() === name.toUpperCase()) {
                selectKecamatan(layer, layer.feature.properties);
            }
        });
    }

    // ============================================================
    // SIDEBAR DETAILS PANEL
    // ============================================================
    function populateSidebar(props) {
        document.getElementById('details-placeholder').style.display = 'none';
        document.getElementById('details-content').style.display = 'flex';

        document.getElementById('detail-name').textContent = `Kec. ${titleCase(props.kecamatan)}`;
        document.getElementById('detail-rank').textContent = `#${props.priority_rank}`;
        document.getElementById('detail-score').textContent = props.healthcare_gap_score.toFixed(1);
        document.getElementById('detail-explanation').textContent = props.explanation || 'Tidak ada narasi analisis.';

        const badge = document.getElementById('detail-priority-badge');
        badge.className = `badge ${getPriorityClass(props.priority_category)}`;
        badge.textContent = props.priority_category;

        setCircleRing(props.healthcare_gap_score, props.priority_category);

        const wf = props.workforce_gap || 0, fac = props.facility_gap || 0, dem = props.demand_score || 0, dis = props.disease_need_score || 0;
        setProgress('workforce', wf, props.workforce_issue);
        setProgress('facility', fac, props.facility_issue);
        setProgress('demand', dem, props.demand_issue);
        setProgress('disease', dis, props.disease_issue);

        // Populate Tenaga Kesehatan (Layer 3)
        const docCount = props.jumlah_tenaga_medis !== undefined ? props.jumlah_tenaga_medis : '—';
        const nurseCount = props.jumlah_perawat !== undefined ? props.jumlah_perawat : '—';
        const midwifeCount = props.jumlah_bidan !== undefined ? props.jumlah_bidan : '—';
        const totalNakes = props.total_tenaga_kesehatan !== undefined ? props.total_tenaga_kesehatan : '—';

        document.getElementById('detail-doctors').textContent = docCount;
        document.getElementById('detail-nurses').textContent = nurseCount;
        document.getElementById('detail-midwives').textContent = midwifeCount;
        document.getElementById('detail-total-nakes').textContent = totalNakes;

        // Populate Demografi & Populasi (Layer 4)
        const popVal = props.jumlah_penduduk !== undefined ? `${(props.jumlah_penduduk * 1000).toLocaleString('id-ID')} jiwa` : '—';
        const densityVal = props.kepadatan_penduduk !== undefined ? `${props.kepadatan_penduduk.toLocaleString('id-ID')} /km²` : '—';

        document.getElementById('detail-population').textContent = popVal;
        document.getElementById('detail-density').textContent = densityVal;

        const pNode = document.getElementById('detail-cause-primary');
        pNode.textContent = (props.primary_root_cause || 'UNKNOWN').replace(/_/g, ' ');
        pNode.style.color = ROOT_CAUSE_COLORS[props.primary_root_cause] || COLORS.indigo;

        const cNode = document.getElementById('detail-confidence');
        cNode.textContent = props.root_cause_confidence || 'MEDIUM';
        cNode.style.color = props.root_cause_confidence === 'HIGH' ? COLORS.green : props.root_cause_confidence === 'MEDIUM' ? COLORS.yellow : COLORS.rose;
    }

    function setProgress(id, val, issueText) {
        const v = document.getElementById(`val-${id}`);
        const f = document.getElementById(`fill-${id}`);
        const i = document.getElementById(`issue-${id}`);
        if (v) v.textContent = val.toFixed(2);
        if (f) f.style.width = `${Math.min(100, val * 100)}%`;
        if (i) i.textContent = (!issueText || issueText === 'NOT_AVAILABLE') ? 'Normal' : issueText;
    }

    function setCircleRing(score, priority) {
        const ring = document.getElementById('detail-score-ring');
        if (!ring) return;
        const r = ring.r.baseVal.value;
        const circ = r * 2 * Math.PI;
        ring.style.strokeDasharray = `${circ} ${circ}`;
        ring.style.strokeDashoffset = circ - (score / 100) * circ;
        ring.style.stroke = getPriorityColor(priority);
    }

    // ============================================================
    // FILTERS
    // ============================================================
    function applyFilters() {
        if (!rawKecamatanData || !mainGeojsonLayer) return;
        const query = (document.getElementById('search-kecamatan').value || '').toLowerCase().trim();
        const pFilter = document.getElementById('filter-priority').value;
        const cFilter = document.getElementById('filter-cause').value;

        const filtered = rawKecamatanData.features.filter(f => {
            const p = f.properties;
            return p.kecamatan.toLowerCase().includes(query)
                && (pFilter === 'ALL' || p.priority_category === pFilter)
                && (cFilter === 'ALL' || p.primary_root_cause === cFilter);
        });

        mainGeojsonLayer.eachLayer(layer => {
            const p = layer.feature.properties;
            const match = filtered.some(f => f.properties.kecamatan === p.kecamatan);
            if (match) {
                layer.setStyle(currentMapMode === 'priority' ? getPriorityStyle(p.priority_category) : getGapStyle(p.healthcare_gap_score));
            } else {
                layer.setStyle({ fillColor: '#334155', weight: 1, color: '#1e293b', opacity: 0.25, fillOpacity: 0.1 });
            }
        });

        if (charts.rankings) {
            const sortedFiltered = [...filtered].sort((a,b) => b.properties.healthcare_gap_score - a.properties.healthcare_gap_score);
            charts.rankings.data.labels = sortedFiltered.map(f => titleCase(f.properties.kecamatan));
            charts.rankings.data.datasets[0].data = sortedFiltered.map(f => f.properties.healthcare_gap_score);
            charts.rankings.data.datasets[0].backgroundColor = sortedFiltered.map(f => getPriorityColor(f.properties.priority_category));
            charts.rankings.update();
        }
    }

    // ============================================================
    // CHARTS (MAIN MAP PAGE)
    // ============================================================
    function initMainCharts() {
        if (!rawKecamatanData) return;
        const features = rawKecamatanData.features;
        const sorted = [...features].sort((a,b) => b.properties.healthcare_gap_score - a.properties.healthcare_gap_score);

        // Rankings Bar Chart
        const ctx1 = document.getElementById('gap-rankings-chart');
        if (ctx1) {
            if (charts.rankings) charts.rankings.destroy();
            charts.rankings = new Chart(ctx1.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: sorted.map(f => titleCase(f.properties.kecamatan)),
                    datasets: [{ label: 'Healthcare Gap Score', data: sorted.map(f => f.properties.healthcare_gap_score), backgroundColor: sorted.map(f => getPriorityColor(f.properties.priority_category)), borderRadius: 3, hoverBackgroundColor: '#818cf8' }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` Score: ${ctx.raw.toFixed(1)}/100` } } },
                    scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 10 } }, min: 0, max: 100 }, x: { grid: { display: false }, ticks: { color: '#9ca3af', font: { size: 8 }, maxRotation: 75, minRotation: 45 } } },
                    onClick: (e, els) => { if (els.length > 0) zoomToKecamatanByName(sorted[els[0].index].properties.kecamatan); }
                }
            });
        }

        // Driver Doughnut
        const causeCounts = {};
        features.forEach(f => {
            const c = f.properties.primary_root_cause || 'UNKNOWN';
            causeCounts[c] = (causeCounts[c] || 0) + 1;
        });
        const ctx2 = document.getElementById('driver-distribution-chart');
        if (ctx2) {
            if (charts.driver) charts.driver.destroy();
            charts.driver = new Chart(ctx2.getContext('2d'), {
                type: 'doughnut',
                data: { labels: Object.keys(causeCounts).map(c => c.replace(/_/g,' ')), datasets: [{ data: Object.values(causeCounts), backgroundColor: Object.keys(causeCounts).map(c => ROOT_CAUSE_COLORS[c] || COLORS.slate), borderWidth: 1, borderColor: '#111827', hoverOffset: 4 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { color: '#9ca3af', font: { size: 9 }, padding: 8, boxWidth: 10 } }, tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw} Kecamatan` } } }, cutout: '65%' }
            });
        }
    }

    function highlightBarInChart(name) {
        if (!charts.rankings) return;
        const idx = charts.rankings.data.labels.findIndex(l => l.toUpperCase() === name.toUpperCase());
        if (idx !== -1) {
            charts.rankings.setActiveElements([{ datasetIndex: 0, index: idx }]);
            charts.rankings.tooltip.setActiveElements([{ datasetIndex: 0, index: idx }], { x: 0, y: 0 });
            charts.rankings.update();
        }
    }

    // ============================================================
    // ANALYTICS PAGE
    // ============================================================
    function renderAnalyticsPage() {
        if (!rawKecamatanData) return;
        renderFullRankingTable(rawKecamatanData.features);
        renderRCAChart();
        renderDistributionChart();

        document.getElementById('analytics-search').oninput = filterAnalyticsTable;
        document.getElementById('analytics-filter-priority').onchange = filterAnalyticsTable;
    }

    function renderFullRankingTable(features) {
        const sorted = [...features].sort((a,b) => a.properties.priority_rank - b.properties.priority_rank);
        const tbody = document.getElementById('full-ranking-body');
        tbody.innerHTML = '';
        sorted.forEach(f => {
            const p = f.properties;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="rank-num ${p.priority_rank<=3?'rank-'+p.priority_rank:''}">#${p.priority_rank}</span></td>
                <td class="kec-name-cell">${titleCase(p.kecamatan)}</td>
                <td class="gap-score-cell" style="color:${PRIORITY_MAP_COLORS[p.priority_category]}">${p.healthcare_gap_score.toFixed(1)}</td>
                <td><span class="badge ${getPriorityClass(p.priority_category)}">${p.priority_category}</span></td>
                <td><span class="driver-badge">${(p.primary_root_cause||'').replace(/_/g,' ')}</span></td>
                <td style="color:#f87171">${(p.workforce_gap||0).toFixed(2)}</td>
                <td style="color:#fb923c">${(p.facility_gap||0).toFixed(2)}</td>
                <td><button class="btn-secondary" onclick="switchPage('optimizer');setTimeout(()=>prefillOptimizer('${p.kecamatan}'),300);">Optimize →</button></td>
            `;
            tbody.appendChild(tr);
        });
    }

    function filterAnalyticsTable() {
        if (!rawKecamatanData) return;
        const query = (document.getElementById('analytics-search').value || '').toLowerCase();
        const pFilter = document.getElementById('analytics-filter-priority').value;
        const filtered = rawKecamatanData.features.filter(f => {
            const p = f.properties;
            return p.kecamatan.toLowerCase().includes(query) && (pFilter === 'ALL' || p.priority_category === pFilter);
        });
        renderFullRankingTable(filtered);
    }

    function renderRCAChart() {
        if (!rawKecamatanData) return;
        const features = rawKecamatanData.features;
        const causeCounts = {};
        features.forEach(f => { const c = f.properties.primary_root_cause || 'UNKNOWN'; causeCounts[c] = (causeCounts[c] || 0) + 1; });

        const ctx = document.getElementById('analytics-rca-chart');
        if (!ctx) return;
        if (charts.analyticsRca) charts.analyticsRca.destroy();
        charts.analyticsRca = new Chart(ctx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: Object.keys(causeCounts).map(c => c.replace(/_/g,' ')),
                datasets: [{ data: Object.values(causeCounts), backgroundColor: Object.keys(causeCounts).map(c => ROOT_CAUSE_COLORS[c] || COLORS.slate), borderRadius: 4 }]
            },
            options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 10 } } }, y: { grid: { display: false }, ticks: { color: '#9ca3af', font: { size: 10 } } } } }
        });
    }

    function renderDistributionChart() {
        if (!rawKecamatanData) return;
        const scores = rawKecamatanData.features.map(f => f.properties.healthcare_gap_score);
        const bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
        const counts = new Array(bins.length - 1).fill(0);
        scores.forEach(s => { for (let i = 0; i < bins.length - 1; i++) { if (s >= bins[i] && s < bins[i+1]) { counts[i]++; break; } } });
        const labels = bins.slice(0,-1).map((b, i) => `${b}–${bins[i+1]}`);

        const ctx = document.getElementById('analytics-dist-chart');
        if (!ctx) return;
        if (charts.analyticsDist) charts.analyticsDist.destroy();
        charts.analyticsDist = new Chart(ctx.getContext('2d'), {
            type: 'bar',
            data: { labels, datasets: [{ label: 'Districts', data: counts, backgroundColor: 'rgba(99,102,241,0.6)', borderRadius: 4, hoverBackgroundColor: '#818cf8' }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 10 } } }, x: { grid: { display: false }, ticks: { color: '#9ca3af', font: { size: 10 } } } } }
        });
    }

    // ============================================================
    // WHAT-IF SIMULATION
    // ============================================================
    const sliders = [
        { id: 'sim-doctors',    valId: 'val-sim-doctors',    prefix: '+', unit: '' },
        { id: 'sim-nurses',     valId: 'val-sim-nurses',     prefix: '+', unit: '' },
        { id: 'sim-midwives',   valId: 'val-sim-midwives',   prefix: '+', unit: '' },
        { id: 'sim-facilities', valId: 'val-sim-facilities', prefix: '+', unit: '' },
        { id: 'sim-beds',       valId: 'val-sim-beds',       prefix: '+', unit: '' }
    ];

    sliders.forEach(s => {
        const el = document.getElementById(s.id);
        const val = document.getElementById(s.valId);
        if (el && val) {
            el.addEventListener('input', () => {
                val.textContent = `${s.prefix}${el.value}${s.unit}`;
            });
        }
    });

    document.getElementById('btn-simulate')?.addEventListener('click', runSimulation);
    document.getElementById('btn-sim-reset')?.addEventListener('click', resetSimulation);

    function runSimulation() {
        const kec = document.getElementById('sim-kecamatan').value;
        if (!kec || !rawKecamatanData) { alert('Please select a Kecamatan first.'); return; }

        const feature = rawKecamatanData.features.find(f => f.properties.kecamatan === kec);
        if (!feature) return;
        const p = feature.properties;

        const dDoctors   = parseInt(document.getElementById('sim-doctors').value) || 0;
        const dNurses    = parseInt(document.getElementById('sim-nurses').value) || 0;
        const dMidwives  = parseInt(document.getElementById('sim-midwives').value) || 0;
        const dFacilities = parseInt(document.getElementById('sim-facilities').value) || 0;
        const dBeds      = parseInt(document.getElementById('sim-beds').value) || 0;

        const totalWorkerSensitivity = (dDoctors * SENSITIVITY.doctor + dNurses * SENSITIVITY.nurse + dMidwives * SENSITIVITY.midwife);
        const totalFacilitySensitivity = (dFacilities * SENSITIVITY.facility + dBeds * SENSITIVITY.beds);

        // Scale by current workforce gap (more room = more impact)
        const wfImpact  = totalWorkerSensitivity * (p.workforce_gap || 0.5) * 100 * 0.30;
        const facImpact = totalFacilitySensitivity * (p.facility_gap || 0.5) * 100 * 0.20;
        const totalReduction = Math.min(wfImpact + facImpact, p.healthcare_gap_score * 0.5); // cap at 50%

        const newScore = Math.max(0, p.healthcare_gap_score - totalReduction);
        const improvement = ((p.healthcare_gap_score - newScore) / p.healthcare_gap_score * 100).toFixed(1);

        // Show results
        document.getElementById('sim-placeholder').style.display = 'none';
        document.getElementById('sim-results').style.display = 'grid';
        document.getElementById('sim-maps').style.display = 'grid';

        document.getElementById('sim-before-score').textContent = p.healthcare_gap_score.toFixed(1);
        document.getElementById('sim-before-priority').textContent = p.priority_category;
        document.getElementById('sim-after-score').textContent = newScore.toFixed(1);
        document.getElementById('sim-after-priority').textContent = getProjectedPriority(newScore);
        document.getElementById('sim-improvement-pct').textContent = `${improvement}%`;

        // Before / After maps
        renderSimMaps(kec, p.healthcare_gap_score, newScore);
    }

    function getProjectedPriority(score) {
        if (score >= 60) return 'Sangat Tinggi';
        if (score >= 45) return 'Tinggi';
        if (score >= 30) return 'Sedang';
        return 'Rendah';
    }

    function renderSimMaps(targetKec, beforeScore, afterScore) {
        // Destroy existing
        if (simMapBefore) { simMapBefore.remove(); simMapBefore = null; }
        if (simMapAfter)  { simMapAfter.remove();  simMapAfter = null; }

        simMapBefore = createBaseMap('sim-map-before', 11);
        simMapAfter  = createBaseMap('sim-map-after', 11);

        [simMapBefore, simMapAfter].forEach((m, isAfter) => {
            L.geoJSON(rawKecamatanData, {
                style: f => {
                    const isTarget = f.properties.kecamatan === targetKec;
                    const score = isTarget ? (isAfter ? afterScore : beforeScore) : f.properties.healthcare_gap_score;
                    return getGapStyle(score);
                },
                onEachFeature: (feature, layer) => {
                    const p = feature.properties;
                    const isTarget = p.kecamatan === targetKec;
                    const label = isTarget ? (isAfter ? `${titleCase(p.kecamatan)}\nProjected: ${afterScore.toFixed(1)}` : `${titleCase(p.kecamatan)}\nCurrent: ${p.healthcare_gap_score.toFixed(1)}`) : titleCase(p.kecamatan);
                    layer.bindTooltip(label, { className: 'leaflet-tooltip-own', sticky: true });
                    if (isTarget) { layer.setStyle({ weight: 3, color: isAfter ? '#4ade80' : '#f87171' }); }
                }
            }).addTo(m);
            setTimeout(() => m.invalidateSize(), 150);
        });
    }

    function resetSimulation() {
        sliders.forEach(s => {
            const el = document.getElementById(s.id);
            const val = document.getElementById(s.valId);
            if (el) el.value = 0;
            if (val) val.textContent = '+0';
        });
        document.getElementById('sim-kecamatan').value = '';
        document.getElementById('sim-placeholder').style.display = 'flex';
        document.getElementById('sim-results').style.display = 'none';
        document.getElementById('sim-maps').style.display = 'none';
    }

    // ============================================================
    // AI OPTIMIZER — INTERVENTION OPTIONS
    // ============================================================
    document.getElementById('btn-analyze-kec')?.addEventListener('click', analyzeKecamatan);
    document.getElementById('btn-optimize')?.addEventListener('click', runResourceOptimizer);

    window.prefillOptimizer = function(kec) {
        const sel = document.getElementById('opt-kecamatan');
        if (sel) sel.value = kec;
        analyzeKecamatan();
    };

    function analyzeKecamatan() {
        const kec = document.getElementById('opt-kecamatan').value;
        if (!kec || !rawKecamatanData) { alert('Please select a Kecamatan.'); return; }

        const feature = rawKecamatanData.features.find(f => f.properties.kecamatan === kec);
        if (!feature) return;
        const p = feature.properties;

        document.getElementById('intervention-options').style.display = 'block';
        document.getElementById('optimizer-placeholder').style.display = 'none';
        document.getElementById('allocation-result').style.display = 'none';

        // Calculate intervention impacts
        const gap = p.healthcare_gap_score;
        const wf  = p.workforce_gap || 0.5;
        const fac = p.facility_gap || 0.5;

        const impactA = (fac * SENSITIVITY.facility * 100 * 0.20).toFixed(1);
        const impactB = (wf  * SENSITIVITY.nurse * 10 * 100 * 0.30).toFixed(1);
        const impactC = (0.08 * gap).toFixed(1);
        const impactD = (Math.min(parseFloat(impactA) + parseFloat(impactB) + parseFloat(impactC), gap * 0.55)).toFixed(1);

        document.getElementById('opt-a-detail').textContent = `Add 1 new facility near high-density area. Estimated cost: Rp 2.5M`;
        document.getElementById('opt-b-detail').textContent = `Redistribute 5 doctors + 10 nurses from surplus districts.`;
        document.getElementById('opt-c-detail').textContent = `Improve road access & mobile health unit deployment.`;
        document.getElementById('opt-d-detail').textContent = `Combined: facility + workers + accessibility in one package.`;

        document.getElementById('opt-a-impact').textContent = `↓ Gap −${impactA} pts`;
        document.getElementById('opt-b-impact').textContent = `↓ Gap −${impactB} pts`;
        document.getElementById('opt-c-impact').textContent = `↓ Gap −${impactC} pts`;
        document.getElementById('opt-d-impact').textContent = `↓ Gap −${impactD} pts (Best)`;

        // Show AI Recommendation for best option (D)
        showAIRecommendation(p, impactD);
    }

    function showAIRecommendation(props, projectedReduction) {
        document.getElementById('ai-rec-box').style.display = 'block';
        document.getElementById('optimizer-placeholder').style.display = 'none';

        const newGap = Math.max(0, props.healthcare_gap_score - parseFloat(projectedReduction));
        const improvePct = ((props.healthcare_gap_score - newGap) / props.healthcare_gap_score * 100).toFixed(1);
        const driver = (props.primary_root_cause || '').replace(/_/g, ' ');
        const totalCost = (5 * COST.doctor + 10 * COST.nurse + 1 * COST.facility);

        document.getElementById('rec-area').textContent = titleCase(props.kecamatan);
        document.getElementById('rec-problem').textContent = driver;
        document.getElementById('rec-action').textContent = 'Combined Intervention (Option D)';
        document.getElementById('rec-resources').textContent = '+5 Doctors, +10 Nurses, +1 Facility';
        document.getElementById('rec-reduction').textContent = `−${improvePct}%`;
        document.getElementById('rec-cost').textContent = `Rp ${(totalCost/1000).toFixed(1)} Miliar`;
        document.getElementById('rec-confidence').textContent = props.root_cause_confidence || 'HIGH';
    }

    // ============================================================
    // RESOURCE CONSTRAINT — GREEDY OPTIMIZER
    // ============================================================
    function runResourceOptimizer() {
        if (!rawKecamatanData) return;

        const budget    = parseFloat(document.getElementById('res-budget').value) || 5000;
        let avDoctors  = parseInt(document.getElementById('res-doctors').value) || 10;
        let avNurses   = parseInt(document.getElementById('res-nurses').value) || 20;

        // Greedy: sort by gap desc, allocate resources
        const sorted = [...rawKecamatanData.features]
            .sort((a,b) => b.properties.healthcare_gap_score - a.properties.healthcare_gap_score);

        let remaining = budget;
        const allocation = [];

        for (const f of sorted) {
            if (remaining <= 0 && avDoctors <= 0 && avNurses <= 0) break;
            const p = f.properties;

            const allocDoctors = Math.min(avDoctors, 2);
            const allocNurses  = Math.min(avNurses, 5);
            const costUnit = allocDoctors * COST.doctor + allocNurses * COST.nurse;
            if (remaining < costUnit && allocDoctors === 0 && allocNurses === 0) continue;

            const actualCost = Math.min(costUnit, remaining);
            if (actualCost <= 0 && allocDoctors === 0 && allocNurses === 0) continue;

            const wfImpact  = (allocDoctors * SENSITIVITY.doctor + allocNurses * SENSITIVITY.nurse) * (p.workforce_gap || 0.5) * 100 * 0.30;
            const newGap = Math.max(0, p.healthcare_gap_score - wfImpact);
            const improve = ((p.healthcare_gap_score - newGap) / p.healthcare_gap_score * 100).toFixed(1);

            allocation.push({ rank: p.priority_rank, kecamatan: titleCase(p.kecamatan), currentGap: p.healthcare_gap_score.toFixed(1), doctors: allocDoctors, nurses: allocNurses, cost: actualCost, projectedGap: newGap.toFixed(1), improvement: improve + '%', priority: p.priority_category });

            avDoctors  -= allocDoctors;
            avNurses   -= allocNurses;
            remaining  -= actualCost;
        }

        // Render allocation table
        document.getElementById('allocation-result').style.display = 'block';
        document.getElementById('optimizer-placeholder').style.display = 'none';

        const totalImprovement = allocation.reduce((s,a) => s + parseFloat(a.improvement), 0).toFixed(1);
        document.getElementById('allocation-summary').textContent = `Optimal allocation for ${allocation.length} districts. Total projected improvement: ${totalImprovement}%. Budget remaining: Rp ${remaining.toFixed(0)} Juta.`;

        const tbody = document.getElementById('allocation-body');
        tbody.innerHTML = '';
        allocation.forEach(a => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="rank-num">#${a.rank}</span></td>
                <td class="kec-name-cell">${a.kecamatan}</td>
                <td style="color:#f87171;font-weight:700;">${a.currentGap}</td>
                <td style="color:#60a5fa;font-weight:600;">${a.doctors > 0 ? '+'+a.doctors : '—'}</td>
                <td style="color:#a78bfa;font-weight:600;">${a.nurses > 0 ? '+'+a.nurses : '—'}</td>
                <td style="color:#9ca3af;">Rp ${a.cost}</td>
                <td style="color:#4ade80;font-weight:700;">${a.projectedGap}</td>
                <td style="color:#34d399;font-weight:700;">↓${a.improvement}</td>
            `;
            tbody.appendChild(tr);
        });

        // Show overall AI recommendation
        if (allocation.length > 0) {
            const topKec = rawKecamatanData.features.find(f => titleCase(f.properties.kecamatan) === allocation[0].kecamatan);
            if (topKec) showAIRecommendation(topKec.properties, (topKec.properties.healthcare_gap_score * 0.3).toFixed(1));
        }
    }

    // ============================================================
    // INIT
    // ============================================================
    loadAllData();

}); // end DOMContentLoaded
