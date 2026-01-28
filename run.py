"""
Network Monitoring & Alert System
Main application entry point
"""

import threading
import signal
import sys
import yaml
from src.database.db_manager import DatabaseManager
from src.monitoring.scheduler import MonitoringScheduler
from src.api.app import app
from src.utils.logger import setup_logger


# Setup logger
logger = setup_logger()

# Load configuration
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize database
logger.info("Initializing database...")
db = DatabaseManager()
db.initialize()

# Load devices from config file
logger.info("Loading device definitions...")
with open('config/devices.yaml', 'r') as f:
    device_config = yaml.safe_load(f)

# Add devices from config if they don't exist
if device_config and 'devices' in device_config:
    for device in device_config['devices']:
        existing = db.get_all_devices()
        if not any(d['ip_address'] == device['ip'] for d in existing):
            db.add_device(
                name=device['name'],
                ip=device['ip'],
                device_type=device.get('type', 'unknown'),
                snmp_enabled=device.get('snmp_enabled', False),
                snmp_community=device.get('snmp_community', 'public')
            )
            logger.info(f"Added device: {device['name']} ({device['ip']})")

# Start monitoring in background
logger.info("Starting monitoring scheduler...")
scheduler = MonitoringScheduler(
    poll_interval=config['monitoring']['poll_interval'],
    failure_threshold=config['monitoring']['consecutive_failures']
)
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
    logger.info("Starting web server on http://0.0.0.0:5000")
    app.run(debug=False, host='0.0.0.0', port=5000)
