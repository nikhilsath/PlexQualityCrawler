# Plex Quality Crawler

## Project Overview

Plex Quality Crawler is a Python-based tool that scans directories for files and gathers metadata on video content.  It stores the results in an SQLite database for later reference and leaves other file types untouched.

## Project Structure

```
PlexQualityCrawler/
├── database/               # Database-related modules
│   ├── __init__.py         # Package initializer
│   ├── database.py         # Exposes database helper functions
│   ├── db_connection.py    # Manages database connections
│   ├── schema.py           # Handles database initialization & validation
│   ├── scan_targets.py     # Manages scan target queries
│   ├── file_records.py     # Handles file metadata storage & retrieval
│   └── settings.py         # Manages app settings (e.g., SMB server)
├── scanner.py              # Scans selected folders and updates metadata
├── ui.py                   # User interface for managing scan targets & settings
├── requirements.txt        # Python dependencies
└── plex_quality_crawler.db # SQLite database (created automatically)
```

## Installation

1. Install the required Python packages:

```bash
pip install -r requirements.txt
```

2. Run the GUI application:

```bash
python3 ui.py
```

On the first run the database file `plex_quality_crawler.db` is created automatically.  The initializer in `database/schema.py` ensures all required tables exist.

## Function Descriptions

### Scanner (`scanner.py`)

- `scan_directory(scan_path)` – Recursively scans a directory, collecting file size, modification time and type.  If a network share is unavailable it attempts to remount it with `remount_drive()`.
- `remount_drive(scan_path, smb_server)` – Reconnects an SMB share when it becomes unmounted.
- `extract_metadata_ffprobe(file_path)` – Uses `ffprobe` to gather detailed metadata about a video file.
- `run_detailed_scan()` – Retrieves all unscanned videos from the database, extracts metadata for each and stores the results.

### UI (`ui.py`)

- `load_top_folders()` – Loads the list of user configured folders.
- `start_detailed_scan()` – Launches `run_detailed_scan()` in a background thread so the UI remains responsive.
- `update_progress(current, total)` – Updates the progress bar during a scan.
- `open_logs()` – Opens the application log with the system default text editor.

### Database Helpers (`database/`)

- `store_scan_results(...)` – Inserts or updates basic file details discovered during a directory scan.
- `get_unscanned_videos()` – Returns videos that still need a detailed scan.
- `mark_file_as_scanned(file_path)` – Marks a file as having been processed by `ffprobe`.
- `update_video_metadata(file_path, metadata)` – Stores extracted metadata fields.
- `get_selected_smb_server()` – Returns the SMB server configured in settings.
- `get_selected_top_folders()` – Retrieves the list of active scan targets.
- `update_last_scanned(folder)` – Records the timestamp when a folder was last scanned.

## Database Schema

### ScanTargets
Tracks directories being scanned.
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
top_folder TEXT UNIQUE NOT NULL
status TEXT NOT NULL DEFAULT 'active'
last_scanned TIMESTAMP DEFAULT NULL
```

### FileRecords
Stores metadata for scanned files.
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
file_name TEXT NOT NULL
file_type TEXT
file_path TEXT NOT NULL UNIQUE
file_size INTEGER
file_modified TEXT
last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
top_folder TEXT
video_codec TEXT
resolution TEXT
duration REAL
frame_rate TEXT
video_bitrate INTEGER
video_bit_depth INTEGER
color_primaries TEXT
color_transfer TEXT
audio_codec TEXT
audio_channels INTEGER
audio_sample_rate INTEGER
audio_bitrate INTEGER
audio_languages TEXT
subtitle_count INTEGER
subtitle_languages TEXT
file_format TEXT
probe_score INTEGER
detailed_scan_attempted INTEGER DEFAULT 0
```

### Settings
Stores user-defined settings such as the selected SMB server.
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
key TEXT UNIQUE NOT NULL
value TEXT NOT NULL
```

## Best Practices
- Enable WAL mode for safer database writes.
- Ensure only one scan runs at a time to prevent corruption.
- Use `INSERT OR REPLACE` to avoid duplicates.
- Close SQLite connections properly to avoid incomplete writes.

