"""
Telegram Notifier
Sends alert notifications via Telegram Bot API
"""

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
                print(f"⚠️  Telegram send failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Telegram error: {e}")
