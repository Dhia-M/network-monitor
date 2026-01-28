"""
Network Discovery Utility
Scans subnets to find active devices
"""

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
