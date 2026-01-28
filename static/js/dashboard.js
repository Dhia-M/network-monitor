// Auto-refresh interval (10 seconds)
const REFRESH_INTERVAL = 10000;

// Fetch and update device status
async function loadDeviceStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Update stats
        document.getElementById('total-devices').textContent = data.summary.total;
        document.getElementById('up-devices').textContent = data.summary.up;
        document.getElementById('down-devices').textContent = data.summary.down;

        // Update device grid
        const grid = document.getElementById('device-grid');
        grid.innerHTML = '';

        if (data.devices.length === 0) {
            grid.innerHTML = '<p style="text-align: center; grid-column: 1 / -1; padding: 40px; color: var(--text-secondary);">No devices configured. Click "Add Device" to start monitoring.</p>';
            document.getElementById('loading').style.display = 'none';
            return;
        }

        data.devices.forEach(device => {
            const card = createDeviceCard(device);
            grid.appendChild(card);
        });

        // Hide loading indicator
        document.getElementById('loading').style.display = 'none';

    } catch (error) {
        console.error('Failed to load device status:', error);
        document.getElementById('loading').innerHTML = '<p style="color: var(--danger);">❌ Failed to load devices</p>';
    }
}

// Create device card element
function createDeviceCard(device) {
    const card = document.createElement('div');
    card.className = 'device-card';

    const status = device.status || 'UNKNOWN';
    const statusClass = status.toLowerCase();
    const responseTime = device.response_time ? `${device.response_time} ms` : 'N/A';
    const lastCheck = device.last_check ? formatDateTime(device.last_check) : 'Never';

    // Build basic info HTML
    let html = `
        <div class="device-header">
            <div class="device-name">${escapeHtml(device.name)}</div>
            <span class="status-badge ${statusClass}">${status}</span>
        </div>
        <div class="device-info">
            <div class="info-row">
                <span class="info-label">IP Address</span>
                <span class="info-value">${device.ip_address}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Type</span>
                <span class="info-value">${device.device_type || 'Unknown'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Response Time</span>
                <span class="info-value">${responseTime}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Last Check</span>
                <span class="info-value">${lastCheck}</span>
            </div>
        </div>
    `;

    // Add SNMP metrics if available
    if (device.snmp_enabled && status === 'UP') {
        html += createMetricsSection(device.id);
    }

    // Add action buttons
    html += `
        <div class="device-actions">
            <button class="btn-detail" onclick="viewDeviceDetails(${device.id})">📊 Details</button>
            <button class="btn-delete" onclick="deleteDevice(${device.id}, '${escapeHtml(device.name)}')">🗑️ Delete</button>
        </div>
    `;

    card.innerHTML = html;

    // Load metrics if SNMP enabled
    if (device.snmp_enabled && status === 'UP') {
        loadDeviceMetrics(device.id);
    }

    return card;
}

// Create metrics section HTML
function createMetricsSection(deviceId) {
    return `
        <div class="metrics-section" id="metrics-${deviceId}">
            <div class="metrics-title">⚙️ Performance Metrics</div>
            <div class="metric-bar">
                <div class="metric-label">
                    <span>CPU Usage</span>
                    <span id="cpu-${deviceId}">Loading...</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill low" id="cpu-bar-${deviceId}" style="width: 0%"></div>
                </div>
            </div>
            <div class="metric-bar">
                <div class="metric-label">
                    <span>Memory Usage</span>
                    <span id="mem-${deviceId}">Loading...</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill low" id="mem-bar-${deviceId}" style="width: 0%"></div>
                </div>
            </div>
            <div class="info-row">
                <span class="info-label">Uptime</span>
                <span class="info-value" id="uptime-${deviceId}">Loading...</span>
            </div>
        </div>
    `;
}

// Load SNMP metrics for a device
async function loadDeviceMetrics(deviceId) {
    try {
        const response = await fetch(`/api/devices/${deviceId}`);
        const data = await response.json();

        if (data.metrics && data.metrics.length > 0) {
            const latest = data.metrics[0];

            // Update CPU
            if (latest.cpu_usage !== null) {
                const cpuValue = Math.round(latest.cpu_usage);
                document.getElementById(`cpu-${deviceId}`).textContent = `${cpuValue}%`;
                const cpuBar = document.getElementById(`cpu-bar-${deviceId}`);
                cpuBar.style.width = `${cpuValue}%`;
                cpuBar.className = `progress-fill ${getMetricClass(cpuValue)}`;
            }

            // Update Memory
            if (latest.memory_usage !== null) {
                const memValue = Math.round(latest.memory_usage);
                document.getElementById(`mem-${deviceId}`).textContent = `${memValue}%`;
                const memBar = document.getElementById(`mem-bar-${deviceId}`);
                memBar.style.width = `${memValue}%`;
                memBar.className = `progress-fill ${getMetricClass(memValue)}`;
            }

            // Update Uptime
            if (latest.uptime !== null) {
                document.getElementById(`uptime-${deviceId}`).textContent = formatUptime(latest.uptime);
            }
        }
    } catch (error) {
        console.error(`Failed to load metrics for device ${deviceId}:`, error);
    }
}

// Get CSS class based on metric value
function getMetricClass(value) {
    if (value < 70) return 'low';
    if (value < 85) return 'medium';
    return 'high';
}

