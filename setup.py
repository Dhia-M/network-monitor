"""
Setup script to initialize the monitoring system
Helps with first-time setup and device configuration
"""

import yaml
from src.database.db_manager import DatabaseManager


def setup_database():
    """Initialize the database"""
    print("🔧 Initializing database...")
    db = DatabaseManager()
    db.initialize()
    print("✅ Database initialized")
    return db


def load_devices_from_config(db):
    """Load devices from config file"""
    print("\n📋 Loading devices from config/devices.yaml...")
    
    try:
        with open('config/devices.yaml', 'r') as f:
            device_config = yaml.safe_load(f)
        
        if not device_config or 'devices' not in device_config:
            print("⚠️  No devices found in config file")
            return
        
        added_count = 0
        for device in device_config['devices']:
            # Check if device already exists
            existing = db.get_all_devices()
            if any(d['ip_address'] == device['ip'] for d in existing):
                print(f"⏭️  {device['name']} ({device['ip']}) already exists")
                continue
            
            # Add device
            device_id = db.add_device(
                name=device['name'],
                ip=device['ip'],
                device_type=device.get('type', 'unknown'),
                snmp_enabled=device.get('snmp_enabled', False),
                snmp_community=device.get('snmp_community', 'public')
            )
            
            if device_id:
                print(f"✅ Added: {device['name']} ({device['ip']})")
                added_count += 1
        
        print(f"\n📊 Added {added_count} new devices")
        
    except FileNotFoundError:
        print("❌ config/devices.yaml not found")
    except Exception as e:
        print(f"❌ Error loading devices: {e}")


def display_summary(db):
    """Display setup summary"""
    devices = db.get_all_devices()
    
    print("\n" + "="*50)
    print("📋 Setup Summary")
    print("="*50)
    print(f"Total devices configured: {len(devices)}")
    
    if devices:
        print("\nConfigured devices:")
        for device in devices:
            snmp_status = "✓" if device.get('snmp_enabled') else "✗"
            print(f"  • {device['name']:<20} {device['ip_address']:<15} SNMP: {snmp_status}")
    
    print("\n" + "="*50)
    print("✅ Setup complete!")
    print("="*50)
    print("\nNext steps:")
    print("1. Review configuration in config/config.yaml")
    print("2. Configure email/Telegram alerts if desired")
    print("3. Run: python run.py")
    print("4. Open: http://localhost:5000")
    print("")


if __name__ == '__main__':
    print("🚀 Network Monitoring System - Setup\n")
    
    # Initialize database
    db = setup_database()
    
    # Load devices
    load_devices_from_config(db)
    
    # Display summary
    display_summary(db)
