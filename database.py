import sqlite3
import os
import logging
import time
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
MAX_RETRIES = 5  # Retry 5 times before failing
RETRY_DELAY = 0.5  # Wait 0.5 seconds between retries

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
    """Initializes the database and ensures required tables exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check if the Settings table already has the correct schema
    cursor.execute("PRAGMA table_info(Settings);")
    columns = {row[1] for row in cursor.fetchall()}  # Get column names

    if "key" not in columns or "value" not in columns:
        logging.warning("Updating Settings table to new schema.")

        # Backup old table if it exists
        cursor.execute("ALTER TABLE Settings RENAME TO Settings_backup;")

        # Create new Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL
            )
        ''')

        # Migrate existing scan path if available
        cursor.execute("SELECT scan_path FROM Settings_backup LIMIT 1;")
        existing_path = cursor.fetchone()
        if existing_path:
            cursor.execute("INSERT INTO Settings (key, value) VALUES ('scan_path', ?);", (existing_path[0],))

        # Drop old table
        cursor.execute("DROP TABLE Settings_backup;")

        conn.commit()
        logging.info("Database schema updated successfully.")

    # Ensure ScanTargets table exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ScanTargets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            top_folder TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            last_scanned TIMESTAMP DEFAULT NULL
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
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL
        )
    ''')


    # Store only one scan path at a time (overwrite previous entry)
    cursor.execute("DELETE FROM Settings;")  # Clear old path
    cursor.execute("INSERT INTO Settings (scan_path) VALUES (?)", (scan_path,))

    conn.commit()
    conn.close()

    logging.info(f"Scan path saved: {scan_path}")

def get_total_file_count():
    """Returns the total number of scanned files."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM FileRecords")
    total = cursor.fetchone()[0]
    conn.close()
    return total


def get_selected_smb_server():
    """Fetch the last-selected SMB server from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM Settings WHERE key = 'smb_server'")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None  # Return server or None if not found

def set_selected_smb_server(smb_server):
    """Update or insert the selected SMB server in the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Insert or update
    cursor.execute('''
        INSERT INTO Settings (key, value) VALUES ('smb_server', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (smb_server,))

    conn.commit()
    conn.close()
    logging.info(f"Updated selected SMB server: {smb_server}")


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

def extract_top_folder(file_path):
    """Extracts the first folder after 'Volumes' in a file path."""
    match = re.search(TOP_FOLDER_REGEX, file_path)
    return match.group(1) if match else None
    
def get_all_unique_top_folders():
    """Fetches all unique top_folder values from ScanTargets."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT top_folder FROM ScanTargets")
    top_folders = [row[0] for row in cursor.fetchall()]
    conn.close()
    return top_folders


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

    # Create the ScanTargets table with status and last_scanned
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ScanTargets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            top_folder TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            last_scanned TIMESTAMP DEFAULT NULL
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

    # Add the Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL
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
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL
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

def get_selected_top_folders():
    """Fetches all user-selected top folders from ScanTargets."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT top_folder FROM ScanTargets WHERE status = 'active'")
    top_folders = [row[0] for row in cursor.fetchall()]
    conn.close()
    return top_folders

def add_scan_target(top_folder):
    """Adds a new scan target with retry mechanism to handle database locks."""
    for attempt in range(MAX_RETRIES):
        conn = None
        try:
            conn = sqlite3.connect(DB_FILE, timeout=10)
            cursor = conn.cursor()

            logging.info(f"Attempting to add scan target: {top_folder} (Attempt {attempt + 1})")

            # Insert or fail (so we can catch errors properly)
            cursor.execute("INSERT INTO ScanTargets (top_folder, status) VALUES (?, 'active')", (top_folder,))
            conn.commit()

            # Verify if it was added
            cursor.execute("SELECT id FROM ScanTargets WHERE top_folder = ?", (top_folder,))
            result = cursor.fetchone()

            if result:
                logging.info(f"Scan target '{top_folder}' successfully added with ID {result[0]}.")
                return  # ✅ Success, exit function
            else:
                logging.error(f"Scan target '{top_folder}' was NOT added despite INSERT (unexpected behavior).")
                return

        except sqlite3.IntegrityError as e:
            logging.error(f"Constraint violation when adding scan target '{top_folder}': {e}")
            return  # No point retrying a duplicate insertion

        except sqlite3.OperationalError as e:
            error_message = str(e).lower()

            if "database is locked" in error_message:
                logging.warning(f"Database is locked, retrying... ({attempt + 1}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY)
            else:
                logging.error(f"OperationalError (NOT a lock issue) when adding scan target '{top_folder}': {e}")
                return  # Don't retry non-lock-related operational errors

        except Exception as e:
            logging.error(f"Unexpected error when adding scan target '{top_folder}': {e}")
            return

        finally:
            if conn:
                conn.close()

    logging.error(f"Failed to add scan target '{top_folder}' after {MAX_RETRIES} attempts due to persistent database lock.")


def remove_scan_target(top_folder):
    """Marks a scan target as 'inactive' instead of deleting it."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE ScanTargets SET status = 'inactive' WHERE top_folder = ?", (top_folder,))
    conn.commit()
    conn.close()

def update_last_scanned(top_folder):
    """Updates the last scanned timestamp for a top_folder."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE ScanTargets SET last_scanned = CURRENT_TIMESTAMP WHERE top_folder = ?", (top_folder,))
    conn.commit()
    conn.close()

def delete_scan_target(top_folder):
    """Permanently removes a scan target from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ScanTargets WHERE top_folder = ?", (top_folder,))
    conn.commit()
    conn.close()
    logging.info(f"Deleted scan target from database: {top_folder}")

def activate_scan_target(top_folder):
    """Marks a scan target as 'active' instead of inserting a duplicate."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE ScanTargets SET status = 'active' WHERE top_folder = ?", (top_folder,))
        conn.commit()
        logging.info(f"Scan target '{top_folder}' activated.")

def deactivate_scan_target(top_folder):
    """Marks a scan target as 'inactive' instead of removing it."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE ScanTargets SET status = 'inactive' WHERE top_folder = ?", (top_folder,))
        conn.commit()
        logging.info(f"Scan target '{top_folder}' deactivated.")
