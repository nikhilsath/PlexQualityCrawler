# Plex Quality Crawler

## Project Overview

Plex Quality Crawler is a Python-based tool that scans directories for all files and gathers metadata on video files. It provides an organized way to track media content by extracting relevant details while leaving other file types untouched.

## Project Structure

```
PlexQualityCrawler/
│── database/               # Database-related modules
│   │── __init__.py         # Package initializer
│   │── database.py         # Main entry point for database functions
│   │── db_connection.py    # Manages database connections
│   │── schema.py           # Handles database initialization & validation
│   │── scan_targets.py     # Manages scan target queries
│   │── file_records.py     # Handles file metadata storage & retrieval
│   │── settings.py         # Manages app settings (e.g., SMB server)
│
│── scanner.py              # Scans selected folders and updates metadata
│── ui.py                   # User interface for managing scan targets & settings
│── requirements.txt        # Python dependencies
│── plex_quality_crawler.db # SQLite database (created automatically)
│── README.txt              # Project documentation
```

## Function Descriptions

### **Scanner Functions (`scanner.py`)**

#### `run()` (scanner.py)
- This function is currently under review and may be legacy code.
- Testing is required to determine if it is still needed.

#### `run_detailed_scan()`
- Runs a detailed scan for video files.
- Retrieves unscanned videos from the database and processes them with `ffprobe`.
- Updates scan progress in the UI.
- Marks files as `detailed_scan_attempted` even if scanning fails.

#### `extract_metadata_ffprobe(file_path)`
- Extracts metadata from video files using `ffprobe`.
- Returns details such as codec, resolution, bitrate, and subtitle languages.
- Ensures missing metadata does not break the scanning process.

#### `scan_directory(scan_path)`
- Recursively scans a directory for media files.
- Collects metadata such as file size, last modified date, and file type.
- Attempts to remount networked drives if unavailable.

#### `remount_drive(scan_path, smb_server)`
- Reconnects an SMB network drive if it's unmounted.
- Uses system commands (`open smb://`) to remount on macOS.
- Ensures scanning does not fail due to drive disconnection.

#### `start_detailed_scan()` (scanner.py)
- Starts the detailed scan process programmatically.
- Handles scan initiation and progress updates within the scanning module.
- Currently under review to determine if both versions of `start_detailed_scan()` are necessary.

#### `mark_scan_in_progress(scan_id)` (scanner.py)
- Marks a scan request as "in_progress" in the database.
- This function is under review for possible removal after testing.

### **UI Functions (`ui.py`)**

#### `load_top_folders()` (ui.py)
- Loads the list of top-level folders selected for scanning.
- Fetches data from the database and populates the UI.


#### `start_detailed_scan()` (ui.py)
- Initiates a detailed scan in a background thread.
- Ensures the UI remains responsive.
- Shows a progress bar while scanning is in progress.
- Calls the scan function in `scanner.py`.

#### `update_progress(current, total)`
- Updates the progress bar in the UI based on scan progress.
- Ensures the UI is updated from the main thread.

#### `open_logs()`
- Opens the log file in the system's default text editor.
- Handles platform-specific file opening (`open`, `xdg-open`, `os.startfile`).

### **Database Functions (`database/`)**

#### `get_unscanned_videos()` (file_records.py)
- Retrieves a list of video files that have not yet undergone a detailed scan.

#### `mark_file_as_scanned(file_path)` (file_records.py)
- Marks a file as having completed a detailed scan.

#### `mark_scan_attempted(file_path)` (file_records.py)
- Flags a file as having attempted a scan, even if it failed.

#### `update_video_metadata(file_path, metadata)` (file_records.py)
- Stores extracted metadata into the database.

#### `get_selected_smb_server()` (settings.py)
- Retrieves the selected SMB server for network drive scanning.

#### `get_selected_top_folders()` (scan_targets.py)
- Fetches the top-level folders that are currently selected for scanning.

#### `store_scan_results(file_name, file_path, file_size, file_modified, file_type)` (file_records.py)
- Stores basic scan results for all media files found in a directory scan.

#### `update_last_scanned(folder)` (scan_targets.py)
- Updates the timestamp of when a folder was last scanned.

## Planned Improvements

### **1️⃣ Improve Scan Performance**
- Implement multi-threaded scanning to speed up processing.
- Optimize database writes to avoid bottlenecks.

### **2️⃣ UI Enhancements**
- Add scan history logs and error reporting in the UI.
- Implement real-time scan status indicators.

### **3️⃣ Implement File Health Checks**
- Use `ffmpeg` to detect corrupted or incomplete media files.
- Mark problematic files for manual review.

### **4️⃣ Expand Metadata Collection**
- Store additional metadata such as HDR info, bit depth, and additional audio tracks.

### **5️⃣ Multi-Computer Support (Future Phase 2)**
- Enable distributed scanning across multiple machines.
- Implement a central database for merging scan results.

## Database Structure

### **1. ScanTargets**
Tracks directories being scanned.
```
id INTEGER PRIMARY KEY AUTOINCREMENT
top_folder TEXT UNIQUE NOT NULL
status TEXT NOT NULL DEFAULT 'active'
last_scanned TIMESTAMP DEFAULT NULL
```

### **2. FileRecords**
Stores metadata for scanned files.
```
id INTEGER PRIMARY KEY AUTOINCREMENT
file_name TEXT NOT NULL
file_type TEXT
file_path TEXT NOT NULL UNIQUE
file_size INTEGER
file_modified TEXT
last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
top_folder TEXT
detailed_scan_attempted INTEGER DEFAULT 0
```

### **3. Settings**
Stores user-defined settings, such as the selected SMB server.
```
id INTEGER PRIMARY KEY AUTOINCREMENT
key TEXT UNIQUE NOT NULL
value TEXT NOT NULL
```

## Best Practices for Large Projects
- **Enable WAL mode** for safer database writes.
- **Ensure only one scan runs at a time** to prevent corruption.
- **Use `INSERT OR REPLACE` instead of `INSERT`** to avoid duplicate issues.
- **Close SQLite connections properly** to avoid incomplete writes.

## Next Steps
- Implement logging for all major database operations.
- Improve error handling for UI interactions.
- Expand documentation with detailed function descriptions.
- Review and consolidate redundant functions (`start_detailed_scan()` in both `scanner.py` and `ui.py`).

