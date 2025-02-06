import logging
from database.db_connection import get_connection

def get_all_unique_top_folders():
    """Fetches all unique top_folder values from ScanTargets."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT top_folder FROM ScanTargets")
    top_folders = [row[0] for row in cursor.fetchall()]
    conn.close()
    return top_folders

def get_selected_top_folders():
    """Fetches all user-selected top folders from ScanTargets."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT top_folder FROM ScanTargets WHERE status = 'active'")
    top_folders = [row[0] for row in cursor.fetchall()]
    conn.close()
    return top_folders

def add_scan_target(top_folder):
    """Adds a new scan target."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO ScanTargets (top_folder, status) VALUES (?, 'active')", (top_folder,))
        conn.commit()
        logging.info(f"Added scan target: {top_folder}")
    except Exception as e:
        logging.error(f"Failed to add scan target '{top_folder}': {e}")
    finally:
        conn.close()


def update_last_scanned(top_folder):
    """Updates the last scanned timestamp for a top_folder."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE ScanTargets SET last_scanned = CURRENT_TIMESTAMP WHERE top_folder = ?", (top_folder,))
    conn.commit()
    conn.close()
    logging.info(f"Updated last scanned time for '{top_folder}'.")

def delete_scan_target(top_folder):
    """Permanently removes a scan target from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ScanTargets WHERE top_folder = ?", (top_folder,))
    conn.commit()
    conn.close()
    logging.info(f"Deleted scan target from database: {top_folder}")

def activate_scan_target(top_folder):
    """Marks a scan target as 'active' instead of inserting a duplicate."""
    conn = get_connection()
    cursor = conn.cursor()
    
    logging.debug(f"Activating scan target: {top_folder}")  # ✅ Log before update
    cursor.execute("UPDATE ScanTargets SET status = 'active' WHERE top_folder = ?", (top_folder,))
    
    conn.commit()
    conn.close()
    logging.info(f"Scan target '{top_folder}' activated.")

def deactivate_scan_target(top_folder):
    """Marks a scan target as 'inactive' instead of removing it."""
    conn = get_connection()
    cursor = conn.cursor()
    
    logging.debug(f"Deactivating scan target: {top_folder}")  # ✅ Log before update
    cursor.execute("UPDATE ScanTargets SET status = 'inactive' WHERE top_folder = ?", (top_folder,))
    
    conn.commit()
    conn.close()
    logging.info(f"Scan target '{top_folder}' deactivated.")
