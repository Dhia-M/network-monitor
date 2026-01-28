"""
Monitoring Scheduler
Main polling loop that checks all devices periodically
"""

import time
import threading
from typing import List
from src.database.db_manager import DatabaseManager
from src.monitoring.ping_monitor import ping_device
from src.monitoring.snmp_monitor import SNMPMonitor


class MonitoringScheduler:
    """Main monitoring loop that polls devices periodically"""
    
    def __init__(self, poll_interval: int = 3, failure_threshold: int = 3):
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
        
        # TODO: Send actual notifications (email, Telegram) via AlertManager
    
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
