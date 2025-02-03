import sqlite3
import os
import logging
import re


# Configure logging
logging.basicConfig(
    filename="plex_quality_crawler.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Variables
DB_FILE = "plex_quality_crawler.db"
TOP_FOLDER_REGEX = r"/Volumes/([^/]+)"

#enables wal mode for concurrency
def enable_wal_mode():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        conn.commit()
        conn.close()
        logging.info("WAL mode enabled successfully.")
    except sqlite3.OperationalError as e:
        logging.error(f"Failed to enable WAL mode: {e}")


enable_wal_mode() 


def initialize_database():
    #Initializes the database if it doesn't exist and ensures required tables are created.
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create the ScanQueue table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ScanQueue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_path TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create the FileRecords table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS FileRecords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_type TEXT,
            file_path TEXT NOT NULL UNIQUE,
            file_size INTEGER,
            file_modified TEXT,
            last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            top_folder TEXT  -- New column
        )
    ''')

    conn.commit()
    conn.close()
    logging.info("Database initialized successfully.")

#Saves the selected scan path in the database.
def save_scan_path(scan_path):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_path TEXT NOT NULL
        )
    ''')

    # Store only one scan path at a time (overwrite previous entry)
    cursor.execute("DELETE FROM Settings;")  # Clear old path
    cursor.execute("INSERT INTO Settings (scan_path) VALUES (?)", (scan_path,))

    conn.commit()
    conn.close()

    logging.info(f"Scan path saved: {scan_path}")

def mark_deleted_files():
    #Marks files as deleted if they are no longer found in the scanned directory
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM FileRecords")
    all_files = cursor.fetchall()

    for (file_path,) in all_files:
        if not os.path.exists(file_path):  # File no longer exists
            cursor.execute("DELETE FROM FileRecords WHERE file_path = ?", (file_path,))
            logging.info(f"File removed from database (no longer exists): {file_path}")

    conn.commit()
    conn.close()

#Inserts a new scan request into the queue.
def add_scan_request(scan_path):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("INSERT INTO ScanQueue (scan_path, status, created_at) VALUES (?, 'pending', datetime('now'))", (scan_path,))

    conn.commit()
    conn.close()

    logging.info(f"Scan request added for path: {scan_path}")

def get_pending_scans():
    #Retrieves all pending scan requests from the database.
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id, scan_path FROM ScanQueue WHERE status='pending'")
    pending_scans = cursor.fetchall()  # Get all pending scan jobs

    conn.close()
    return pending_scans

def update_scan_status(scan_id, new_status):
    #Updates the status of a scan request in the database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE ScanQueue SET status = ? WHERE id = ?", (new_status, scan_id))
    conn.commit()
    conn.close()

    logging.info(f"Scan ID {scan_id} status updated to {new_status}.")
    
def extract_top_folder(file_path):
    """Extracts the first folder after 'Volumes' in a file path."""
    match = re.search(TOP_FOLDER_REGEX, file_path)
    return match.group(1) if match else None

def update_top_folders():
    """Updates 'top_folder' for all files in FileRecords where it is NULL."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Fetch files where top_folder is NULL
    cursor.execute("SELECT id, file_path FROM FileRecords WHERE top_folder IS NULL")
    rows = cursor.fetchall()

    batch = [(extract_top_folder(file_path), file_id) for file_id, file_path in rows if extract_top_folder(file_path)]

    if batch:
        cursor.executemany("UPDATE FileRecords SET top_folder = ? WHERE id = ?", batch)
        conn.commit()
        logging.info(f"Updated top_folder for {len(batch)} files.")

    conn.close()
if __name__ == "__main__":
    initialize_database()

def store_scan_results(file_name, file_path, file_size, file_modified, file_type):
    """Stores or updates scanned file metadata in the database."""
    conn = sqlite3.connect(DB_FILE)
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

def get_all_files():
    """Fetch all scanned files from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT file_name, file_type, file_size, file_modified FROM FileRecords")
    files = cursor.fetchall()

    conn.close()
    return files

def get_filtered_files(query):
    """Fetch files using a custom query."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(query)
    files = cursor.fetchall()

    conn.close()
    return files
