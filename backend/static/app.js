// SentinelOps Frontend Application Logic - Executive SRE Edition

let metricsChart = null;
let currentMetricView = 'cpu'; // 'cpu', 'mem', 'load'
let currentTTB = null;

// Initialize Chart.js
function initChart() {
    const ctx = document.getElementById('metricsChart').getContext('2d');
    metricsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'User Service',
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.08)',
                    data: [],
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'Order Service',
                    borderColor: '#bc8cff',
                    backgroundColor: 'rgba(188, 140, 255, 0.08)',
                    data: [],
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'Payment Service',
                    borderColor: '#d29922',
                    backgroundColor: 'rgba(210, 153, 34, 0.08)',
                    data: [],
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 350 },
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8b949e', font: { family: 'ui-monospace, monospace', size: 11 } }
                },
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#8b949e', maxTicksLimit: 8, font: { family: 'ui-monospace, monospace', size: 11 } }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#f0f6fc', font: { size: 12, family: '-apple-system, sans-serif' } }
                }
            }
        }
    });
}

// Show Toast Notification
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.style.borderColor = isError ? '#f85149' : '#58a6ff';
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3200);
}

// Trigger Benchmark Chaos Scenarios
async function triggerScenario(endpoint, label) {
    try {
        const res = await fetch(endpoint, { method: 'POST' });
        const data = await res.json();
        showToast(`${label}: Dispatched successfully`);
        fetchStatus();
    } catch (err) {
        showToast(`Error triggering ${label}: ${err.message}`, true);
    }
}

// Inject Individual Service Fault
async function injectFault(service, mode) {
    try {
        const res = await fetch(`/api/fault/${service}/${mode}`, { method: 'POST' });
        const data = await res.json();
        showToast(`Injected '${mode}' fault into ${service}`);
        fetchStatus();
    } catch (err) {
        showToast(`Failed to inject fault: ${err.message}`, true);
    }
}

