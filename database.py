import sqlite3
import os
import logging
# Configure logging
logging.basicConfig(
    filename="plex_quality_crawler.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


DB_FILE = "plex_quality_crawler.db"

def initialize_database():
    #Initializes the database if it doesn't exist and ensures required tables are created.
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create the ScanQueue table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ScanQueue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
def add_scan_request():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("INSERT INTO ScanQueue (status) VALUES ('pending')")

    conn.commit()
    conn.close()

    logging.info("New scan request added.")

def get_pending_scans():

    #Retrieves all pending scan requests from the database.
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM ScanQueue WHERE status = 'pending'")
    pending_scans = cursor.fetchall()  # Get all pending scan jobs

    conn.close()
    return pending_scans

#Fetches metadata for a specific file from the database.
def get_file_metadata(file_path):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT file_name, file_type, file_size, file_modified, file_path, last_scanned FROM FileRecords WHERE file_path = ?", (file_path,))
    result = cursor.fetchone()

    conn.close()
    return result  # Returns a tuple if file exists, otherwise None



def update_scan_status(scan_id, new_status):
    #Updates the status of a scan request in the database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE ScanQueue SET status = ? WHERE id = ?", (new_status, scan_id))
    conn.commit()
    conn.close()

    logging.info(f"Scan ID {scan_id} status updated to {new_status}.")

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
