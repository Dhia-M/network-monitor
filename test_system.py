"""
Quick test script to verify the monitoring system components
Run this after installation to ensure everything works
"""

import sys


def test_imports():
    """Test that all required packages are installed"""
    print("🔍 Testing package imports...")
    
    packages = [
        ('flask', 'Flask'),
        ('ping3', 'ping3'),
        ('pysnmp.hlapi', 'pysnmp'),
        ('yaml', 'PyYAML'),
        ('requests', 'requests')
    ]
    
    all_ok = True
    for module, name in packages:
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} - NOT INSTALLED")
            all_ok = False
    
    return all_ok


def test_database():
    """Test database initialization"""
    print("\n🔍 Testing database...")
    
    try:
        from src.database.db_manager import DatabaseManager
        db = DatabaseManager(db_path="data/test_monitoring.db")
        db.initialize()
        
        # Test adding a device
        device_id = db.add_device("Test Device", "127.0.0.1", "test", False)
        if device_id:
            print("  ✅ Database operations working")
            # Clean up
            db.delete_device(device_id)
            return True
        else:
            print("  ❌ Database operations failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False


def test_ping():
    """Test ping functionality"""
    print("\n🔍 Testing ping monitor...")
    
    try:
        from src.monitoring.ping_monitor import ping_device
        
        # Ping localhost
        status, response_time = ping_device("127.0.0.1", timeout=2)
        
        if status == "UP":
            print(f"  ✅ Ping working (response: {response_time}ms)")
            return True
        else:
            print("  ⚠️  Ping returned DOWN for localhost")
            return False
            
    except Exception as e:
        print(f"  ❌ Ping error: {e}")
        print("  💡 Tip: On Windows, run as Administrator or use subprocess method")
        return False


def test_snmp():
    """Test SNMP functionality (non-critical)"""
    print("\n🔍 Testing SNMP monitor...")
    
    try:
        from src.monitoring.snmp_monitor import SNMPMonitor
        
        snmp = SNMPMonitor()
        print("  ✅ SNMP module loaded (requires SNMP-enabled devices to test fully)")
        return True
            
    except Exception as e:
        print(f"  ❌ SNMP error: {e}")
        return False


def test_config():
    """Test configuration files"""
    print("\n🔍 Testing configuration files...")
    
    import os
    
    files = [
        'config/config.yaml',
        'config/devices.yaml'
    ]
    
    all_ok = True
    for file in files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - NOT FOUND")
            all_ok = False
    
    return all_ok


def main():
    print("="*60)
    print("🧪 Network Monitoring System - Component Test")
    print("="*60)
    print()
    
    tests = [
        ("Package Imports", test_imports),
        ("Configuration Files", test_config),
        ("Database Operations", test_database),
        ("Ping Monitor", test_ping),
        ("SNMP Monitor", test_snmp)
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ {name} test crashed: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name:<30} {status}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed! System is ready to run.")
        print("\nNext step: python run.py")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    print("="*60)


if __name__ == '__main__':
    main()