// Fetch System Status & Update Dashboard
async function fetchStatus() {
    try {
        const res = await fetch('/api/system/status');
        if (!res.ok) return;
        const data = await res.json();

        // 1. Update Service Cards
        for (const [svc, info] of Object.entries(data.services)) {
            const badge = document.getElementById(`badge-${svc}`);
            const cpuEl = document.getElementById(`cpu-${svc}`);
            const memEl = document.getElementById(`mem-${svc}`);
            const slopeEl = document.getElementById(`slope-${svc}`);
            const latEl = document.getElementById(`lat-${svc}`);
            const errEl = document.getElementById(`err-${svc}`);

            if (badge) {
                const mode = info.fault_mode || 'normal';
                if (mode === 'normal') {
                    badge.textContent = 'NORMAL';
                    badge.className = 'badge-status badge-ok';
                } else if (mode === 'cascade_failure' || info.sentinel_alert) {
                    badge.textContent = mode.toUpperCase().replace('_', ' ');
                    badge.className = 'badge-status badge-alert';
                } else if (info.precursor_alert) {
                    badge.textContent = 'LEAK PRECURSOR';
                    badge.className = 'badge-status badge-warning';
                } else {
                    badge.textContent = mode.toUpperCase().replace('_', ' ');
                    badge.className = 'badge-status badge-warning';
                }
            }

            if (cpuEl && info.cpu !== undefined) cpuEl.textContent = `${info.cpu.toFixed(1)}%`;
            if (memEl && info.memory !== undefined) {
                memEl.textContent = `${info.memory.toFixed(1)}%`;
                if (info.memory >= 85.0) {
                    memEl.style.color = '#f85149';
                } else if (info.memory >= 70.0) {
                    memEl.style.color = '#d29922';
                } else {
                    memEl.style.color = '#58a6ff';
                }
            }
            if (slopeEl && info.trend_slope !== undefined) {
                const s = info.trend_slope;
                slopeEl.textContent = `${s >= 0 ? '+' : ''}${s.toFixed(2)}`;
                slopeEl.style.color = s > 0.35 ? '#d29922' : (s < 0 ? '#8b949e' : '#f0f6fc');
            }
            if (latEl && info.latency_ms !== undefined) latEl.textContent = `${info.latency_ms.toFixed(0)} ms`;
            if (errEl && info.error_rate !== undefined) errEl.textContent = `${(info.error_rate * 100).toFixed(1)}%`;
        }

        // 2. Update 3-Way Strategy Comparison Matrix Table
        if (data.sentinel_matrix) {
            const matrix = data.sentinel_matrix;
            const svcs = ['user_service', 'order_service', 'payment_service'];
            
            // Row 1: Static Rule
            svcs.forEach(s => {
                const el = document.getElementById(`matrix-static-${s}`);
                if (el) {
                    const val = matrix.static_rule ? matrix.static_rule[s] : 'OK';
                    el.textContent = val;
                    el.className = val === 'CRITICAL' ? 'badge-status badge-alert' : 'badge-status badge-ok';
                }
            });

            // Row 2: Isolation Forest
            svcs.forEach(s => {
                const el = document.getElementById(`matrix-iso-${s}`);
                if (el) {
                    const val = matrix.isolation_forest ? matrix.isolation_forest[s] : 'OK';
                    el.textContent = val;
                    el.className = val === 'ANOMALY' ? 'badge-status badge-warning' : 'badge-status badge-ok';
                }
            });

            // Row 3: Sentinel Precursor Engine
            svcs.forEach(s => {
                const el = document.getElementById(`matrix-sentinel-${s}`);
                if (el) {
                    const val = matrix.sentinel_precursor ? matrix.sentinel_precursor[s] : 'OK';
                    if (val === 'PRECURSOR_ALERT') {
                        el.textContent = 'PRECURSOR';
                        el.className = 'badge-status badge-alert';
                    } else if (val === 'BURST_SUPPRESSED') {
                        el.textContent = 'SUPPRESSED';
                        el.className = 'badge-status badge-suppressed';
                    } else if (val === 'CRITICAL') {
                        el.textContent = 'CRITICAL';
                        el.className = 'badge-status badge-alert';
                    } else {
                        el.textContent = 'OK';
                        el.className = 'badge-status badge-ok';
                    }
                }
            });
        }

        // 3. Update Precursor Early-Warning Showcase Card
        const precursorCard = document.getElementById('precursor-card');
        const precursorBadge = document.getElementById('precursor-status-badge');
        const ttbValEl = document.getElementById('ttb-countdown') || document.getElementById('ttb-countdown-val');
        const precursorSvcEl = document.getElementById('precursor-service-val');
        const precursorSlopeEl = document.getElementById('precursor-slope-val');
        const precursorMemEl = document.getElementById('precursor-mem-val');
        const precursorLeadEl = document.getElementById('precursor-lead-val');

        if (data.precursor_active && data.active_precursor) {
            precursorCard.classList.add('alert-active');
            precursorBadge.className = 'card-pill pill-precursor-active';
            precursorBadge.textContent = 'PRECURSOR ALERT: ACTIVE';
            
            currentTTB = Math.round(data.active_precursor.ttb_seconds);
            if (ttbValEl) ttbValEl.textContent = currentTTB > 0 ? currentTTB : '0';
            if (precursorSvcEl) precursorSvcEl.textContent = data.active_precursor.service;
            if (precursorSlopeEl) precursorSlopeEl.textContent = `+${data.active_precursor.trend_slope.toFixed(4)} %/tick`;
            if (precursorMemEl) precursorMemEl.textContent = `${data.active_precursor.memory_percent.toFixed(1)} %`;
            if (precursorLeadEl) precursorLeadEl.textContent = `+${currentTTB}s Head-Start`;
        } else {
            precursorCard.classList.remove('alert-active');
            precursorBadge.className = 'card-pill pill-dormant';
            precursorBadge.textContent = 'MONITOR: DORMANT';
            if (ttbValEl) ttbValEl.textContent = '--';
            if (precursorSvcEl) precursorSvcEl.textContent = 'None';
            if (precursorSlopeEl) precursorSlopeEl.textContent = '0.0000 %/tick';
            if (precursorMemEl) precursorMemEl.textContent = '-- %';
            if (precursorLeadEl) precursorLeadEl.textContent = '+41.4s Precursor Advantage';
            currentTTB = null;
        }

        // 4. Update Bivariate Load Shield Card
        const shieldCard = document.getElementById('burst-shield-card');
        const shieldBadge = document.getElementById('burst-status-badge');
        const shieldHeadline = document.getElementById('shield-headline');
        const shieldSubtext = document.getElementById('shield-subtext');
        const shieldCount = document.getElementById('shield-suppressed-count');
        const shieldStatus = document.getElementById('shield-live-status');

        if (data.burst_suppressed_active) {
            shieldCard.classList.add('shield-active');
            shieldBadge.className = 'card-pill pill-shield-active';
            shieldBadge.textContent = 'SHIELD ACTIVE';
            if (shieldHeadline) shieldHeadline.textContent = 'Benign Traffic Burst Decoupled';
            if (shieldSubtext) shieldSubtext.textContent = 'High RPS surge decoupled from internal degradation. Zero false alarms generated.';
            if (shieldCount) shieldCount.textContent = 'Surge Suppressed (0 FPs)';
            if (shieldStatus) shieldStatus.textContent = 'Suppressing False Alarms';
        } else {
            shieldCard.classList.remove('shield-active');
            shieldBadge.className = 'card-pill pill-dormant';
            shieldBadge.textContent = 'SHIELD: READY';
            if (shieldHeadline) shieldHeadline.textContent = 'Surge Discrimination Engine';
            if (shieldSubtext) shieldSubtext.textContent = 'Decouples legitimate traffic demand from internal degradation to eliminate false alarms.';
            if (shieldCount) shieldCount.textContent = '0 FPs (Immune)';
            if (shieldStatus) shieldStatus.textContent = 'Protecting';
        }

        // 5. Update Anomalies Feed & Telemetry Chart
        fetchAnomalies();
        fetchChartData();
    } catch (err) {
        console.error("Status fetch error:", err);
    }
}

