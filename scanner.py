import os
import time
import logging
import sqlite3 
import database  

DB_FILE = "plex_quality_crawler.db"  # Define the database file

# Configure logging
logging.basicConfig(
    filename="plex_quality_crawler.log",
    level=logging.INFO,  
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Fetches all pending scans from the database.
def fetch_pending_scans():
    pending_scans = database.get_pending_scans()
    print(f"DEBUG: Pending Scans Retrieved -> {pending_scans}")  # 🔍 Debugging step

    if not pending_scans:
        logging.info("No pending scans found.")
        return []

    logging.info(f"Found {len(pending_scans)} pending scan(s).")
    return pending_scans  # Ensure function returns a list of tuples (scan_id, scan_path)

# Updates a scan request's status to 'in_progress'
def mark_scan_in_progress(scan_id):
    database.update_scan_status(scan_id, "in_progress")
    logging.info(f"Scan ID {scan_id} marked as 'in_progress'.")

# Scans the SMB directory and collects metadata only for new or modified files.
def scan_directory(scan_path):
    """Scans the directory and collects metadata."""
    if not os.path.exists(scan_path):
        logging.error(f"Scan failed: Directory '{scan_path}' not found.")
        return []

    scanned_files = []
    for root, _, files in os.walk(scan_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            file_modified = time.ctime(os.path.getmtime(file_path))
            file_type = os.path.splitext(file)[1].lower() if os.path.splitext(file)[1] else "unknown"

            # Debugging print before appending to the list
            logging.debug(f"Scanned file details: {file}, {file_path}, {file_size}, {file_modified}, {file_type}")
            print(f"DEBUG: {file}, {file_path}, {file_size}, {file_modified}, {file_type}")

            scanned_files.append((file, file_path, file_size, file_modified, file_type))

    logging.debug(f"Final scanned files list: {scanned_files}")
    return scanned_files

# MAIN EXECUTION LOOP
if __name__ == "__main__":
    while True:
        pending_scans = fetch_pending_scans()

        if not pending_scans:
            logging.info("No more pending scans. Scanner is now idle.")
            break  # Exit the loop if there are no pending scans

        for scan in pending_scans:
            if len(scan) < 2:
                logging.error(f"Invalid scan entry found in ScanQueue: {scan}")
                continue  # Skip this entry

            scan_id, scan_path = scan  # Extract scan ID and scan path
            
            try:
                mark_scan_in_progress(scan_id)
                logging.info(f"Processing scan ID: {scan_id} with path {scan_path}")

                scanned_files = scan_directory(scan_path)
                
                if not all(len(entry) == 5 for entry in scanned_files):
                    logging.error(f"Invalid tuple structure detected in scan ID {scan_id}: {scanned_files}")
                    raise ValueError("Scanned files contain invalid tuples")

                for file, file_path, file_size, file_modified, file_type in scanned_files:
                    database.store_scan_results(file, file_path, file_size, file_modified, file_type)

                database.mark_deleted_files()
                database.update_scan_status(scan_id, "completed")
                logging.info(f"Scan ID {scan_id} completed.")

            except Exception as e:
                logging.error(f"Error processing scan ID {scan_id}: {str(e)}")
                database.update_scan_status(scan_id, "failed")
                logging.info(f"Scan ID {scan_id} marked as failed.")
