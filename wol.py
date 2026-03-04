#!/usr/bin/env python3
"""
Wake-on-LAN magic packet utility.
Sends a magic packet to wake up a machine on the local network.
"""

import socket
import re


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


def send_wol(mac_address: str, broadcast_address: str = '255.255.255.255', port: int = 9) -> dict:
    """
    Send a Wake-on-LAN magic packet.

    Args:
        mac_address: Target machine's MAC address
        broadcast_address: Broadcast IP (default: 255.255.255.255)
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

    try:
        # Create the magic packet
        magic_packet = create_magic_packet(mac_address)

        # Create UDP socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # Enable broadcast
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            # Send magic packet
            sock.sendto(magic_packet, (broadcast_address, port))

        normalized_mac = normalize_mac(mac_address)
        return {
            'success': True,
            'message': f'Magic packet sent to {normalized_mac}'
        }

    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to send magic packet: {str(e)}'
        }


if __name__ == '__main__':
    # Test with a dummy MAC address
    test_mac = '00:11:22:33:44:55'
    result = send_wol(test_mac)
    print(f"Result: {result}")
