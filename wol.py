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
    Get all network interfaces with their IPv4 addresses.
    Returns a list of tuples: (interface_name, ip_address)
    """
    interfaces = []
    system = platform.system()

    try:
        if system == "Linux":
            # Linux: use socket.if_nameindex()
            for idx, name in socket.if_nameindex():
                if name == 'lo':
                    continue  # Skip loopback
                try:
                    # Get interface address using SIOCGIFADDR
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    info = fcntl.ioctl(
                        s.fileno(),
                        0x8915,  # SIOCGIFADDR
                        struct.pack('256s', name[:15].encode('utf-8'))
                    )
                    ip = socket.inet_ntoa(info[20:24])
                    interfaces.append((name, ip))
                    s.close()
                except (OSError, IOError):
                    pass
        elif system == "Darwin":
            # macOS: parse ifconfig output
            import subprocess
            result = subprocess.run(
                ['ifconfig'],
                capture_output=True,
                text=True,
                check=False
            )
            current_if = None
            for line in result.stdout.split('\n'):
                # Interface definition lines start at column 0 (no leading whitespace)
                # and contain a colon followed by flags
                if line and not line[0].isspace() and ':' in line:
                    # Extract interface name (before the first colon)
                    current_if = line.split(':')[0]
                # Look for inet (IPv4) lines - they are indented with tabs
                elif current_if and current_if != 'lo0' and line.strip().startswith('inet '):
                    stripped = line.strip()
                    # Make sure it's "inet " not "inet6"
                    if stripped.startswith('inet ') and not stripped.startswith('inet6 '):
                        parts = stripped.split()
                        if len(parts) >= 2:
                            ip = parts[1]
                            # Skip loopback and link-local addresses
                            if not ip.startswith('127.') and not ip.startswith('169.254.'):
                                interfaces.append((current_if, ip))
    except Exception as e:
        print(f"Warning: Could not get all interfaces: {e}")

    # Fallback: if no interfaces found, include default (no binding)
    if not interfaces:
        print("Warning: Could not enumerate interfaces, using default")

    return interfaces


def create_magic_packet(mac_address: str) -> bytes:
    """
    Create a WOL magic packet.
    A magic packet is a broadcast frame containing:
    - 6 bytes of FF (255)
    - The target MAC address repeated 16 times
    """
    # Normalize MAC address
    mac = normalize_mac(mac_address)

    # Convert MAC to bytes
    mac_bytes = bytes.fromhex(mac.replace(':', ''))

    # Create the magic packet: 6 x 0xFF + 16 x MAC address
    magic_packet = b'\xff' * 6 + mac_bytes * 16

    return magic_packet


def send_wol(mac_address: str, broadcast_address: str = '<broadcast>', port: int = 9) -> dict:
    """
    Send a Wake-on-LAN magic packet through all available network interfaces.

    Args:
        mac_address: Target machine's MAC address
        broadcast_address: Broadcast IP (default: <broadcast> for system default)
        port: UDP port to send to (default: 9, also common: 7)

    Returns:
        dict with 'success' (bool) and 'message' (str)
    """
    # Validate MAC address
    if not validate_mac(mac_address):
        return {
            'success': False,
            'message': f'Invalid MAC address format: {mac_address}'
        }

    # Create the magic packet
    magic_packet = create_magic_packet(mac_address)
    normalized_mac = normalize_mac(mac_address)

    # Get all network interfaces
    interfaces = get_interfaces()

    successful_sends = []
    failed_sends = []
    system = platform.system()

    # Send through each interface
    for if_name, if_ip in interfaces:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # Bind to specific interface
            if system == "Linux":
                # Linux: use SO_BINDTODEVICE
                try:
                    sock.setsockopt(socket.SOL_SOCKET, 25, if_name.encode('utf-8'))
                except PermissionError:
                    # SO_BINDTODEVICE requires CAP_NET_RAW or root
                    # Fall back to binding to the interface IP
                    sock.bind((if_ip, 0))
            elif system == "Darwin":
                # macOS: bind to the interface IP
                sock.bind((if_ip, 0))
            else:
                # Other systems: try binding to IP
                sock.bind((if_ip, 0))

            # Determine broadcast address
            bcast_addr = broadcast_address
            if broadcast_address == '<broadcast>':
                bcast_addr = '255.255.255.255'

            # Send magic packet
            sock.sendto(magic_packet, (bcast_addr, port))
            successful_sends.append(f"{if_name} ({if_ip})")
            sock.close()

        except Exception as e:
            failed_sends.append(f"{if_name} ({if_ip}): {str(e)}")

    # Also try sending without binding (system default routing)
    if not interfaces or True:  # Always try default as fallback
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                bcast_addr = '255.255.255.255' if broadcast_address == '<broadcast>' else broadcast_address
                sock.sendto(magic_packet, (bcast_addr, port))
            if not successful_sends:
                successful_sends.append("default interface")
        except Exception as e:
            if not successful_sends:
                failed_sends.append(f"default interface: {str(e)}")

    # Build result message
    if successful_sends:
        # For web UI: use simple message, put details in extra fields
        count = len(successful_sends)
        msg = f'Magic packet sent to {normalized_mac} via {count} interface{"s" if count > 1 else ""}'
        return {
            'success': True,
            'message': msg,
            'interfaces': successful_sends,
            'failed': failed_sends
        }
    else:
        return {
            'success': False,
            'message': f'Failed to send magic packet: {"; ".join(failed_sends)}'
        }


if __name__ == '__main__':
    # Test with a dummy MAC address
    test_mac = '00:11:22:33:44:55'
    result = send_wol(test_mac)
    print(f"Result: {result}")