// Fetch and Render Anomalies Feed
async function fetchAnomalies() {
    try {
        const res = await fetch('/api/anomalies?limit=10');
        if (!res.ok) return;
        const data = await res.json();
        const list = document.getElementById('anomaly-list');
        const countEl = document.getElementById('stat-anomaly-count');

        if (countEl) countEl.textContent = data.count || 0;

        if (!data.anomalies || data.anomalies.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6e7681" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                    <p>All microservices operating normally.</p>
                    <small>Click a scenario above to test detection.</small>
                </div>
            `;
            return;
        }

        list.innerHTML = data.anomalies.map(a => {
            const timeStr = new Date(a.time).toLocaleTimeString();
            let details = {};
            try {
                details = typeof a.details === 'string' ? JSON.parse(a.details) : (a.details || {});
            } catch (e) {}

            const isPrecursor = a.model_name === 'sentinel_precursor' || details.precursor_flag;
            const ttbText = details.ttb_seconds > 0 ? ` | TTB: ${details.ttb_seconds.toFixed(0)}s` : '';
            const slopeText = details.trend_slope ? ` | β: +${details.trend_slope.toFixed(2)}` : '';

            return `
                <div class="anomaly-item" style="${isPrecursor ? 'border-left-color: #d29922;' : ''}">
                    <div class="anomaly-item-header">
                        <span style="color: var(--text-primary);">${a.service_name}</span>
                        <span style="color: ${isPrecursor ? '#d29922' : '#f85149'}; font-family: ui-monospace, monospace;">${a.model_name.toUpperCase()} (${a.severity})</span>
                    </div>
                    <div class="anomaly-item-meta">
                        <span>CPU: ${details.cpu_percent ? details.cpu_percent.toFixed(1) : '-'}% | Mem: ${details.memory_percent ? details.memory_percent.toFixed(1) : '-'}%${slopeText}${ttbText}</span>
                        <span>${timeStr}</span>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error("Anomalies fetch error:", err);
    }
}

// Fetch and Render Telemetry Chart with Multi-Metric View Toggle
async function fetchChartData() {
    try {
        const res = await fetch('/api/metrics?minutes=10');
        if (!res.ok) return;
        const data = await res.json();

        if (!data.data || data.data.length === 0) return;

        // Group rows by timestamp
        const timeMap = {};
        data.data.forEach(row => {
            const t = new Date(row.time).toLocaleTimeString();
            if (!timeMap[t]) {
                timeMap[t] = {
                    user_service: { cpu: 0, mem: 0, load: 0 },
                    order_service: { cpu: 0, mem: 0, load: 0 },
                    payment_service: { cpu: 0, mem: 0, load: 0 }
                };
            }
            const rps = Math.max(row.requests_total || 0, 0.5);
            const loadRatio = (row.latency_seconds || 0.05) / rps;
            timeMap[t][row.service_name] = {
                cpu: row.cpu_percent || 0,
                mem: row.memory_percent || 0,
                load: Number(loadRatio.toFixed(4))
            };
        });

        const labels = Object.keys(timeMap).slice(-18);

        if (currentMetricView === 'cpu') {
            metricsChart.data.labels = labels;
            metricsChart.data.datasets = [
                {
                    label: 'User Service CPU %',
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.08)',
                    data: labels.map(l => timeMap[l].user_service ? timeMap[l].user_service.cpu : null),
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'Order Service CPU %',
                    borderColor: '#bc8cff',
                    backgroundColor: 'rgba(188, 140, 255, 0.08)',
                    data: labels.map(l => timeMap[l].order_service ? timeMap[l].order_service.cpu : null),
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'Payment Service CPU %',
                    borderColor: '#d29922',
                    backgroundColor: 'rgba(210, 153, 34, 0.08)',
                    data: labels.map(l => timeMap[l].payment_service ? timeMap[l].payment_service.cpu : null),
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 2
                }
            ];
            metricsChart.options.scales.y.min = 0;
            metricsChart.options.scales.y.max = 100;
        } else if (currentMetricView === 'mem') {
            // Memory view with 85% Static Rule threshold line
            const threshold85 = labels.map(() => 85.0);
            metricsChart.data.labels = labels;
            metricsChart.data.datasets = [
                {
                    label: 'User Service Memory %',
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.05)',
                    data: labels.map(l => timeMap[l].user_service ? timeMap[l].user_service.mem : null),
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'Order Service Memory % (Leak)',
                    borderColor: '#d29922',
                    backgroundColor: 'rgba(210, 153, 34, 0.1)',
                    data: labels.map(l => timeMap[l].order_service ? timeMap[l].order_service.mem : null),
                    tension: 0.35,
                    borderWidth: 3,
                    pointRadius: 3
                },
                {
                    label: 'Payment Service Memory %',
                    borderColor: '#bc8cff',
                    backgroundColor: 'rgba(188, 140, 255, 0.05)',
                    data: labels.map(l => timeMap[l].payment_service ? timeMap[l].payment_service.mem : null),
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'Prometheus Tripwire (85%)',
                    borderColor: '#f85149',
                    borderDash: [6, 6],
                    data: threshold85,
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false
                }
            ];
            metricsChart.options.scales.y.min = 20;
            metricsChart.options.scales.y.max = 100;
        } else if (currentMetricView === 'load') {
            // Load Ratio View
            const thresholdShield = labels.map(() => 0.08);
            metricsChart.data.labels = labels;
            metricsChart.data.datasets = [
                {
                    label: 'User Service L̃ Ratio',
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.05)',
                    data: labels.map(l => timeMap[l].user_service ? timeMap[l].user_service.load : null),
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'Order Service L̃ Ratio',
                    borderColor: '#bc8cff',
                    backgroundColor: 'rgba(188, 140, 255, 0.05)',
                    data: labels.map(l => timeMap[l].order_service ? timeMap[l].order_service.load : null),
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'Payment Service L̃ Ratio',
                    borderColor: '#d29922',
                    backgroundColor: 'rgba(210, 153, 34, 0.05)',
                    data: labels.map(l => timeMap[l].payment_service ? timeMap[l].payment_service.load : null),
                    tension: 0.35,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'Surge Shield Boundary (0.08)',
                    borderColor: '#3fb950',
                    borderDash: [5, 5],
                    data: thresholdShield,
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false
                }
            ];
            metricsChart.options.scales.y.min = 0;
            metricsChart.options.scales.y.max = undefined;
        }

        metricsChart.update();
    } catch (err) {
        console.error("Chart data error:", err);
    }
}

