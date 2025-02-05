import logging
from database.db_connection import get_connection

def store_scan_results(file_name, file_path, file_size, file_modified, file_type):
    """Stores or updates scanned file metadata."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO FileRecords (file_name, file_type, file_path, file_size, file_modified, last_scanned)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(file_path) DO UPDATE SET 
            file_size = excluded.file_size,
            file_modified = excluded.file_modified,
            file_type = excluded.file_type,
            last_scanned = CURRENT_TIMESTAMP
    ''', (file_name, file_type, file_path, file_size, file_modified))

    conn.commit()
    conn.close()
    logging.info(f"Updated metadata for file: {file_name} (Type: {file_type})")

def get_total_file_count():
    """Returns the total number of scanned files."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM FileRecords")
    total = cursor.fetchone()[0]
    conn.close()
    return total
