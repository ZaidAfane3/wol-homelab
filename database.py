#!/usr/bin/env python3
"""
SQLite database module for storing WOL machines.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os


# Database file path - use /data directory for persistent storage with proper permissions
DB_PATH = '/data/wol.db'


def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with the machines table."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT NOT NULL UNIQUE,
            alias TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_wol TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


def get_all_machines() -> List[Dict]:
    """Get all saved machines."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, mac_address, alias, created_at, last_wol
        FROM machines
        ORDER BY created_at DESC
    ''')

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_machine_by_id(machine_id: int) -> Optional[Dict]:
    """Get a machine by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, mac_address, alias, created_at, last_wol
        FROM machines
        WHERE id = ?
    ''', (machine_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_machine_by_mac(mac_address: str) -> Optional[Dict]:
    """Get a machine by its MAC address."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, mac_address, alias, created_at, last_wol
        FROM machines
        WHERE mac_address = ?
    ''', (mac_address,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def add_machine(mac_address: str, alias: str) -> Dict:
    """
    Add a new machine.

    Returns:
        dict with 'success' (bool), 'message' (str), and optionally 'id' (int)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO machines (mac_address, alias)
            VALUES (?, ?)
        ''', (mac_address, alias))

        conn.commit()
        machine_id = cursor.lastrowid
        conn.close()

        return {
            'success': True,
            'message': f'Machine "{alias}" added successfully',
            'id': machine_id
        }

    except sqlite3.IntegrityError:
        conn.close()
        return {
            'success': False,
            'message': 'A machine with this MAC address already exists'
        }


def update_last_wol(machine_id: int) -> bool:
    """Update the last_wol timestamp for a machine."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE machines
        SET last_wol = ?
        WHERE id = ?
    ''', (datetime.now().isoformat(), machine_id))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return success


def delete_machine(machine_id: int) -> bool:
    """Delete a machine by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM machines WHERE id = ?', (machine_id,))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return success


if __name__ == '__main__':
    # Test database functions
    init_db()
    print("Database initialized at:", DB_PATH)
    print("Machines:", get_all_machines())
