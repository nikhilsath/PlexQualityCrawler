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

            # Logging scan details at INFO level
            logging.info(f"Scanned file: {file}, Path: {file_path}, Size: {file_size}, Modified: {file_modified}, Type: {file_type}")

            scanned_files.append((file, file_path, file_size, file_modified, file_type))

    logging.info(f"Final scanned files list: {scanned_files}")
    return scanned_files

# MAIN EXECUTION 
if __name__ == "__main__":
    selected_folders = database.get_selected_top_folders()  # Fetch active scan targets
    logging.info(f"Fetched scan targets: {selected_folders}")

    if not selected_folders:
        logging.info("No active scan targets found. Exiting scanner.")
        sys.exit(0)  # Exit if no folders are selected

    for folder in selected_folders:
        scan_path = f"/Volumes/{folder}"  # Convert top_folder to full path
        logging.info(f"Scanning: {folder}")

        scanned_files = scan_directory(scan_path)  # Perform scan

        if scanned_files:
            for file, file_path, file_size, file_modified, file_type in scanned_files:
                database.store_scan_results(file, file_path, file_size, file_modified, file_type)

        database.update_last_scanned(folder)  # Update last scanned timestamp
        time.sleep(1)  # Small delay

    logging.info("Scanning completed. Exiting scanner.")

