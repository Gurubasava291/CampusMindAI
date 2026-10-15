/**
 * CampusPulse DSU — Operational Sustainability Map (Leaflet.js)
 */

let campusMap = null;
let markersLayer = null;
let allIssues = [];

document.addEventListener('DOMContentLoaded', () => {
    initSustainabilityMap();
});

function initSustainabilityMap() {
    const mapEl = document.getElementById('sustainability-map-view');
    if (!mapEl) return;

    const defaultLat = parseFloat(mapEl.dataset.lat || '12.6582');
    const defaultLng = parseFloat(mapEl.dataset.lng || '77.4475');
    const defaultZoom = parseInt(mapEl.dataset.zoom || '17');

    // Initialize Leaflet map
    campusMap = L.map('sustainability-map-view').setView([defaultLat, defaultLng], defaultZoom);

    // OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Dayananda Sagar University',
        maxZoom: 19
    }).addTo(campusMap);

    markersLayer = L.layerGroup().addTo(campusMap);

    fetchIssuesAndRender();
    setupFilters();
}

function fetchIssuesAndRender() {
    const category = document.getElementById('filter-category')?.value || '';
    const status = document.getElementById('filter-status')?.value || '';
    const priority = document.getElementById('filter-priority')?.value || '';

    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (status) params.append('status', status);
    if (priority) params.append('priority', priority);

    fetch(`/api/map-issues?${params.toString()}`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                allIssues = data.issues;
                renderMarkers(allIssues);
                updateIssueCount(allIssues.length);
            }
        })
        .catch(err => console.error("Error loading map issues:", err));
}

function renderMarkers(issues) {
    if (!markersLayer) return;
    markersLayer.clearLayers();

    const categoryIcons = {
        'water': '💧',
        'electricity': '⚡',
        'waste': '♻️',
        'greenery': '🌿',
        'infrastructure': '🔧'
    };

    const priorityColors = {
        'critical': '#DC2626',
        'high': '#EA580C',
        'medium': '#EAB308',
        'low': '#64748B'
    };

    issues.forEach(issue => {
        const iconChar = categoryIcons[issue.category] || '📍';
        const ringColor = priorityColors[issue.priority] || '#164227';

        const customIcon = L.divIcon({
            className: 'custom-map-pin',
            html: `
                <div style="
                    background: white;
                    border: 3px solid ${ringColor};
                    width: 36px;
                    height: 36px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 18px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.25);
                ">${iconChar}</div>
            `,
            iconSize: [36, 36],
            iconAnchor: [18, 18]
        });

        const marker = L.marker([issue.latitude, issue.longitude], { icon: customIcon });

        const photoHtml = issue.photo_path ? `
            <img src="${issue.photo_path}" style="width: 100%; height: 110px; object-fit: cover; border-radius: 6px; margin-bottom: 8px;">
        ` : '';

        const popupContent = `
            <div style="font-family: 'Inter', sans-serif; min-width: 200px; max-width: 260px;">
                ${photoHtml}
                <div style="font-size: 11px; font-weight: 700; color: #4D7C5F; text-transform: uppercase;">${issue.report_number} • ${issue.category}</div>
                <h4 style="font-size: 14px; margin: 4px 0 6px; color: #0D2818;">${issue.title}</h4>
                <div style="font-size: 12px; color: #4B5563; margin-bottom: 8px;">📍 ${issue.building_name} (${issue.specific_spot})</div>
                <div style="display: flex; gap: 6px; align-items: center; margin-bottom: 10px;">
                    <span style="font-size: 11px; padding: 2px 8px; border-radius: 12px; font-weight: 600; text-transform: uppercase; background: ${ringColor}; color: white;">
                        ${issue.priority}
                    </span>
                    <span style="font-size: 11px; padding: 2px 8px; border-radius: 12px; background: #E2E8F0; color: #334155; font-weight: 600;">
                        ${issue.status.replace('_', ' ')}
                    </span>
                </div>
                <a href="/reports/${issue.id}" style="display: block; text-align: center; background: #164227; color: white; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; text-decoration: none;">
                    View Full Report
                </a>
            </div>
        `;

        marker.bindPopup(popupContent);
        markersLayer.addLayer(marker);
    });
}

function updateIssueCount(count) {
    const el = document.getElementById('map-issues-count');
    if (el) el.textContent = `${count} issues mapped`;
}

function setupFilters() {
    const filters = ['filter-category', 'filter-status', 'filter-priority'];
    filters.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', fetchIssuesAndRender);
        }
    });

    const resetBtn = document.getElementById('filter-reset-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            filters.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            fetchIssuesAndRender();
        });
    }
}
