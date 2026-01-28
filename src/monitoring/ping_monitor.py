"""
ICMP Ping Monitor
Performs connectivity checks using ICMP Echo Request/Reply
"""

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
        # ping3 returns response time in seconds, or None/False if unreachable
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
