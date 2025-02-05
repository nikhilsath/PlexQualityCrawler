# Plex Quality Crawler

## Project Overview
Plex Quality Crawler is a Python-based tool that scans directories for video files and tracks metadata to improve organization.

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

## Database Structure
The application uses an SQLite database (`plex_quality_crawler.db`) with the following tables:

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
```

### **3. Settings**
Stores user-defined settings, such as the selected SMB server.
```
id INTEGER PRIMARY KEY AUTOINCREMENT
key TEXT UNIQUE NOT NULL
value TEXT NOT NULL
```

## Adding New Database Functions
To add a new function to interact with the database:

1. **Decide the file to modify**  
   - If related to **scan targets**, update `scan_targets.py`  
   - If related to **file records**, update `file_records.py`  
   - If related to **settings**, update `settings.py`  
   - If it's a core database operation, update `db_connection.py`

2. **Write the function** in the appropriate file.  
   Example: Adding a function to count scan targets in `scan_targets.py`:
   ```python
   def count_scan_targets():
       """Returns the total number of scan targets."""
       conn = get_connection()
       cursor = conn.cursor()
       cursor.execute("SELECT COUNT(*) FROM ScanTargets")
       total = cursor.fetchone()[0]
       conn.close()
       return total
   ```

3. **Expose the function in `database.py`**
   ```python
   from database.scan_targets import count_scan_targets
   ```
   Add it to `__all__` to make it accessible when importing `database`:
   ```python
   __all__ = ["count_scan_targets"]
   ```

4. **Use the function in `scanner.py` or `ui.py`**  
   ```python
   total_targets = database.count_scan_targets()
   print(f"Total scan targets: {total_targets}")
   ```

## Best Practices for Large Projects
To prevent losing functions during major refactors, large companies use:
- **Code Documentation**: Internal wikis or tools like Confluence.  
- **Automated Testing**: Ensuring critical functions are always checked.  
- **Version Control**: Using Git and tracking function removals/additions.  
- **API Documentation**: Keeping an updated list of all database functions.  
- **Code Reviews**: Ensuring all functions are migrated before a major change.  

This project should eventually adopt some of these practices for easier tracking.

## Next Steps
- Implement logging for all major database operations.
- Improve error handling for UI interactions.
- Expand documentation with detailed function descriptions.
