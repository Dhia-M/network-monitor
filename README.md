# Network Monitoring & Alert System

A centralized network monitoring tool that continuously monitors device availability and performance, detects connectivity issues in real time, generates alerts, and presents device status through a modern web-based dashboard.

## 🎯 Features

- **Real-time Monitoring**: ICMP ping checks every 30 seconds
- **SNMP Metrics Collection**: CPU, memory, and uptime tracking
- **Intelligent Alerting**: Email and Telegram notifications
- **Web Dashboard**: Modern, responsive interface with auto-refresh
- **Network Discovery**: Auto-scan subnets to find devices
- **Historical Tracking**: Logs and metrics database
- **False Positive Prevention**: Consecutive failure threshold

## 📋 Prerequisites

- Python 3.8 or higher
- Network access to devices you want to monitor
- (Optional) SNMP-enabled devices for performance metrics
- (Optional) SMTP credentials for email alerts
- (Optional) Telegram bot for instant notifications

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Your Setup

Edit `config/config.yaml` to set:
- Monitoring intervals
- Alert thresholds
- Email SMTP settings (if using email alerts)
- Telegram bot credentials (if using Telegram)

Edit `config/devices.yaml` to add your network devices.

### 3. Run the System

```bash
python run.py
```

The system will:
- Initialize the database
- Load devices from config
- Start monitoring in the background
- Launch web dashboard on **http://localhost:5000**

## 📁 Project Structure

```
network-monitoring/
├── config/
│   ├── config.yaml          # System configuration
│   └── devices.yaml         # Device definitions
├── src/
│   ├── database/           # Database operations
│   ├── monitoring/         # Ping & SNMP monitors
│   ├── alerting/           # Email & Telegram notifications
│   ├── api/                # Flask web server
│   └── utils/              # Discovery & logging
├── static/                 # CSS & JavaScript
├── templates/              # HTML templates
├── data/                   # SQLite database (auto-created)
├── logs/                   # Application logs (auto-created)
├── run.py                  # Main entry point
└── requirements.txt        # Python dependencies
```

## ⚙️ Configuration

### Monitoring Settings

```yaml
monitoring:
  poll_interval: 30          # Seconds between checks
  consecutive_failures: 3    # Failures before alerting
  ping_timeout: 2           # Ping timeout in seconds
```

### Adding Devices

In `config/devices.yaml`:

```yaml
devices:
  - name: "Main Router"
    ip: "192.168.1.1"
    type: "router"
    snmp_enabled: true
    snmp_community: "public"
```

### Email Alerts

In `config/config.yaml`:

```yaml
alerting:
  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "your-email@gmail.com"
    password: "your-app-password"
    recipients:
      - "admin@example.com"
```

**Gmail Setup:**
1. Enable 2-Factor Authentication
2. Generate App Password (Google Account → Security)
3. Use App Password (not your regular password)

### Telegram Alerts

1. Create bot via [@BotFather](https://t.me/BotFather)
2. Get bot token
3. Start chat with your bot
4. Get chat ID from `https://api.telegram.org/bot<TOKEN>/getUpdates`

```yaml
alerting:
  telegram:
    enabled: true
    bot_token: "YOUR_BOT_TOKEN"
    chat_id: "YOUR_CHAT_ID"
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/api/status` | GET | Device status summary |
| `/api/devices` | GET | List all devices |
| `/api/devices/<id>` | GET | Device details & metrics |
| `/api/devices` | POST | Add new device |
| `/api/devices/<id>` | DELETE | Remove device |
| `/api/logs` | GET | Recent event logs |
| `/api/alerts` | GET | Recent alerts |

## 🌐 Network Discovery

Scan your network to auto-discover devices:

```python
from src.database.db_manager import DatabaseManager
from src.utils.discovery import discover_and_add_devices

db = DatabaseManager()
discover_and_add_devices("192.168.1.0/24", db)
```

## 🐛 Troubleshooting

### Ping Permission Issues (Windows)

Run terminal as Administrator, or modify `ping_monitor.py` to use `subprocess` instead of `ping3`.

### SNMP Not Working

1. Enable SNMP on your devices
2. Verify community string matches
3. Allow UDP port 161 in firewall

### Dashboard Not Loading

1. Check if server is running on port 5000
2. Visit `http://localhost:5000/api/status` to test API
3. Check browser console (F12) for errors

## 📊 Dashboard Features

- **Summary Statistics**: Total, online, and offline devices
- **Device Cards**: Real-time status with response times
- **Auto-Refresh**: Updates every 10 seconds
- **Responsive Design**: Works on desktop and mobile
- **Modern UI**: Dark theme with glassmorphism effects

## 🔒 Security Notes

- SNMP uses read-only community strings
- Database stored locally (not exposed)
- Email credentials in config file (keep secure)
- No authentication on dashboard (add if deploying publicly)

## 📈 Future Enhancements

- [ ] Performance charts with Chart.js
- [ ] User authentication system
- [ ] Custom alert rules per device
- [ ] Export reports (PDF, CSV)
- [ ] Bandwidth monitoring
- [ ] Docker containerization
- [ ] Multi-user support

## 📚 Technologies Used

- **Backend**: Python 3, Flask
- **Database**: SQLite
- **Monitoring**: ping3, pysnmp
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Protocols**: ICMP, SNMP v2c, HTTP

## 📝 License

This project is created for educational and portfolio purposes.

## 🤝 Contributing

This is a portfolio project, but suggestions and improvements are welcome!

---

**Built for demonstrating networking, automation, and full-stack development skills.**
