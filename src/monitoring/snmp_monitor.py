"""
SNMP Monitor
Collects performance metrics from SNMP-enabled devices
"""

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
                # SNMP error - device may not support SNMP
                return None
            elif errorStatus:
                # SNMP protocol error
                return None
            else:
                # Extract value from result
                for varBind in varBinds:
                    return int(varBind[1])
                    
        except Exception as e:
            # Connection timeout or other error
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
