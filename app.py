#!/usr/bin/env python3
"""
Wake-on-LAN Flask Web Application.
A simple web interface for sending WOL magic packets to machines on your network.
"""

from flask import Flask, render_template, request, jsonify
from database import init_db, get_all_machines, get_machine_by_id, add_machine, delete_machine, update_last_wol
from wol import send_wol, validate_mac, normalize_mac
import os

app = Flask(__name__)

# Initialize database on startup
init_db()


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/machines', methods=['GET'])
def api_get_machines():
    """Get all saved machines."""
    machines = get_all_machines()
    return jsonify(machines)


@app.route('/api/machines', methods=['POST'])
def api_add_machine():
    """Add a new machine."""
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    mac_address = data.get('mac_address', '').strip()
    alias = data.get('alias', '').strip()

    # Validate inputs
    if not mac_address or not alias:
        return jsonify({'success': False, 'message': 'MAC address and alias are required'}), 400

    # Validate MAC format
    if not validate_mac(mac_address):
        return jsonify({'success': False, 'message': 'Invalid MAC address format'}), 400

    # Normalize MAC address
    mac_address = normalize_mac(mac_address)

    # Add to database
    result = add_machine(mac_address, alias)

    if result['success']:
        # Also send WOL packet when adding a new machine
        wol_result = send_wol(mac_address)
        return jsonify({
            'success': True,
            'message': f'Machine "{alias}" added. {wol_result["message"]}',
            'id': result['id'],
            'wol_sent': wol_result['success']
        }), 201

    return jsonify(result), 400


@app.route('/api/wol/<int:machine_id>', methods=['POST'])
def api_send_wol(machine_id):
    """Send a WOL packet to a specific machine."""
    machine = get_machine_by_id(machine_id)

    if not machine:
        return jsonify({'success': False, 'message': 'Machine not found'}), 404

    # Send WOL packet
    result = send_wol(machine['mac_address'])

    # Update last_wol timestamp if successful
    if result['success']:
        update_last_wol(machine_id)

    return jsonify(result)


@app.route('/api/machines/<int:machine_id>', methods=['DELETE'])
def api_delete_machine(machine_id):
    """Delete a machine."""
    success = delete_machine(machine_id)

    if success:
        return jsonify({'success': True, 'message': 'Machine deleted successfully'})

    return jsonify({'success': False, 'message': 'Machine not found'}), 404


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'success': False, 'message': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'success': False, 'message': 'Internal server error'}), 500


if __name__ == '__main__':
    # Run on all interfaces so it's accessible from other devices on the network
    app.run(host='0.0.0.0', port=5001, debug=True)
