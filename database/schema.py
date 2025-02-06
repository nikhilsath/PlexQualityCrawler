import logging
import time
import os
from database.db_connection import get_connection

def initialize_database():
    """Ensures database and required tables exist before proceeding."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ScanTargets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            top_folder TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            last_scanned TIMESTAMP DEFAULT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS FileRecords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_type TEXT,
            file_path TEXT NOT NULL UNIQUE,
            file_size INTEGER,
            file_modified TEXT,
            last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            top_folder TEXT,
            video_codec TEXT,
            resolution TEXT,
            duration REAL,
            frame_rate TEXT,
            video_bitrate INTEGER,
            video_bit_depth INTEGER,
            color_primaries TEXT,
            color_transfer TEXT,
            audio_codec TEXT,
            audio_channels INTEGER,
            audio_sample_rate INTEGER,
            audio_bitrate INTEGER,
            audio_languages TEXT,
            subtitle_count INTEGER,
            subtitle_languages TEXT,
            file_format TEXT,
            probe_score INTEGER,
            detailed_scan_attempted INTEGER DEFAULT 0 
        )
    ''')

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

def validate_database():
    """Runs a quick check to confirm all required tables exist."""
    conn = get_connection()
    cursor = conn.cursor()

    required_tables = {"ScanTargets", "FileRecords", "Settings"}
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = {row[0] for row in cursor.fetchall()}
    
    conn.close()

    if not required_tables.issubset(existing_tables):
        logging.error("Database is missing required tables. Reinitializing...")
        return False
    
    return True

# ✅ Initialize if necessary
if not os.path.exists("plex_quality_crawler.db"):
    logging.info("Database file not found. Initializing database...")
    initialize_database()
    time.sleep(1)
elif not validate_database():
    logging.warning("Reinitializing database due to missing tables.")
    initialize_database()
    time.sleep(1)
else:
    logging.info("Database is valid. Skipping initialization.")
