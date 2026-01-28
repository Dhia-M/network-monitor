"""
API Routes
REST API endpoints for the monitoring dashboard
"""

from flask import render_template, jsonify, request
from src.api.app import app
from src.database.db_manager import DatabaseManager

db = DatabaseManager()


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get current status of all devices"""
    devices = db.get_all_devices()
    
    # Format for JSON response
    return jsonify({
        'devices': devices,
        'summary': {
            'total': len(devices),
            'up': len([d for d in devices if d.get('status') == 'UP']),
            'down': len([d for d in devices if d.get('status') == 'DOWN'])
        }
    })


@app.route('/api/devices')
def api_devices():
    """List all devices"""
    devices = db.get_all_devices()
    return jsonify(devices)


@app.route('/api/devices/<int:device_id>')
def api_device_detail(device_id):
    """Get detailed info for a specific device"""
    device = db.get_device_by_id(device_id)
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Get performance metrics
    metrics = db.get_device_metrics(device_id, limit=20)
    
    return jsonify({
        'device': device,
        'metrics': metrics
    })


@app.route('/api/devices', methods=['POST'])
def api_add_device():
    """Add a new device"""
    data = request.json
    
    device_id = db.add_device(
        name=data['name'],
        ip=data['ip'],
        device_type=data.get('type', 'unknown'),
        snmp_enabled=data.get('snmp_enabled', False),
        snmp_community=data.get('snmp_community', 'public')
    )
    
    if device_id:
        return jsonify({'success': True, 'device_id': device_id})
    else:
        return jsonify({'error': 'Device already exists'}), 400


@app.route('/api/devices/<int:device_id>', methods=['DELETE'])
def api_delete_device(device_id):
    """Remove a device"""
    db.delete_device(device_id)
    return jsonify({'success': True})


@app.route('/api/logs')
def api_logs():
    """Get recent logs"""
    logs = db.get_recent_logs(limit=50)
    return jsonify(logs)


@app.route('/api/alerts')
def api_alerts():
    """Get recent alerts"""
    alerts = db.get_recent_alerts(limit=20)
    return jsonify(alerts)
