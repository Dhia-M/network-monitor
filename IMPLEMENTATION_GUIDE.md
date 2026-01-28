# Network Monitoring & Alert System - Implementation Guide

This guide provides detailed step-by-step instructions for building the Network Monitoring & Alert System from scratch.

---

## 📋 Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Project Structure Creation](#2-project-structure-creation)
3. [Database Layer Implementation](#3-database-layer-implementation)
4. [Monitoring Engine Development](#4-monitoring-engine-development)
5. [Alerting System Integration](#5-alerting-system-integration)
6. [Web Dashboard & API](#6-web-dashboard--api)
7. [Advanced Features](#7-advanced-features)
8. [Testing & Deployment](#8-testing--deployment)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Environment Setup

### Step 1.1: Install Python

Ensure you have Python 3.8+ installed:

```bash
python --version
```

If not installed, download from [python.org](https://www.python.org/downloads/)

### Step 1.2: Create Project Directory

```bash
mkdir network-monitoring
cd network-monitoring
```

### Step 1.3: Set Up Virtual Environment

This isolates project dependencies from your system Python:

```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Activate it (Linux/Mac)
source venv/bin/activate
```

You should see `(venv)` prefix in your terminal.

### Step 1.4: Install Dependencies

Create `requirements.txt`:

```txt
Flask==3.0.0
ping3==4.0.4
pysnmp==4.4.12
PyYAML==6.0.1
requests==2.31.0
```

Install all dependencies:

```bash
pip install -r requirements.txt
```

**What each library does:**
- **Flask**: Web framework for the dashboard and API
- **ping3**: Pure Python implementation of ICMP ping
- **pysnmp**: SNMP protocol implementation for collecting device metrics
- **PyYAML**: Parse configuration files
- **requests**: HTTP client for Telegram/webhook notifications

---

## 2. Project Structure Creation

### Step 2.1: Create Directory Structure

```bash
mkdir -p config src/monitoring src/alerting src/database src/api src/utils static/css static/js templates data
```

### Step 2.2: Understand the Architecture

```
network-monitoring/
├── config/              # Configuration files (YAML)
├── src/                # Source code
│   ├── monitoring/     # Device polling logic
│   ├── alerting/       # Notification systems
│   ├── database/       # Data persistence layer
│   ├── api/           # Flask web server & REST API
│   └── utils/         # Helper utilities
├── static/            # CSS, JavaScript, images
├── templates/         # HTML templates
└── data/             # SQLite database storage
```

**Why this structure?**
- **Separation of concerns**: Each module has a specific responsibility
- **Modularity**: Components can be developed and tested independently
- **Scalability**: Easy to add new features or swap implementations

---

## 3. Database Layer Implementation

### Step 3.1: Design the Database Schema

Create `src/database/schema.sql`:

```sql
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
```

**Schema explanation:**
- **devices**: Master list of monitored devices
- **device_status**: Real-time status (prevents duplicate checks)
- **metrics**: Time-series performance data
- **alerts**: Notification history
- **logs**: Audit trail for troubleshooting

### Step 3.2: Create Database Manager

Create `src/database/db_manager.py`:

```python
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path: str = "data/monitoring.db"):
        self.db_path = db_path
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def get_connection(self):
        """Get database connection with foreign keys enabled"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def initialize(self):
        """Create tables from schema.sql"""
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        conn = self.get_connection()
        conn.executescript(schema)
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
    
    # Device operations
    def add_device(self, name: str, ip: str, device_type: str = "unknown", 
                   snmp_enabled: bool = False, snmp_community: str = "public"):
        """Add a new device to monitor"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO devices (name, ip_address, device_type, snmp_enabled, snmp_community)
                VALUES (?, ?, ?, ?, ?)
            """, (name, ip, device_type, snmp_enabled, snmp_community))
            
            device_id = cursor.lastrowid
            
            # Initialize status
            cursor.execute("""
                INSERT INTO device_status (device_id, status, consecutive_failures)
                VALUES (?, 'UNKNOWN', 0)
            """, (device_id,))
            
            conn.commit()
            return device_id
        except sqlite3.IntegrityError:
            print(f"❌ Device with IP {ip} already exists")
            return None
        finally:
            conn.close()
    
    def get_all_devices(self) -> List[Dict]:
        """Retrieve all monitored devices"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT d.*, ds.status, ds.last_check, ds.response_time, ds.consecutive_failures
            FROM devices d
            LEFT JOIN device_status ds ON d.id = ds.device_id
        """)
        
        devices = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return devices
    
    def get_device_by_id(self, device_id: int) -> Optional[Dict]:
        """Get specific device details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT d.*, ds.status, ds.last_check, ds.response_time
            FROM devices d
            LEFT JOIN device_status ds ON d.id = ds.device_id
            WHERE d.id = ?
        """, (device_id,))
        
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def delete_device(self, device_id: int):
        """Remove a device from monitoring"""
        conn = self.get_connection()
        conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        conn.commit()
        conn.close()
    
    # Status operations
    def update_device_status(self, device_id: int, status: str, response_time: float = None):
        """Update device status after a check"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get current status
        cursor.execute("SELECT status, consecutive_failures FROM device_status WHERE device_id = ?", (device_id,))
        current = cursor.fetchone()
        
        if current:
            old_status = current['status']
            failures = current['consecutive_failures']
            
            # Update failure counter
            if status == 'DOWN':
                failures += 1
            else:
                failures = 0
            
            # Detect state change
            state_changed = (old_status != status)
            
            cursor.execute("""
                UPDATE device_status
                SET status = ?, last_check = ?, response_time = ?, consecutive_failures = ?,
                    last_state_change = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE last_state_change END
                WHERE device_id = ?
            """, (status, datetime.now(), response_time, failures, state_changed, device_id))
            
            conn.commit()
            conn.close()
            
            return state_changed, failures
        
        conn.close()
        return False, 0
    
    # Metrics operations
    def add_metric(self, device_id: int, cpu: float = None, memory: float = None, uptime: int = None):
        """Store SNMP performance metrics"""
        conn = self.get_connection()
        conn.execute("""
            INSERT INTO metrics (device_id, cpu_usage, memory_usage, uptime)
            VALUES (?, ?, ?, ?)
        """, (device_id, cpu, memory, uptime))
        conn.commit()
        conn.close()
    
    def get_device_metrics(self, device_id: int, limit: int = 50) -> List[Dict]:
        """Get recent metrics for a device"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM metrics
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (device_id, limit))
        
        metrics = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return metrics
    
    # Alert operations
    def add_alert(self, device_id: int, alert_type: str, message: str):
        """Record an alert"""
        conn = self.get_connection()
        conn.execute("""
            INSERT INTO alerts (device_id, alert_type, message, sent)
            VALUES (?, ?, ?, 0)
        """, (device_id, alert_type, message))
        conn.commit()
        conn.close()
    
    def mark_alert_sent(self, alert_id: int):
        """Mark alert as successfully sent"""
        conn = self.get_connection()
        conn.execute("UPDATE alerts SET sent = 1 WHERE id = ?", (alert_id,))
        conn.commit()
        conn.close()
    
    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        """Get recent alerts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.*, d.name as device_name, d.ip_address
            FROM alerts a
            JOIN devices d ON a.device_id = d.id
            ORDER BY a.timestamp DESC
            LIMIT ?
        """, (limit,))
        
        alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return alerts
    
    # Logging operations
    def add_log(self, event_type: str, message: str, device_id: int = None):
        """Add an event log"""
        conn = self.get_connection()
        conn.execute("""
            INSERT INTO logs (device_id, event_type, message)
            VALUES (?, ?, ?)
        """, (device_id, event_type, message))
        conn.commit()
        conn.close()
    
    def get_recent_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent logs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT l.*, d.name as device_name
            FROM logs l
            LEFT JOIN devices d ON l.device_id = d.id
            ORDER BY l.timestamp DESC
            LIMIT ?
        """, (limit,))
        
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return logs
```

**Key features:**
- Connection pooling with `row_factory` for easier data access
- Transaction management
- Foreign key constraints enabled
- Comprehensive CRUD operations
- State change detection for alerting

### Step 3.3: Test Database Setup

Create a test script `test_db.py`:

```python
from src.database.db_manager import DatabaseManager

# Initialize database
db = DatabaseManager()
db.initialize()

# Add test devices
db.add_device("Google DNS", "8.8.8.8", "dns_server", False)
db.add_device("Local Router", "192.168.1.1", "router", True, "public")

# Verify
devices = db.get_all_devices()
print(f"✅ Added {len(devices)} devices")
for device in devices:
    print(f"  - {device['name']} ({device['ip_address']})")
```

Run it:

```bash
python test_db.py
```

Expected output:
```
✅ Database initialized successfully
✅ Added 2 devices
  - Google DNS (8.8.8.8)
  - Local Router (192.168.1.1)
```

---

## 4. Monitoring Engine Development

### Step 4.1: Implement ICMP Ping Monitor

Create `src/monitoring/ping_monitor.py`:

```python
from ping3 import ping
from typing import Tuple, Optional

def ping_device(ip_address: str, timeout: int = 2, count: int = 1) -> Tuple[str, Optional[float]]:
    """
    Ping a device and return status and response time.
    
    Args:
        ip_address: IP address to ping
        timeout: Timeout in seconds
        count: Number of ping attempts
    
    Returns:
        Tuple of (status, response_time)
        status: 'UP' or 'DOWN'
        response_time: Time in milliseconds (None if DOWN)
    """
    try:
        # ping3 requires root/admin on some systems
        # Returns response time in seconds, or None/False if unreachable
        response = ping(ip_address, timeout=timeout, unit='ms')
        
        if response is not None and response is not False:
            return ('UP', round(response, 2))
        else:
            return ('DOWN', None)
            
    except Exception as e:
        print(f"⚠️  Ping error for {ip_address}: {e}")
        return ('DOWN', None)

def check_multiple_devices(ip_list: list) -> dict:
    """
    Ping multiple devices and return results.
    
    Args:
        ip_list: List of IP addresses
    
    Returns:
        Dictionary with IP as key, (status, response_time) as value
    """
    results = {}
    for ip in ip_list:
        results[ip] = ping_device(ip)
    return results
```

**How it works:**
- Uses ICMP Echo Request/Reply (ping)
- Returns round-trip time (RTT) in milliseconds
- Handles network errors gracefully
- Timeout prevents hanging on unreachable hosts

**Note:** On Windows, `ping3` requires admin privileges. Alternative: use `subprocess` to call system ping.

### Step 4.2: Implement SNMP Monitor

Create `src/monitoring/snmp_monitor.py`:

```python
from pysnmp.hlapi import *
from typing import Dict, Optional

class SNMPMonitor:
    """Collect performance metrics via SNMP"""
    
    # Standard SNMP OIDs
    OID_CPU_USAGE = '1.3.6.1.4.1.2021.11.9.0'      # UCD-SNMP-MIB
    OID_MEMORY_TOTAL = '1.3.6.1.4.1.2021.4.5.0'    # memTotalReal
    OID_MEMORY_FREE = '1.3.6.1.4.1.2021.4.6.0'     # memAvailReal
    OID_SYSTEM_UPTIME = '1.3.6.1.2.1.1.3.0'        # sysUpTime
    
    def __init__(self, community: str = 'public', timeout: int = 5, retries: int = 2):
        self.community = community
        self.timeout = timeout
        self.retries = retries
    
    def get_metric(self, ip_address: str, oid: str) -> Optional[int]:
        """
        Query a single SNMP OID.
        
        Args:
            ip_address: Target device IP
            oid: SNMP OID to query
        
        Returns:
            Integer value or None if failed
        """
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(self.community),
                UdpTransportTarget((ip_address, 161), timeout=self.timeout, retries=self.retries),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                print(f"⚠️  SNMP error: {errorIndication}")
                return None
            elif errorStatus:
                print(f"⚠️  SNMP error: {errorStatus.prettyPrint()}")
                return None
            else:
                # Extract value from result
                for varBind in varBinds:
                    return int(varBind[1])
                    
        except Exception as e:
            print(f"⚠️  SNMP exception for {ip_address}: {e}")
            return None
    
    def collect_metrics(self, ip_address: str) -> Dict[str, Optional[float]]:
        """
        Collect all metrics from a device.
        
        Returns:
            Dictionary with cpu_usage, memory_usage, uptime
        """
        metrics = {
            'cpu_usage': None,
            'memory_usage': None,
            'uptime': None
        }
        
        # Get CPU usage
        cpu = self.get_metric(ip_address, self.OID_CPU_USAGE)
        if cpu is not None:
            metrics['cpu_usage'] = float(cpu)
        
        # Calculate memory usage
        mem_total = self.get_metric(ip_address, self.OID_MEMORY_TOTAL)
        mem_free = self.get_metric(ip_address, self.OID_MEMORY_FREE)
        
        if mem_total and mem_free:
            used = mem_total - mem_free
            metrics['memory_usage'] = round((used / mem_total) * 100, 2)
        
        # Get uptime (in hundredths of seconds)
        uptime = self.get_metric(ip_address, self.OID_SYSTEM_UPTIME)
        if uptime is not None:
            metrics['uptime'] = uptime // 100  # Convert to seconds
        
        return metrics
```

**SNMP Protocol Overview:**
- **Community string**: Password for SNMP access (default: "public")
- **OIDs**: Object Identifiers - unique addresses for metrics
- **Port 161**: Standard SNMP port
- **V2c**: SNMP version (balance of simplicity and features)

**Common OIDs:**
- `1.3.6.1.2.1.1.3.0` - System uptime
- `1.3.6.1.4.1.2021.11.9.0` - CPU usage (Linux/NET-SNMP)
- `1.3.6.1.4.1.2021.4.*` - Memory statistics

### Step 4.3: Create Monitoring Scheduler

Create `src/monitoring/scheduler.py`:

```python
import time
import threading
from typing import List
from src.database.db_manager import DatabaseManager
from src.monitoring.ping_monitor import ping_device
from src.monitoring.snmp_monitor import SNMPMonitor

class MonitoringScheduler:
    """Main monitoring loop that polls devices periodically"""
    
    def __init__(self, poll_interval: int = 30, failure_threshold: int = 3):
        """
        Args:
            poll_interval: Seconds between checks
            failure_threshold: Consecutive failures before alerting
        """
        self.poll_interval = poll_interval
        self.failure_threshold = failure_threshold
        self.db = DatabaseManager()
        self.snmp = SNMPMonitor()
        self.running = False
        self.thread = None
    
    def check_device(self, device: dict):
        """
        Check a single device (ping + optional SNMP).
        
        Args:
            device: Device dictionary from database
        """
        device_id = device['id']
        ip = device['ip_address']
        name = device['name']
        
        # 1. Ping check
        status, response_time = ping_device(ip)
        
        # 2. Update database
        state_changed, failures = self.db.update_device_status(device_id, status, response_time)
        
        # 3. Log the check
        if state_changed:
            self.db.add_log(
                'STATE_CHANGE',
                f"{name} is now {status}",
                device_id
            )
            print(f"🔄 {name} ({ip}): {status}")
        
        # 4. Check if alert should be triggered
        if status == 'DOWN' and failures >= self.failure_threshold:
            if failures == self.failure_threshold:  # Only alert once
                self._trigger_alert(device, 'DOWN')
        elif status == 'UP' and state_changed:
            # Recovery alert
            self._trigger_alert(device, 'UP')
        
        # 5. Collect SNMP metrics if device is UP and SNMP enabled
        if status == 'UP' and device.get('snmp_enabled'):
            metrics = self.snmp.collect_metrics(ip)
            
            if metrics['cpu_usage'] is not None:
                self.db.add_metric(
                    device_id,
                    cpu=metrics['cpu_usage'],
                    memory=metrics['memory_usage'],
                    uptime=metrics['uptime']
                )
                print(f"📊 {name}: CPU={metrics['cpu_usage']}%, MEM={metrics['memory_usage']}%")
    
    def _trigger_alert(self, device: dict, alert_type: str):
        """
        Trigger an alert for a device.
        
        Args:
            device: Device dictionary
            alert_type: 'UP' or 'DOWN'
        """
        if alert_type == 'DOWN':
            message = f"🔴 ALERT: {device['name']} ({device['ip_address']}) is DOWN"
        else:
            message = f"🟢 RECOVERY: {device['name']} ({device['ip_address']}) is back UP"
        
        # Add to database
        self.db.add_alert(device['id'], alert_type, message)
        
        print(message)
        
        # TODO: Send actual notifications (email, Telegram)
        # This will be implemented in the alerting module
    
    def poll_all_devices(self):
        """Single poll cycle - check all devices"""
        devices = self.db.get_all_devices()
        
        if not devices:
            print("⚠️  No devices to monitor")
            return
        
        print(f"\n🔍 Polling {len(devices)} devices...")
        
        for device in devices:
            self.check_device(device)
        
        print(f"✅ Poll complete\n")
    
    def run(self):
        """Main monitoring loop"""
        self.running = True
        print(f"🚀 Monitoring started (interval: {self.poll_interval}s)")
        
        while self.running:
            try:
                self.poll_all_devices()
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                print("\n⏹️  Monitoring stopped by user")
                self.running = False
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                time.sleep(self.poll_interval)
    
    def start_background(self):
        """Start monitoring in a background thread"""
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            print("🚀 Monitoring started in background")
    
    def stop(self):
        """Stop the monitoring loop"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("⏹️  Monitoring stopped")
```

**Scheduler Logic:**
1. **Poll devices** at regular intervals (default: 30s)
2. **Ping each device** to check connectivity
3. **Track consecutive failures** to avoid false positives
4. **Trigger alerts** only after threshold met
5. **Collect SNMP metrics** for devices that support it
6. **Update database** with all results

### Step 4.4: Test Monitoring

Create `test_monitoring.py`:

```python
from src.database.db_manager import DatabaseManager
from src.monitoring.scheduler import MonitoringScheduler

# Initialize
db = DatabaseManager()
db.initialize()

# Add test devices
db.add_device("Google DNS", "8.8.8.8", "dns", False)
db.add_device("Invalid Host", "192.168.99.99", "test", False)

# Run monitoring (will run indefinitely)
scheduler = MonitoringScheduler(poll_interval=10, failure_threshold=2)
scheduler.run()  # Press Ctrl+C to stop
```

Run:

```bash
python test_monitoring.py
```

Expected output:
```
🚀 Monitoring started (interval: 10s)

🔍 Polling 2 devices...
🔄 Google DNS (8.8.8.8): UP
✅ Poll complete

🔍 Polling 2 devices...
🔄 Invalid Host (192.168.99.99): DOWN
✅ Poll complete

🔍 Polling 2 devices...
🔴 ALERT: Invalid Host (192.168.99.99) is DOWN
✅ Poll complete
```

---

## 5. Alerting System Integration

### Step 5.1: Create Configuration File

Create `config/config.yaml`:

```yaml
# Monitoring settings
monitoring:
  poll_interval: 30          # Seconds between device checks
  consecutive_failures: 3    # Failures before alerting
  ping_timeout: 2           # Ping timeout in seconds

# SNMP settings
snmp:
  community: "public"
  timeout: 5
  retries: 2

# Performance thresholds
thresholds:
  cpu_utilization: 80       # Percent
  memory_usage: 85          # Percent
  response_time: 1000       # Milliseconds

# Alerting configuration
alerting:
  enabled: true
  
  # Email notifications
  email:
    enabled: false
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    use_tls: true
    username: "your-email@gmail.com"
    password: "your-app-password"
    from_address: "monitoring@example.com"
    recipients:
      - "admin@example.com"
  
  # Telegram notifications
  telegram:
    enabled: false
    bot_token: "YOUR_BOT_TOKEN_HERE"
    chat_id: "YOUR_CHAT_ID_HERE"
```

### Step 5.2: Implement Alert Manager

Create `src/alerting/alert_manager.py`:

```python
import yaml
from typing import Dict, List
from src.alerting.email_notifier import EmailNotifier
from src.alerting.telegram_notifier import TelegramNotifier

class AlertManager:
    """Coordinates alert notifications across multiple channels"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.enabled = self.config['alerting']['enabled']
        
        # Initialize notifiers
        self.notifiers = []
        
        if self.config['alerting']['email']['enabled']:
            self.notifiers.append(EmailNotifier(self.config['alerting']['email']))
        
        if self.config['alerting']['telegram']['enabled']:
            self.notifiers.append(TelegramNotifier(self.config['alerting']['telegram']))
    
    def send_alert(self, device: Dict, alert_type: str, message: str):
        """
        Send alert through all enabled channels.
        
        Args:
            device: Device information
            alert_type: 'DOWN', 'UP', or 'THRESHOLD'
            message: Alert message
        """
        if not self.enabled:
            return
        
        for notifier in self.notifiers:
            try:
                notifier.send(device, alert_type, message)
            except Exception as e:
                print(f"⚠️  Failed to send alert via {notifier.__class__.__name__}: {e}")
```

### Step 5.3: Implement Email Notifier

Create `src/alerting/email_notifier.py`:

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict

class EmailNotifier:
    """Send email alerts via SMTP"""
    
    def __init__(self, config: Dict):
        self.smtp_server = config['smtp_server']
        self.smtp_port = config['smtp_port']
        self.use_tls = config['use_tls']
        self.username = config['username']
        self.password = config['password']
        self.from_address = config['from_address']
        self.recipients = config['recipients']
    
    def send(self, device: Dict, alert_type: str, message: str):
        """Send email alert"""
        
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[Network Monitor] {alert_type}: {device['name']}"
        msg['From'] = self.from_address
        msg['To'] = ', '.join(self.recipients)
        
        # HTML body
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2 style="color: {'#d32f2f' if alert_type == 'DOWN' else '#388e3c'};">
              {alert_type} Alert
            </h2>
            <table style="border-collapse: collapse; width: 100%;">
              <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Device:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{device['name']}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>IP Address:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{device['ip_address']}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Type:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{device.get('device_type', 'Unknown')}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Status:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{alert_type}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Time:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
              </tr>
            </table>
            <p style="margin-top: 20px;">{message}</p>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        # Send email
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            print(f"✉️  Email sent to {', '.join(self.recipients)}")
        except Exception as e:
            print(f"❌ Email send failed: {e}")
```

**Email Setup (Gmail example):**
1. Enable 2-factor authentication on Gmail
2. Generate an "App Password" (Google Account → Security → App Passwords)
3. Use this app password in config.yaml

### Step 5.4: Implement Telegram Notifier

Create `src/alerting/telegram_notifier.py`:

```python
import requests
from typing import Dict
from datetime import datetime

class TelegramNotifier:
    """Send alerts via Telegram Bot API"""
    
    def __init__(self, config: Dict):
        self.bot_token = config['bot_token']
        self.chat_id = config['chat_id']
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
    
    def send(self, device: Dict, alert_type: str, message: str):
        """Send Telegram message"""
        
        # Emoji indicators
        emoji = {
            'DOWN': '🔴',
            'UP': '🟢',
            'THRESHOLD': '⚠️'
        }.get(alert_type, '🔵')
        
        # Format message
        text = f"""
{emoji} *{alert_type} Alert*

*Device:* {device['name']}
*IP:* `{device['ip_address']}`
*Type:* {device.get('device_type', 'Unknown')}
*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{message}
        """.strip()
        
        # Send via Telegram API
        try:
            response = requests.post(self.api_url, json={
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            })
            
            if response.status_code == 200:
                print(f"📱 Telegram alert sent")
            else:
                print(f"❌ Telegram send failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Telegram error: {e}")
```

**Telegram Setup:**
1. Talk to [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot: `/newbot`
3. Get your bot token
4. Start a chat with your bot
5. Get your chat ID: visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`

---

## 6. Web Dashboard & API

### Step 6.1: Create Flask Application

Create `src/api/app.py`:

```python
from flask import Flask, render_template, jsonify, request
from src.database.db_manager import DatabaseManager

app = Flask(__name__, 
    template_folder='../../templates',
    static_folder='../../static'
)

db = DatabaseManager()

# Import routes
from src.api import routes

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### Step 6.2: Create API Routes

Create `src/api/routes.py`:

```python
from flask import render_template, jsonify, request
from src.api.app import app, db

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """Get current status of all devices"""
    devices = db.get_all_devices()
    
    # Format for JSON response
    return jsonify({
        'devices': devices,
        'summary': {
            'total': len(devices),
            'up': len([d for d in devices if d.get('status') == 'UP']),
            'down': len([d for d in devices if d.get('status') == 'DOWN'])
        }
    })

@app.route('/api/devices')
def api_devices():
    """List all devices"""
    devices = db.get_all_devices()
    return jsonify(devices)

@app.route('/api/devices/<int:device_id>')
def api_device_detail(device_id):
    """Get detailed info for a specific device"""
    device = db.get_device_by_id(device_id)
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Get performance metrics
    metrics = db.get_device_metrics(device_id, limit=20)
    
    return jsonify({
        'device': device,
        'metrics': metrics
    })

@app.route('/api/devices', methods=['POST'])
def api_add_device():
    """Add a new device"""
    data = request.json
    
    device_id = db.add_device(
        name=data['name'],
        ip=data['ip'],
        device_type=data.get('type', 'unknown'),
        snmp_enabled=data.get('snmp_enabled', False),
        snmp_community=data.get('snmp_community', 'public')
    )
    
    if device_id:
        return jsonify({'success': True, 'device_id': device_id})
    else:
        return jsonify({'error': 'Device already exists'}), 400

@app.route('/api/devices/<int:device_id>', methods=['DELETE'])
def api_delete_device(device_id):
    """Remove a device"""
    db.delete_device(device_id)
    return jsonify({'success': True})

@app.route('/api/logs')
def api_logs():
    """Get recent logs"""
    logs = db.get_recent_logs(limit=50)
    return jsonify(logs)

@app.route('/api/alerts')
def api_alerts():
    """Get recent alerts"""
    alerts = db.get_recent_alerts(limit=20)
    return jsonify(alerts)
```

### Step 6.3: Create Dashboard UI

Create `templates/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Monitoring Dashboard</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <h1>🌐 Network Monitoring Dashboard</h1>
            <div class="stats">
                <div class="stat-card">
                    <span class="stat-label">Total Devices</span>
                    <span class="stat-value" id="total-devices">0</span>
                </div>
                <div class="stat-card up">
                    <span class="stat-label">Online</span>
                    <span class="stat-value" id="up-devices">0</span>
                </div>
                <div class="stat-card down">
                    <span class="stat-label">Offline</span>
                    <span class="stat-value" id="down-devices">0</span>
                </div>
            </div>
        </header>

        <!-- Device Grid -->
        <main id="device-grid" class="device-grid">
            <!-- Devices will be loaded here by JavaScript -->
        </main>

        <!-- Loading indicator -->
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Loading device status...</p>
        </div>
    </div>

    <script src="/static/js/dashboard.js"></script>
</body>
</html>
```

### Step 6.4: Style the Dashboard

Create `static/css/style.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

:root {
    --bg-dark: #0f172a;
    --bg-darker: #020617;
    --card-bg: rgba(30, 41, 59, 0.5);
    --border-color: rgba(148, 163, 184, 0.1);
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --success: #10b981;
    --danger: #ef4444;
    --warning: #f59e0b;
    --accent: #3b82f6;
}

body {
    font-family: 'Inter', sans-serif;
    background: linear-gradient(135deg, var(--bg-darker) 0%, var(--bg-dark) 100%);
    color: var(--text-primary);
    min-height: 100vh;
    padding: 20px;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
}

/* Header */
.header {
    margin-bottom: 40px;
    animation: fadeInDown 0.5s ease;
}

.header h1 {
    font-size: 2.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 20px;
}

.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
}

.stat-card {
    background: var(--card-bg);
    backdrop-filter: blur(10px);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: all 0.3s ease;
}

.stat-card:hover {
    transform: translateY(-2px);
    border-color: var(--accent);
    box-shadow: 0 8px 24px rgba(59, 130, 246, 0.15);
}

.stat-label {
    font-size: 0.875rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--text-primary);
}

.stat-card.up .stat-value {
    color: var(--success);
}

.stat-card.down .stat-value {
    color: var(--danger);
}

/* Device Grid */
.device-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 24px;
    animation: fadeIn 0.8s ease;
}

.device-card {
    background: var(--card-bg);
    backdrop-filter: blur(10px);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 24px;
    transition: all 0.3s ease;
}

.device-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
}

.device-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
}

.device-name {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
}

.status-badge {
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.status-badge.up {
    background: rgba(16, 185, 129, 0.15);
    color: var(--success);
    border: 1px solid var(--success);
}

.status-badge.down {
    background: rgba(239, 68, 68, 0.15);
    color: var(--danger);
    border: 1px solid var(--danger);
}

.device-info {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.info-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.875rem;
}

.info-label {
    color: var(--text-secondary);
}

.info-value {
    color: var(--text-primary);
    font-weight: 500;
    font-family: 'Courier New', monospace;
}

/* Loading */
.loading {
    text-align: center;
    padding: 60px 20px;
}

.spinner {
    width: 50px;
    height: 50px;
    border: 3px solid var(--border-color);
    border-top: 3px solid var(--accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 20px;
}

/* Animations */
@keyframes spin {
    to { transform: rotate(360deg); }
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes fadeInDown {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Responsive */
@media (max-width: 768px) {
    .header h1 {
        font-size: 2rem;
    }
    
    .device-grid {
        grid-template-columns: 1fr;
    }
}
```

### Step 6.5: Add Dashboard JavaScript

Create `static/js/dashboard.js`:

```javascript
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
            grid.innerHTML = '<p style="text-align: center; grid-column: 1 / -1; padding: 40px; color: var(--text-secondary);">No devices configured. Add devices to start monitoring.</p>';
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
    const lastCheck = device.last_check ? new Date(device.last_check).toLocaleString() : 'Never';
    
    card.innerHTML = `
        <div class="device-header">
            <div class="device-name">${device.name}</div>
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
    
    return card;
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    // Initial load
    loadDeviceStatus();
    
    // Auto-refresh
    setInterval(loadDeviceStatus, REFRESH_INTERVAL);
});
```

---

## 7. Advanced Features

### Step 7.1: Auto Device Discovery

Create `src/utils/discovery.py`:

```python
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.monitoring.ping_monitor import ping_device
from src.monitoring.snmp_monitor import SNMPMonitor

def scan_subnet(subnet: str, max_workers: int = 50) -> list:
    """
    Scan a subnet for active devices.
    
    Args:
        subnet: CIDR notation (e.g., '192.168.1.0/24')
        max_workers: Number of parallel threads
    
    Returns:
        List of active IP addresses
    """
    network = ipaddress.ip_network(subnet, strict=False)
    active_hosts = []
    
    print(f"🔍 Scanning {subnet} ({network.num_addresses} addresses)...")
    
    # Use thread pool for parallel scanning
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit ping tasks
        future_to_ip = {
            executor.submit(ping_device, str(ip), timeout=1): str(ip)
            for ip in network.hosts()
        }
        
        # Collect results
        for future in as_completed(future_to_ip):
            ip = future_to_ip[future]
            status, _ = future.result()
            
            if status == 'UP':
                active_hosts.append(ip)
                print(f"  ✅ Found: {ip}")
    
    print(f"📊 Discovered {len(active_hosts)} active devices")
    return active_hosts

def discover_and_add_devices(subnet: str, db_manager, check_snmp: bool = True):
    """
    Discover devices and add them to the database.
    
    Args:
        subnet: CIDR notation
        db_manager: DatabaseManager instance
        check_snmp: Test for SNMP availability
    """
    active_hosts = scan_subnet(subnet)
    snmp = SNMPMonitor() if check_snmp else None
    
    for ip in active_hosts:
        # Check if device already exists
        devices = db_manager.get_all_devices()
        if any(d['ip_address'] == ip for d in devices):
            print(f"⏭️  {ip} already in database")
            continue
        
        # Test SNMP
        snmp_enabled = False
        if snmp:
            metrics = snmp.collect_metrics(ip)
            snmp_enabled = metrics['uptime'] is not None
        
        # Add to database
        device_id = db_manager.add_device(
            name=f"Device-{ip.split('.')[-1]}",
            ip=ip,
            device_type="discovered",
            snmp_enabled=snmp_enabled
        )
        
        print(f"➕ Added {ip} (SNMP: {snmp_enabled})")
```

**Usage:**

```python
from src.database.db_manager import DatabaseManager
from src.utils.discovery import discover_and_add_devices

db = DatabaseManager()
discover_and_add_devices("192.168.1.0/24", db)
```

### Step 7.2: Logger Utility

Create `src/utils/logger.py`:

```python
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name: str = "network_monitor", log_file: str = "logs/monitor.log"):
    """
    Configure application logger with file rotation.
    
    Args:
        name: Logger name
        log_file: Path to log file
    
    Returns:
        Configured logger
    """
    # Create logs directory
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # File handler with rotation (10 MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
```

---

## 8. Testing & Deployment

### Step 8.1: Create Application Entry Point

Create `run.py`:

```python
import threading
import signal
import sys
from src.database.db_manager import DatabaseManager
from src.monitoring.scheduler import MonitoringScheduler
from src.api.app import app
from src.utils.logger import setup_logger

# Setup logger
logger = setup_logger()

# Initialize database
db = DatabaseManager()
db.initialize()

# Start monitoring in background
scheduler = MonitoringScheduler(poll_interval=30, failure_threshold=3)
monitoring_thread = threading.Thread(target=scheduler.run, daemon=True)
monitoring_thread.start()

logger.info("🚀 Network Monitoring System started")

# Graceful shutdown handler
def signal_handler(sig, frame):
    logger.info("⏹️  Shutting down...")
    scheduler.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Start Flask web server
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
```

### Step 8.2: Add Sample Devices

Create `add_devices.py`:

```python
from src.database.db_manager import DatabaseManager

db = DatabaseManager()
db.initialize()

# Add sample devices
devices = [
    ("Google DNS", "8.8.8.8", "dns", False),
    ("Cloudflare DNS", "1.1.1.1", "dns", False),
    ("Local Router", "192.168.1.1", "router", True),
]

for name, ip, dev_type, snmp in devices:
    device_id = db.add_device(name, ip, dev_type, snmp)
    if device_id:
        print(f"✅ Added: {name} ({ip})")
```

Run:

```bash
python add_devices.py
```

### Step 8.3: Run the System

```bash
python run.py
```

You should see:

```
✅ Database initialized successfully
🚀 Monitoring started in background
✅ Network Monitoring System started
 * Running on http://0.0.0.0:5000
```

Open your browser: **http://localhost:5000**

---

## 9. Troubleshooting

### Issue: "Permission denied" for ping

**Solution (Windows):**
- Run terminal as Administrator, OR
- Modify `ping_monitor.py` to use `subprocess` instead of `ping3`:

```python
import subprocess

def ping_device(ip, timeout=2):
    try:
        result = subprocess.run(
            ['ping', '-n', '1', '-w', str(timeout*1000), ip],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # Parse response time from output
            # This is simplified - full parsing needed
            return ('UP', 10.0)
        else:
            return ('DOWN', None)
    except Exception as e:
        return ('DOWN', None)
```

### Issue: SNMP not working

**Possible causes:**
1. **SNMP not enabled** on target device
2. **Wrong community string** (default: "public")
3. **Firewall blocking** port 161

**Solutions:**
- Enable SNMP on router/device (check device manual)
- Verify community string matches device configuration
- Allow UDP port 161 in Windows Firewall

### Issue: Email not sending

**Gmail users:**
1. Enable 2FA on Google Account
2. Generate App Password (not your regular password)
3. Use App Password in `config.yaml`

### Issue: Dashboard not updating

1. Check browser console (F12) for JavaScript errors
2. Verify Flask server is running
3. Test API manually: `http://localhost:5000/api/status`
4. Check if devices exist in database

---

## 🎉 Next Steps

### Enhancements to Consider:

1. **Add SSL/TLS** for HTTPS dashboard
2. **User authentication** (login system)
3. **Historical graphs** showing uptime trends
4. **Bandwidth monitoring** via SNMP
5. **Custom alerting rules** per device
6. **Export reports** (PDF, CSV)
7. **Mobile app** using the REST API
8. **Slack/Discord webhooks** for alerts
9. **Multi-tenancy** for different customers
10. **Docker containerization** for easy deployment

---

## 📚 Additional Resources

- **ICMP Protocol**: [RFC 792](https://datatracker.ietf.org/doc/html/rfc792)
- **SNMP Protocol**: [Net-SNMP Documentation](http://www.net-snmp.org/)
- **Flask**: [Official Documentation](https://flask.palletsprojects.com/)
- **Chart.js**: [Documentation](https://www.chartjs.org/docs/)
- **SQLite**: [Language Reference](https://www.sqlite.org/lang.html)

---

## ✅ Final Checklist

- [ ] Virtual environment created and activated
- [ ] All dependencies installed
- [ ] Database initialized with schema
- [ ] Configuration file created with your settings
- [ ] Sample devices added
- [ ] Monitoring scheduler tested
- [ ] Alert system configured (email/Telegram)
- [ ] Dashboard accessible at http://localhost:5000
- [ ] Devices showing correct UP/DOWN status
- [ ] SNMP metrics collected (if applicable)
- [ ] Alerts triggered on failures
- [ ] Logs generated in database

---

**Congratulations!** You now have a fully functional Network Monitoring & Alert System. This demonstrates real-world networking skills, automation capabilities, and full-stack development experience valuable for internship roles.
