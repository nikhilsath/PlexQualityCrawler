import logging
from database.db_connection import get_connection

def get_selected_smb_server():
    """Fetch the last-selected SMB server from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM Settings WHERE key = 'smb_server'")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_selected_smb_server(smb_server):
    """Update or insert the selected SMB server in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Settings (key, value) VALUES ('smb_server', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (smb_server,))
    conn.commit()
    conn.close()
    logging.info(f"Updated selected SMB server: {smb_server}")
