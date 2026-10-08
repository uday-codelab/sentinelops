// SentinelOps Frontend Application Logic

let metricsChart = null;
let trafficActive = false;

// Initialize Chart.js
function initChart() {
    const ctx = document.getElementById('metricsChart').getContext('2d');
    metricsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'User Service CPU %',
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.08)',
                    data: [],
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'Order Service CPU %',
                    borderColor: '#a855f7',
                    backgroundColor: 'rgba(168, 85, 247, 0.08)',
                    data: [],
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'Payment Service CPU %',
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.08)',
                    data: [],
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af', font: { family: 'JetBrains Mono' } }
                },
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af', maxTicksLimit: 8, font: { family: 'JetBrains Mono' } }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#f9fafb', font: { family: 'Inter', size: 12 } }
                }
            }
        }
    });
}

// Show Toast Notification
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.style.borderColor = isError ? 'rgba(239, 68, 68, 0.5)' : 'rgba(99, 102, 241, 0.5)';
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Inject Fault Mode
async function injectFault(service, mode) {
    try {
        const res = await fetch(`/api/fault/${service}/${mode}`, { method: 'POST' });
        const data = await res.json();
        showToast(`💥 Injected '${mode}' fault into ${service}`);
        fetchStatus();
    } catch (err) {
        showToast(`Failed to inject fault: ${err.message}`, true);
    }
}

// Reset All Services to Normal
async function resetAllServices() {
    try {
        await Promise.all([
            fetch('/api/fault/user_service/normal', { method: 'POST' }),
            fetch('/api/fault/order_service/normal', { method: 'POST' }),
            fetch('/api/fault/payment_service/normal', { method: 'POST' })
        ]);
        showToast('🟢 All microservices reset to NORMAL operating mode');
        fetchStatus();
    } catch (err) {
        showToast(`Error resetting services: ${err.message}`, true);
    }
}

// Toggle Simulated Traffic
async function toggleTraffic() {
    try {
        const res = await fetch('/api/traffic/toggle', { method: 'POST' });
        const data = await res.json();
        trafficActive = data.active;
        
        const btnLabel = document.getElementById('traffic-btn-label');
        const btn = document.getElementById('btn-toggle-traffic');
        
        if (trafficActive) {
            btnLabel.textContent = 'Stop Traffic Simulation';
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-secondary');
            showToast('🚀 Background traffic generator STARTED');
        } else {
            btnLabel.textContent = 'Start Traffic Simulation';
            btn.classList.remove('btn-secondary');
            btn.classList.add('btn-primary');
            showToast('⏸️ Traffic generator PAUSED');
        }
    } catch (err) {
        showToast(`Traffic toggle error: ${err.message}`, true);
    }
}

// Retrain ML Baseline
async function retrainML() {
    try {
        const res = await fetch('/api/models/train', { method: 'POST' });
        const data = await res.json();
        showToast('🧠 Isolation Forest model retrained with fresh baseline');
    } catch (err) {
        showToast(`Training error: ${err.message}`, true);
    }
}

// Fetch System Status & Update Service Cards
async function fetchStatus() {
    try {
        const res = await fetch('/api/system/status');
        if (!res.ok) return;
        const data = await res.json();

        // Update each service card
        for (const [svc, info] of Object.entries(data.services)) {
            const card = document.getElementById(`card-${svc}`);
            const badge = document.getElementById(`badge-${svc}`);
            const cpuEl = document.getElementById(`cpu-${svc}`);
            const latEl = document.getElementById(`lat-${svc}`);
            const errEl = document.getElementById(`err-${svc}`);

            if (!card) continue;

            const mode = info.fault_mode || 'normal';
            badge.textContent = mode.toUpperCase().replace('_', ' ');

            if (mode === 'normal') {
                badge.className = 'badge badge-normal';
                card.className = 'service-card';
            } else if (mode === 'cascade_failure') {
                badge.className = 'badge badge-critical';
                card.className = 'service-card state-critical';
            } else {
                badge.className = 'badge badge-warning';
                card.className = 'service-card';
            }

            if (info.cpu !== undefined) cpuEl.textContent = `${info.cpu.toFixed(1)}%`;
            if (info.latency_ms !== undefined) latEl.textContent = `${info.latency_ms.toFixed(0)} ms`;
            if (info.error_rate !== undefined) errEl.textContent = `${(info.error_rate * 100).toFixed(1)}%`;
        }

        // Update anomalies list
        fetchAnomalies();
        fetchChartData();
    } catch (err) {
        console.error("Status fetch error:", err);
    }
}

// Fetch and Render Anomalies
async function fetchAnomalies() {
    try {
        const res = await fetch('/api/anomalies?limit=10');
        if (!res.ok) return;
        const data = await res.json();
        const list = document.getElementById('anomaly-list');
        const countEl = document.getElementById('stat-anomaly-count');

        countEl.textContent = data.count || 0;

        if (!data.anomalies || data.anomalies.length === 0) {
            list.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">🛡️</span>
                    <p>All microservices operating normally.</p>
                    <small>Inject a fault above to trigger AI detection.</small>
                </div>
            `;
            return;
        }

        list.innerHTML = data.anomalies.map(a => {
            const timeStr = new Date(a.time).toLocaleTimeString();
            let details = {};
            try {
                details = typeof a.details === 'string' ? JSON.parse(a.details) : a.details;
            } catch (e) {}

            return `
                <div class="anomaly-item">
                    <div class="anomaly-header">
                        <span class="anomaly-svc">🚨 ${a.service_name}</span>
                        <span class="anomaly-score">Score: ${a.anomaly_score} (${a.severity})</span>
                    </div>
                    <div class="anomaly-meta">
                        <span>Model: ${a.model_name} | CPU: ${details.cpu_percent ? details.cpu_percent.toFixed(1) : '-'}%</span>
                        <span>${timeStr}</span>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error("Anomalies fetch error:", err);
    }
}

// Fetch Historical Chart Telemetry
async function fetchChartData() {
    try {
        const res = await fetch('/api/metrics?minutes=10');
        if (!res.ok) return;
        const data = await res.json();

        if (!data.data || data.data.length === 0) return;

        // Group metrics by timestamp
        const timeMap = {};
        data.data.forEach(row => {
            const t = new Date(row.time).toLocaleTimeString();
            if (!timeMap[t]) timeMap[t] = { user_service: 0, order_service: 0, payment_service: 0 };
            timeMap[t][row.service_name] = row.cpu_percent || 0;
        });

        const labels = Object.keys(timeMap).slice(-15);
        const userCpu = labels.map(l => timeMap[l].user_service || null);
        const orderCpu = labels.map(l => timeMap[l].order_service || null);
        const payCpu = labels.map(l => timeMap[l].payment_service || null);

        metricsChart.data.labels = labels;
        metricsChart.data.datasets[0].data = userCpu;
        metricsChart.data.datasets[1].data = orderCpu;
        metricsChart.data.datasets[2].data = payCpu;
        metricsChart.update();
    } catch (err) {
        console.error("Chart data error:", err);
    }
}

// Event Listeners Setup
document.addEventListener('DOMContentLoaded', () => {
    initChart();

    document.getElementById('btn-reset-all').addEventListener('click', resetAllServices);
    document.getElementById('btn-toggle-traffic').addEventListener('click', toggleTraffic);
    document.getElementById('btn-train-ml').addEventListener('click', retrainML);

    // Initial fetch
    fetchStatus();

    // Poll every 3 seconds for live dashboard updates
    setInterval(fetchStatus, 3000);
});