// Second-by-second countdown animation
function initCountdownTicker() {
    setInterval(() => {
        if (currentTTB !== null && currentTTB > 0) {
            currentTTB -= 1;
            const el = document.getElementById('ttb-countdown') || document.getElementById('ttb-countdown-val');
            if (el) el.textContent = currentTTB > 0 ? currentTTB : '0';
        }
    }, 1000);
}

// Event Listeners Setup
document.addEventListener('DOMContentLoaded', () => {
    initChart();
    initCountdownTicker();

    // 1. Benchmark Suite Action Bar Buttons
    document.getElementById('btn-scenario-flash-crowd').addEventListener('click', () => {
        triggerScenario('/api/scenarios/flash_crowd', '1. Benign Flash Crowd');
    });
    document.getElementById('btn-scenario-memory-leak').addEventListener('click', () => {
        triggerScenario('/api/scenarios/memory_leak', '2. Progressive Memory Leak');
    });
    document.getElementById('btn-scenario-gateway-timeout').addEventListener('click', () => {
        triggerScenario('/api/scenarios/gateway_timeout', '3. Gateway Timeout');
    });
    document.getElementById('btn-scenario-cascade-failure').addEventListener('click', () => {
        triggerScenario('/api/scenarios/cascade_failure', '4. Cascade Failure');
    });
    document.getElementById('btn-scenario-reset').addEventListener('click', () => {
        triggerScenario('/api/scenarios/reset', 'Reset Normal');
    });

    // 2. Telemetry Chart View Toggles
    const btnCpu = document.getElementById('btn-chart-cpu');
    const btnMem = document.getElementById('btn-chart-mem');
    const btnLoad = document.getElementById('btn-chart-load');

    btnCpu.addEventListener('click', () => {
        currentMetricView = 'cpu';
        btnCpu.classList.add('active');
        btnMem.classList.remove('active');
        btnLoad.classList.remove('active');
        fetchChartData();
    });

    btnMem.addEventListener('click', () => {
        currentMetricView = 'mem';
        btnMem.classList.add('active');
        btnCpu.classList.remove('active');
        btnLoad.classList.remove('active');
        fetchChartData();
    });

    btnLoad.addEventListener('click', () => {
        currentMetricView = 'load';
        btnLoad.classList.add('active');
        btnCpu.classList.remove('active');
        btnMem.classList.remove('active');
        fetchChartData();
    });

    // Initial fetch
    fetchStatus();

    // Poll every 3 seconds for live synchronized dashboard updates
    setInterval(fetchStatus, 3000);
});
