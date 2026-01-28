"""
Email Notifier
Sends alert notifications via SMTP email
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict


class EmailNotifier:
    """Send email alerts via SMTP"""
    
    def __init__(self, config: Dict):
        self.smtp_server = config['smtp_server']
        self.smtp_port = config['smtp_port']
        self.use_tls = config['use_tls']
        self.username = config['username']
        self.password = config['password']
        self.from_address = config['from_address']
        self.recipients = config['recipients']
    
    def send(self, device: Dict, alert_type: str, message: str):
        """Send email alert"""
        
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[Network Monitor] {alert_type}: {device['name']}"
        msg['From'] = self.from_address
        msg['To'] = ', '.join(self.recipients)
        
        # HTML body
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2 style="color: {'#d32f2f' if alert_type == 'DOWN' else '#388e3c'};">
              {alert_type} Alert
            </h2>
            <table style="border-collapse: collapse; width: 100%;">
              <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Device:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{device['name']}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>IP Address:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{device['ip_address']}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Type:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{device.get('device_type', 'Unknown')}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Status:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{alert_type}</td>
              </tr>
              <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Time:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
              </tr>
            </table>
            <p style="margin-top: 20px;">{message}</p>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        # Send email
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            print(f"✉️  Email sent to {', '.join(self.recipients)}")
        except Exception as e:
            print(f"❌ Email send failed: {e}")
