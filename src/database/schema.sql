-- Network Monitoring System Database Schema

-- Device registry
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    ip_address TEXT NOT NULL UNIQUE,
    device_type TEXT,
    snmp_enabled BOOLEAN DEFAULT 0,
    snmp_community TEXT DEFAULT 'public',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Current device status
CREATE TABLE IF NOT EXISTS device_status (
    device_id INTEGER PRIMARY KEY,
    status TEXT NOT NULL,  -- 'UP' or 'DOWN'
    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time REAL,
    consecutive_failures INTEGER DEFAULT 0,
    last_state_change TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Performance metrics (SNMP data)
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_usage REAL,
    memory_usage REAL,
    uptime INTEGER,
    interface_status TEXT,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Alert history
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent BOOLEAN DEFAULT 0,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Event logs
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    device_id INTEGER,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_metrics_device_time ON metrics(device_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_device_time ON alerts(device_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_time ON logs(timestamp);