# database/database.py
from database.db_connection import get_connection, enable_wal_mode
from database.schema import initialize_database, validate_database
from database.scan_targets import get_all_unique_top_folders, get_selected_top_folders, add_scan_target, activate_scan_target, deactivate_scan_target, update_last_scanned
from database.file_records import store_scan_results, get_total_file_count
from database.settings import get_selected_smb_server, set_selected_smb_server

# ✅ Explicitly assign functions to module-level attributes
get_connection = get_connection
enable_wal_mode = enable_wal_mode
initialize_database = initialize_database
validate_database = validate_database
get_all_unique_top_folders = get_all_unique_top_folders
get_selected_top_folders = get_selected_top_folders
add_scan_target = add_scan_target
store_scan_results = store_scan_results
get_total_file_count = get_total_file_count
get_selected_smb_server = get_selected_smb_server
set_selected_smb_server = set_selected_smb_server
get_all_unique_top_folders = get_all_unique_top_folders

# ✅ Ensure all functions are explicitly exposed for wildcard imports
__all__ = [
    "get_connection", "enable_wal_mode",
    "initialize_database", "validate_database",
    "get_all_unique_top_folders", "get_selected_top_folders", "add_scan_target",
    "store_scan_results", "get_total_file_count",
    "get_selected_smb_server", "set_selected_smb_server",
     "activate_scan_target", "deactivate_scan_target",
     "update_last_scanned"
]
