import os
import time
import subprocess
import logging
import json
import sqlite3 
import sys
import database  
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal

# Global Variables
DB_FILE = "plex_quality_crawler.db"  # Define the database file
detailed_scan_running = False

# Configure logging
logging.basicConfig(
    filename="plex_quality_crawler.log",
    level=logging.INFO,  
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def remount_drive(scan_path, smb_server):
    """Attempts to remount the networked SMB drive if it's unmounted."""
    volume_name = scan_path.split("/")[2]  # Extracts the volume name

    # ✅ Ensure smb_server does NOT have "smb://" prefix
    if smb_server.startswith("smb://"):
        smb_server = smb_server.replace("smb://", "")

    smb_share_path = f"smb://{smb_server}/{volume_name}"

    logging.warning(f"Network drive '{volume_name}' appears to be unmounted. Attempting to reconnect...")

    # ✅ Check if already mounted
    if os.path.exists(f"/Volumes/{volume_name}"):
        logging.info(f"Drive '{volume_name}' is already mounted at /Volumes/{volume_name}. No remount needed.")
        return True

    try:
        # ✅ Use `open smb://` instead of `mount_smbfs`
        result = subprocess.run(["open", smb_share_path], capture_output=True, text=True)
        logging.info(f"Executed: open {smb_share_path}")

        # ✅ Give time for remounting
        time.sleep(5)

        # ✅ Check if the share is now mounted
        if os.path.ismount(f"/Volumes/{volume_name}"):
            logging.info(f"SMB share '{smb_share_path}' successfully remounted.")
            return True
        else:
            logging.error(f"Failed to remount SMB share '{smb_share_path}'.")
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
        smb_server = database.get_selected_smb_server()  # Fetch the selected SMB server
        if remount_drive(scan_path, smb_server):

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

# Video Scan
def extract_metadata_ffprobe(file_path):
    """Extracts full metadata from ffprobe for video, audio, and subtitles."""
    command = [
        "ffprobe", "-v", "error", "-show_format", "-show_streams",
        "-of", "json", file_path
    ]
    
    result = subprocess.run(command, capture_output=True, text=True)

    # ✅ Remove full JSON logging, just confirm success/failure
    if result.returncode != 0 or not result.stdout.strip():
        logging.error(f"❌ ffprobe failed for {file_path}: {result.stderr.strip()}")
        return None  

    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError:
        logging.error(f"❌ Failed to parse ffprobe JSON for {file_path}")
        return None  

    if "streams" not in metadata:
        logging.error(f"⚠️ No 'streams' found for {file_path}")
        return None  

    # Extract format-level metadata
    format_info = metadata.get("format", {})

    # ✅ Handle missing video stream safely
    video_stream = next((s for s in metadata["streams"] if s["codec_type"] == "video"), None)

    if video_stream is None:
        logging.warning(f"⚠️ No video stream found for {file_path}. Skipping video metadata.")

    # Extract all audio streams
    audio_streams = [s for s in metadata["streams"] if s["codec_type"] == "audio"]
    audio_languages = [s.get("tags", {}).get("language", "und") for s in audio_streams]
    audio_stream = audio_streams[0] if audio_streams else None  # Pick first audio track

    # Extract subtitle streams
    subtitle_streams = [s for s in metadata["streams"] if s["codec_type"] == "subtitle"]
    subtitle_languages = [s.get("tags", {}).get("language", "und") for s in subtitle_streams]

    return {
        # General File Info
        "file_format": format_info.get("format_name"),
        "duration": float(format_info.get("duration", 0)),
        "probe_score": int(format_info.get("probe_score", 0)),

        # ✅ Video Stream Metadata - Now Safe!
        "video_codec": video_stream.get("codec_name") if video_stream else None,
        "resolution": f"{video_stream.get('width', 'unknown')}x{video_stream.get('height', 'unknown')}" if video_stream else None,
        "frame_rate": video_stream.get("avg_frame_rate") if video_stream else None,
        "video_bitrate": int(video_stream.get("bit_rate", 0)) if video_stream and "bit_rate" in video_stream else None,
        "video_bit_depth": int(video_stream.get("bits_per_raw_sample", 0)) if video_stream and "bits_per_raw_sample" in video_stream else None,
        "color_primaries": video_stream.get("color_primaries") if video_stream else None,
        "color_transfer": video_stream.get("color_transfer") if video_stream else None,

        # Audio Stream Metadata
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
        "audio_channels": int(audio_stream.get("channels", 0)) if audio_stream else None,
        "audio_sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream else None,
        "audio_bitrate": int(audio_stream.get("bit_rate", 0)) if audio_stream and "bit_rate" in audio_stream else None,
        "audio_languages": ", ".join(audio_languages),

        # Subtitle Stream Metadata
        "subtitle_count": len(subtitle_streams),
        "subtitle_languages": ", ".join(subtitle_languages),
    }


def run_detailed_scan():
    """Runs the detailed scan process and marks files as scanned."""
    global detailed_scan_running

    logging.info("🔍 Detailed scan started.")

    video_files = database.get_unscanned_videos()
    total_files = len(video_files)

    if total_files == 0:
        logging.info("✅ No video files need a detailed scan.")
        detailed_scan_running = False
        return

    logging.info(f"🔄 Scanning {total_files} files for metadata.")

    for i, file in enumerate(video_files):
        if file.startswith("._") or file.endswith(".DS_Store"):  # ✅ Skip macOS metadata files
            logging.info(f"⏭️ Skipping macOS metadata file: {file}")
            continue

        logging.info(f"📂 Processing file: {file}")
        
        metadata = extract_metadata_ffprobe(file)
        database.mark_file_as_scanned(file)  
        if metadata is None:
            logging.error(f"❌ Skipping {file} due to failed metadata extraction.")
            continue  # Move to the next file

        # ✅ Store metadata & mark as scanned (only once)
        database.update_video_metadata(file, metadata)

        # ✅ Log progress every 50 files instead of every single file
        if (i + 1) % 50 == 0:
            logging.info(f"📊 Progress: {i+1}/{len(video_files)} files scanned")


    logging.info("✅ Detailed scan completed.")
    detailed_scan_running = False  # ✅ Reset flag after completion


def start_detailed_scan():
    """Starts the detailed scan and ensures UI updates properly."""
    global detailed_scan_running
    if detailed_scan_running:
        QMessageBox.warning(None, "Scan in Progress", "A detailed scan is already running.")
        return
    
    detailed_scan_running = True  # ✅ Set flag to indicate a scan is running
    progress_bar.setValue(0)
    progress_bar.setVisible(True)

    threading.Thread(target=run_detailed_scan, daemon=True).start()
    progress_bar.setVisible(True)  # Show the progress bar

    for i, file in enumerate(video_files):
        metadata = extract_metadata_ffprobe(file)
        database.update_video_metadata(file, metadata)
        update_progress(i + 1, total_files)  # Update UI progress

    logging.info("Detailed scan completed.")
    QMessageBox.information(None, "Scan Complete", "Detailed scan completed successfully.")
    
    progress_bar.setVisible(False)  # Hide the progress bar after completion
    detailed_scan_running = False  # ✅ Reset flag after completion

class ScanThread(QThread):
    progress_signal = pyqtSignal(int, int)  # Emits progress updates

    def run(self):
        total_files = len(database.get_unscanned_videos())
        scanned_files = 0

        for file in database.get_unscanned_videos():
            extract_metadata_ffprobe(file)  # Process the file
            scanned_files += 1
            self.progress_signal.emit(scanned_files, total_files)  # Emit progress update