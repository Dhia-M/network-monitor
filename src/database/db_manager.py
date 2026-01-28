"""
Database Manager for Network Monitoring System
Handles all database operations including device management, status tracking, metrics, alerts, and logs.
"""

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
            print(f"⚠️  Device with IP {ip} already exists")
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
