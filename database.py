import sqlite3
import os

DB_FILE = "plex_quality_crawler.db"

def initialize_database():
    # Only initialize if the database file doesn't exist
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Create the ScanQueue table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ScanQueue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac_address TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        print("Database initialized successfully.")
    else:
        print("Database already exists. No changes made.")

if __name__ == "__main__":
    initialize_database()
