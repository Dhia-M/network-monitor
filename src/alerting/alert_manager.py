"""
Alert Manager
Coordinates alert notifications across multiple channels
"""

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