// Format uptime in human-readable format
function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
}

// Format datetime for display
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Modal functions
function openAddDeviceModal() {
    document.getElementById('addDeviceModal').style.display = 'block';
}

function closeAddDeviceModal() {
    document.getElementById('addDeviceModal').style.display = 'none';
    document.getElementById('addDeviceForm').reset();
}

// Toggle SNMP community field
document.addEventListener('DOMContentLoaded', () => {
    const snmpCheckbox = document.getElementById('snmpEnabled');
    const snmpCommunityGroup = document.getElementById('snmpCommunityGroup');

    if (snmpCheckbox) {
        snmpCheckbox.addEventListener('change', function () {
            snmpCommunityGroup.style.display = this.checked ? 'block' : 'none';
        });
    }
});

// Add device function
async function addDevice(event) {
    event.preventDefault();

    const deviceData = {
        name: document.getElementById('deviceName').value,
        ip: document.getElementById('deviceIP').value,
        type: document.getElementById('deviceType').value,
        snmp_enabled: document.getElementById('snmpEnabled').checked,
        snmp_community: document.getElementById('snmpCommunity').value || 'public'
    };

    try {
        const response = await fetch('/api/devices', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(deviceData)
        });

        const result = await response.json();

        if (response.ok) {
            closeAddDeviceModal();
            loadDeviceStatus(); // Refresh the device list
            alert(`✅ Device "${deviceData.name}" added successfully!`);
        } else {
            alert(`❌ Error: ${result.error || 'Failed to add device'}`);
        }
    } catch (error) {
        console.error('Error adding device:', error);
        alert('❌ Failed to add device. Please try again.');
    }
}

// Delete device function
async function deleteDevice(deviceId, deviceName) {
    if (!confirm(`Are you sure you want to delete "${deviceName}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/devices/${deviceId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadDeviceStatus(); // Refresh the device list
            alert(`✅ Device "${deviceName}" deleted successfully!`);
        } else {
            alert('❌ Failed to delete device');
        }
    } catch (error) {
        console.error('Error deleting device:', error);
        alert('❌ Failed to delete device. Please try again.');
    }
}

// View device details
async function viewDeviceDetails(deviceId) {
    try {
        const response = await fetch(`/api/devices/${deviceId}`);
        const data = await response.json();

        document.getElementById('detailDeviceName').textContent = `${data.device.name} - Details`;

        let html = `
            <div style="padding: 24px;">
                <div class="device-info">
                    <div class="info-row">
                        <span class="info-label">IP Address</span>
                        <span class="info-value">${data.device.ip_address}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Type</span>
                        <span class="info-value">${data.device.device_type}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Status</span>
                        <span class="info-value">${data.device.status}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">SNMP Enabled</span>
                        <span class="info-value">${data.device.snmp_enabled ? 'Yes' : 'No'}</span>
                    </div>
                </div>
        `;

        if (data.metrics && data.metrics.length > 0) {
            html += `
                <h3 style="margin-top: 24px; margin-bottom: 16px; color: var(--text-primary);">📊 Recent Metrics</h3>
                <div style="max-height: 300px; overflow-y: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 1px solid var(--border-color);">
                                <th style="padding: 8px; text-align: left; color: var(--text-secondary);">Time</th>
                                <th style="padding: 8px; text-align: left; color: var(--text-secondary);">CPU</th>
                                <th style="padding: 8px; text-align: left; color: var(--text-secondary);">Memory</th>
                                <th style="padding: 8px; text-align: left; color: var(--text-secondary);">Uptime</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            data.metrics.slice(0, 20).forEach(metric => {
                html += `
                    <tr style="border-bottom: 1px solid var(--border-color);">
                        <td style="padding: 8px; color: var(--text-primary);">${formatDateTime(metric.timestamp)}</td>
                        <td style="padding: 8px; color: var(--text-primary);">${metric.cpu_usage !== null ? Math.round(metric.cpu_usage) + '%' : 'N/A'}</td>
                        <td style="padding: 8px; color: var(--text-primary);">${metric.memory_usage !== null ? Math.round(metric.memory_usage) + '%' : 'N/A'}</td>
                        <td style="padding: 8px; color: var(--text-primary);">${metric.uptime !== null ? formatUptime(metric.uptime) : 'N/A'}</td>
                    </tr>
                `;
            });

            html += `
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            html += '<p style="margin-top: 24px; color: var(--text-secondary);">No metrics available yet.</p>';
        }

        html += '</div>';

        document.getElementById('deviceDetailContent').innerHTML = html;
        document.getElementById('deviceDetailModal').style.display = 'block';

    } catch (error) {
        console.error('Error loading device details:', error);
        alert('❌ Failed to load device details');
    }
}

function closeDetailModal() {
    document.getElementById('deviceDetailModal').style.display = 'none';
}

// Close modals when clicking outside
window.onclick = function (event) {
    const addModal = document.getElementById('addDeviceModal');
    const detailModal = document.getElementById('deviceDetailModal');

    if (event.target === addModal) {
        closeAddDeviceModal();
    }
    if (event.target === detailModal) {
        closeDetailModal();
    }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    // Initial load
    loadDeviceStatus();

    // Auto-refresh
    setInterval(loadDeviceStatus, REFRESH_INTERVAL);
});
