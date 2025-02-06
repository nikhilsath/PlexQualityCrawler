import logging
from database.db_connection import get_connection

def store_scan_results(file_name, file_path, file_size, file_modified, file_type):
    """Stores or updates scanned file metadata."""
    conn = get_connection()
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

def get_total_file_count():
    """Returns the total number of scanned files."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM FileRecords")
    total = cursor.fetchone()[0]
    conn.close()
    return total

# Video Scan
def update_video_metadata(file_path, metadata):
    """Updates the FileRecords table with detailed metadata from ffprobe."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE FileRecords
        SET video_codec = ?, resolution = ?, duration = ?, frame_rate = ?, video_bitrate = ?,
            video_bit_depth = ?, color_primaries = ?, color_transfer = ?,
            audio_codec = ?, audio_channels = ?, audio_sample_rate = ?, audio_bitrate = ?, audio_languages = ?,
            subtitle_count = ?, subtitle_languages = ?, file_format = ?, probe_score = ?
        WHERE file_path = ?
    """, (
        metadata["video_codec"], metadata["resolution"], metadata["duration"], metadata["frame_rate"],
        metadata["video_bitrate"], metadata["video_bit_depth"], metadata["color_primaries"], metadata["color_transfer"],
        metadata["audio_codec"], metadata["audio_channels"], metadata["audio_sample_rate"], metadata["audio_bitrate"],
        metadata["audio_languages"], metadata["subtitle_count"], metadata["subtitle_languages"],
        metadata["file_format"], metadata["probe_score"], file_path
    ))

    conn.commit()
    conn.close()

def get_unscanned_videos():
    """Fetches video files that need a detailed scan."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT file_path FROM FileRecords
        WHERE file_type IN ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv')
        AND detailed_scan_attempted = 0
    """)
    
    files = [row[0] for row in cursor.fetchall()]
    logging.info(f"🔎 Found {len(files)} unscanned video files.")  # ✅ Log how many files are found

    conn.close()
    return files


def mark_file_as_scanned(file_path):
    """Marks a file as having undergone a detailed scan."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE FileRecords SET detailed_scan_attempted = 1 WHERE file_path = ?", (file_path,))
    conn.commit()
    conn.close()
    logging.info(f"Marked file as detailed scan completed: {file_path}")
