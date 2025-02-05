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

def get_connection():
    """Returns a database connection."""
    return sqlite3.connect(DB_FILE)

def enable_wal_mode():
    """Enable Write-Ahead Logging (WAL) mode for better performance."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        conn.commit()
        conn.close()
        logging.info("WAL mode enabled successfully.")
    except sqlite3.OperationalError as e:
        logging.error(f"Failed to enable WAL mode: {e}")
