#!/usr/bin/env python3
"""
Wake-on-LAN magic packet utility.
Sends a magic packet to wake up a machine on the local network.
"""

import socket
import re
import fcntl
import struct
import platform


def validate_mac(mac_address: str) -> bool:
    """
    Validate MAC address format.
    Accepts: AA:BB:CC:DD:EE:FF, AA-BB-CC-DD-EE-FF, AABBCCDDEEFF
    """
    # Remove common separators
    cleaned = re.sub(r'[:\-]', '', mac_address.upper())

    # Check if it's exactly 12 hexadecimal characters
    return bool(re.match(r'^[0-9A-F]{12}$', cleaned))


def normalize_mac(mac_address: str) -> str:
    """
    Normalize MAC address to format AA:BB:CC:DD:EE:FF
    """
    cleaned = re.sub(r'[:\-]', '', mac_address.upper())
    return ':'.join([cleaned[i:i+2] for i in range(0, 12, 2)])


def get_interfaces():
    """
    Get all network interfaces with their IPv4 addresses and broadcast addresses.
    Returns a list of dicts: {'name': name, 'ip': ip, 'broadcast': broadcast}
    """
    interfaces = []
    system = platform.system()

    try:
        if system == "Linux":
            # Linux: use socket.if_nameindex() and ioctl
            for idx, name in socket.if_nameindex():
                if name == 'lo':
                    continue  # Skip loopback
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    # Get IP address
                    info_addr = fcntl.ioctl(
                        s.fileno(),
                        0x8915,  # SIOCGIFADDR
                        struct.pack('256s', name[:15].encode('utf-8'))
                    )
                    ip = socket.inet_ntoa(info_addr[20:24])

                    # Get Netmask
                    try:
                        info_mask = fcntl.ioctl(
                            s.fileno(),
                            0x891b,  # SIOCGIFNETMASK
                            struct.pack('256s', name[:15].encode('utf-8'))
                        )
                        netmask = socket.inet_ntoa(info_mask[20:24])

                        # Calculate broadcast
                        ip_parts = [int(p) for p in ip.split('.')]
                        mask_parts = [int(p) for p in netmask.split('.')]
                        bcast_parts = [str(ip_parts[i] | (255 - mask_parts[i])) for i in range(4)]
                        broadcast = '.'.join(bcast_parts)
                    except:
                        broadcast = '255.255.255.255'

                    interfaces.append({'name': name, 'ip': ip, 'broadcast': broadcast})
                    s.close()
                except (OSError, IOError):
                    pass
        elif system == "Darwin":
            # macOS: parse ifconfig output
            import subprocess
            result = subprocess.run(['ifconfig'], capture_output=True, text=True, check=False)
            current_if = None
            for line in result.stdout.split('\n'):
                if line and not line[0].isspace() and ':' in line:
                    current_if = line.split(':')[0]
                elif current_if and current_if != 'lo0' and line.strip().startswith('inet '):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ip = parts[1]
                        if not ip.startswith('127.') and not ip.startswith('169.254.'):
                            broadcast = '255.255.255.255'
                            # Try to find broadcast in the same line
                            for i in range(len(parts)):
                                if parts[i] == 'broadcast' and i + 1 < len(parts):
                                    broadcast = parts[i+1]
                                    break
                            interfaces.append({'name': current_if, 'ip': ip, 'broadcast': broadcast})
    except Exception as e:
        print(f"Warning: Could not get all interfaces: {e}")

    return interfaces


def create_magic_packet(mac_address: str) -> bytes:
    """
    Create a WOL magic packet.
    """
    mac = normalize_mac(mac_address)
    mac_bytes = bytes.fromhex(mac.replace(':', ''))
    return b'\xff' * 6 + mac_bytes * 16


def send_wol(mac_address: str, broadcast_address: str = '<broadcast>', ports: list = [7, 9]) -> dict:
    """
    Send Wake-on-LAN magic packets through all available network interfaces.
    """
    if not validate_mac(mac_address):
        return {'success': False, 'message': f'Invalid MAC address: {mac_address}'}

    magic_packet = create_magic_packet(mac_address)
    normalized_mac = normalize_mac(mac_address)
    interfaces = get_interfaces()
    successful_attempts = 0
    details = []

    # If no interfaces found, try default
    if not interfaces:
        interfaces = [{'name': 'default', 'ip': '0.0.0.0', 'broadcast': '255.255.255.255'}]

    for iface in interfaces:
        if_name = iface['name']
        if_ip = iface['ip']
        # Use provided broadcast_address if not '<broadcast>', otherwise use interface's broadcast
        bcast_addr = broadcast_address if broadcast_address != '<broadcast>' else iface['broadcast']

        for port in ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

                    # Try to bind to interface (best effort)
                    try:
                        if platform.system() == "Linux":
                            # Try binding to device name first (needs root/CAP_NET_RAW)
                            try:
                                sock.setsockopt(socket.SOL_SOCKET, 25, if_name.encode('utf-8'))
                            except PermissionError:
                                if if_ip != '0.0.0.0':
                                    sock.bind((if_ip, 0))
                        elif if_ip != '0.0.0.0':
                            sock.bind((if_ip, 0))
                    except:
                        pass # Continue even if bind fails

                    # Send packet multiple times for reliability
                    for _ in range(3):
                        sock.sendto(magic_packet, (bcast_addr, port))

                successful_attempts += 1
                details.append(f"Sent via {if_name} ({if_ip}) to {bcast_addr}:{port}")
            except Exception as e:
                details.append(f"Failed via {if_name} to {bcast_addr}:{port}: {e}")

    if successful_attempts > 0:
        return {
            'success': True,
            'message': f'Magic packets sent to {normalized_mac} ({successful_attempts} successful attempts)',
            'details': details
        }
    else:
        return {
            'success': False,
            'message': f'Failed to send magic packets: {"; ".join(details[:3])}...',
            'details': details
        }



if __name__ == '__main__':
    # Test with a dummy MAC address
    test_mac = '00:11:22:33:44:55'
    result = send_wol(test_mac)
    print(f"Result: {result}")
