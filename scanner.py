import os
import time
import subprocess
import logging
import sqlite3 
import sys
import database  
import shlex 

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

# Remounts failed scans
def remount_drive(scan_path):
    """Attempts to remount the networked SMB drive if it's unmounted."""
    
    # Extract the volume name
    volume_name = scan_path.split("/")[2]  # ✅ Extracts the SMB share name
    smb_share_path = f"smb://{volume_name}"  # ✅ Construct SMB path

    logging.warning(f"Network drive '{volume_name}' appears to be unmounted. Attempting to reconnect...")

    try:
        # ✅ Use `open` to mount the SMB share
        result = subprocess.run(["open", shlex.quote(smb_share_path)], capture_output=True, text=True)

        # ✅ Give some time for the mount to complete
        time.sleep(5)

        # ✅ Check if the share is now mounted
        if os.path.exists(scan_path):
            logging.info(f"SMB share '{volume_name}' successfully reconnected.")
            return True
        else:
            logging.error(f"Failed to mount SMB share '{smb_share_path}'. Drive still not found.")
            return False

    except Exception as e:
        logging.error(f"Error while attempting to mount SMB share '{smb_share_path}': {str(e)}")
        return False

# Scans the SMB directory and collects metadata only for new or modified files.
def scan_directory(scan_path):
    """Scans the directory and collects metadata, attempting to remount if necessary."""
    
    if not os.path.exists(scan_path):
        logging.error(f"Scan failed: Directory '{scan_path}' not found.")

        # ✅ Attempt to remount if missing
        if remount_drive(scan_path):
            logging.info(f"Retrying scan after remount: {scan_path}")
            time.sleep(5)  # ✅ Give time for remounting
            
            # ✅ Check if the drive is now available
            if not os.path.exists(scan_path):  
                logging.error(f"Directory '{scan_path}' still not found after remount attempt.")
                return []
        else:
            return []  # ✅ Skip scanning if remount fails

    scanned_files = []
    for root, _, files in os.walk(scan_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            file_modified = time.ctime(os.path.getmtime(file_path))
            file_type = os.path.splitext(file)[1].lower() if os.path.splitext(file)[1] else "unknown"

            logging.info(f"Scanned file: {file}, Path: {file_path}, Size: {file_size}, Modified: {file_modified}, Type: {file_type}")

            scanned_files.append((file, file_path, file_size, file_modified, file_type))

    logging.info(f"Final scanned files list: {len(scanned_files)} files found.")
    return scanned_files

# MAIN EXECUTION 
if __name__ == "__main__":
    selected_folders = database.get_selected_top_folders()  # Fetch active scan targets
    logging.info(f"Fetched scan targets: {selected_folders}")

    if not selected_folders:
        logging.info("No active scan targets found. Exiting scanner.")
        sys.exit(0)  # Exit if no folders are selected

    for folder in selected_folders:
        scan_path = f"/Volumes/{folder}/"  # Convert top_folder to full path
        logging.info(f"Scanning: {folder}")

        scanned_files = scan_directory(scan_path)  # Perform scan

        if scanned_files:
            for file, file_path, file_size, file_modified, file_type in scanned_files:
                database.store_scan_results(file, file_path, file_size, file_modified, file_type)

        database.update_last_scanned(folder)  # Update last scanned timestamp
        time.sleep(1)  # Small delay

    logging.info("Scanning completed. Exiting scanner.")

