import sys
import os
import re
import platform
import subprocess
import threading
import logging
import database
import database.settings
from scanner import run_detailed_scan

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QMessageBox, QFileDialog, QDialog, QListWidget,
    QTableView, QVBoxLayout, QHBoxLayout, QCheckBox, QAbstractItemView, QComboBox, QProgressBar
)
from PyQt6.QtCore import QAbstractTableModel, Qt, QTimer

LOG_FILE = os.path.join(os.getcwd(), "plex_quality_crawler.log")  # Log file path
detailed_scan_running = False  # Global flag to track scan status

# Configure logging
logging.basicConfig(
    filename="plex_quality_crawler.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Model for displaying scanned file data in a QTableView.

class ToggleSwitch(QCheckBox):
    """Custom QCheckBox styled to look like a switch."""
    def __init__(self, label):
        super().__init__(label)
        self.setStyleSheet(
            """
            QCheckBox::indicator {
                width: 40px;
                height: 20px;
                border-radius: 10px;
                background-color: lightgray;
            }
            QCheckBox::indicator:checked {
                background-color: green;
            }
            """
        )

# Create layouts for better structure
main_layout = QVBoxLayout()
switches_layout = QVBoxLayout()  
buttons_layout = QVBoxLayout()

def load_top_folders():
    """Fetches unique top folders, clears old switches, and updates the UI."""
    global switches_layout

    # ✅ Fix: Only clear the switches, not the entire UI
    while switches_layout.count():
        item = switches_layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()

    # Fetch scan targets from DB
    all_top_folders = database.get_all_unique_top_folders()
    selected_folders = database.get_selected_top_folders()
    logging.info(f"Refreshing UI with scan targets: {all_top_folders}")

    for folder in all_top_folders:
        switch = ToggleSwitch(folder)
        switch.setChecked(folder in selected_folders)  # ✅ Set state based on DB
        switch.stateChanged.connect(lambda state, f=folder: toggle_scan_target(state, f))
        switches_layout.addWidget(switch)

def update_file_count():
    """Fetch total file count from the database and update the label."""
    total_files = database.get_total_file_count()
    file_count_label.setText(f"Total Files: {total_files}")

def select_scan_path():
    """Allows the user to select a folder to scan, adds it as a scan target, and refreshes UI."""
    folder_path = QFileDialog.getExistingDirectory(window, "Select a Folder to Scan")

    if folder_path:
        folder_name = os.path.basename(folder_path)
        logging.info(f"User selected folder: {folder_name}")

        try:
            logging.debug(f"Calling database.add_scan_target({folder_name})")
            database.add_scan_target(folder_name)  # ✅ Add to DB
            QTimer.singleShot(500, load_top_folders)  # ✅ Wait 500ms before reloading UI
            QMessageBox.information(window, "Scan Target Added", f"'{folder_name}' has been added.")

        except Exception as e:
            logging.error(f"Error adding scan target '{folder_name}': {str(e)}")


def start_detailed_scan():
    """Starts the detailed scan and ensures UI updates properly."""
    global detailed_scan_running
    if detailed_scan_running:
        QMessageBox.warning(None, "Scan in Progress", "A detailed scan is already running.")
        return
    
    detailed_scan_running = True
    progress_bar.setValue(0)
    progress_bar.setVisible(True)

    # Use a QTimer to periodically refresh UI updates
    scan_timer = QTimer()
    scan_timer.timeout.connect(lambda: update_progress(current_progress, total_files))
    scan_timer.start(500)  # Refresh progress every 500ms

    threading.Thread(target=run_detailed_scan, daemon=True).start()

def open_remove_scan_dialog():
    """Opens a dialog box to allow users to remove scan targets."""
    dialog = QDialog(window)
    dialog.setWindowTitle("Remove Scan Targets")
    dialog.resize(400, 300)

    layout = QVBoxLayout()

    # List of scan targets
    scan_list = QListWidget()
    scan_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)  # Allow multiple selections

    # Fetch current scan targets from DB
    scan_targets = database.get_all_unique_top_folders()
    scan_list.addItems(scan_targets)  # Populate the list

    layout.addWidget(scan_list)

    # Remove button
    remove_button = QPushButton("Remove Selected")
    remove_button.clicked.connect(lambda: remove_selected_scans(dialog, scan_list))
    layout.addWidget(remove_button)

    # Cancel button
    cancel_button = QPushButton("Cancel")
    cancel_button.clicked.connect(dialog.reject)
    layout.addWidget(cancel_button)

    dialog.setLayout(layout)
    dialog.exec()  # Show the dialog

def remove_selected_scans(dialog, scan_list):
    """Deletes selected scan targets from the database."""
    selected_items = scan_list.selectedItems()
    if not selected_items:
        QMessageBox.warning(window, "No Selection", "No scan targets selected for removal.")
        return

    # Confirm deletion
    confirm = QMessageBox.question(
        window,
        "Confirm Removal",
        "Are you sure you want to remove the selected scan targets? This cannot be undone.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )

    if confirm == QMessageBox.StandardButton.Yes:
        for item in selected_items:
            folder_name = item.text()
            database.delete_scan_target(folder_name)  # Delete from DB
            logging.info(f"Deleted scan target: {folder_name}")

        QMessageBox.information(window, "Success", "Selected scan targets have been removed.")
        load_top_folders()  # Refresh UI
        dialog.accept()  # Close dialog

def open_logs():
    """Opens the log file (Cross-Platform)."""
    if not os.path.exists(LOG_FILE):
        QMessageBox.warning(window, "Error", "Log file not found.")
        return

    system_name = platform.system()
    try:
        if system_name == "Windows":
            os.startfile(LOG_FILE)
        elif system_name == "Darwin":  # macOS
            subprocess.run(["open", LOG_FILE])
        elif system_name == "Linux":
            subprocess.run(["xdg-open", LOG_FILE])
    except Exception as e:
        QMessageBox.warning(window, "Error", f"Could not open log file: {str(e)}")

def update_progress(current, total):
    """Updates the progress bar in the UI."""
    if total > 0:
        percentage = int((current / total) * 100)
        progress_bar.setValue(percentage)


def start_scanner():
    """Starts scanning all active scan targets, ensuring an SMB server is selected first."""
    
    selected_folders = database.get_selected_top_folders()
    selected_server = smb_dropdown.currentText()  # ✅ Fetch the selected SMB server

    logging.info(f"User clicked Start Scan. Active scan targets: {selected_folders}")

    if not selected_server:
        logging.warning("No SMB server selected. Scanner will not start.")
        QMessageBox.warning(window, "No SMB Server", "Please select an SMB server before starting the scan.")
        return

    if not selected_folders:
        logging.warning("No active scan targets found. Scanner will not start.")
        QMessageBox.warning(window, "No Scan Targets", "No active scan targets found. Select a folder first.")
        return

    try:
        logging.info(f"Attempting to start scanner.py with SMB server: {selected_server}")
        process = subprocess.Popen(["python3", "scanner.py"])
        logging.info(f"Scanner started successfully with PID: {process.pid}")
        QMessageBox.information(window, "Scanning Started", "Scanning has started for selected folders.")
        QTimer.singleShot(5000, update_file_count)  # update file count after timer

    except Exception as e:
        logging.error(f"Error starting scanner: {str(e)}")
        QMessageBox.warning(window, "Error", f"Could not start scanner: {str(e)}")

# Switch Toggles
def toggle_scan_target(state, folder):
    """Updates scan target status and logs the action."""
    logging.debug(f"Toggle event: {folder} set to {'active' if state == 2 else 'inactive'}")

    try:
        if state == 2:  # Checked (ON)
            logging.debug(f"Calling database.activate_scan_target({folder})")
            database.activate_scan_target(folder)  # ✅ Change status to 'active'
        else:  # Unchecked (OFF)
            logging.debug(f"Calling database.deactivate_scan_target({folder})")
            database.deactivate_scan_target(folder)  # ✅ Change status to 'inactive'
    except Exception as e:
        logging.error(f"Error while toggling scan target '{folder}': {str(e)}")


# Create the application
app = QApplication(sys.argv)

# Create the main window
window = QWidget()
window.setWindowTitle("Plex Quality Crawler")
window.resize(600, 400)

# SMB Server Selection Section
smb_layout = QHBoxLayout()

# Dropdown (QComboBox)
smb_dropdown = QComboBox()
smb_layout.addWidget(smb_dropdown)

# Fetch available SMB servers (dummy list for now, will improve later)
available_servers = ["smb://MBP-Server.local", "smb://NAS-Server.local", "smb://File-Server.local"]
smb_dropdown.addItems(available_servers)

# Function to handle SMB server selection change
def update_selected_smb_server():
    selected_server = smb_dropdown.currentText()
    database.set_selected_smb_server(selected_server)  # ✅ Save to database
    logging.info(f"User selected new SMB server: {selected_server}")

# Connect dropdown selection change to the function
smb_dropdown.currentIndexChanged.connect(update_selected_smb_server)


# Load last-selected server from database
last_selected_server = database.settings.get_selected_smb_server()
if last_selected_server in available_servers:
    smb_dropdown.setCurrentText(last_selected_server)
else:
    # ✅ If no server was stored, select the first available option
    default_server = available_servers[0] if available_servers else None
    smb_dropdown.setCurrentText(default_server)
    database.set_selected_smb_server(default_server) 
# Combine with existing layout
main_layout.addLayout(smb_layout)

# File Count Label
file_count_label = QLabel("Total Files: 0")
main_layout.addWidget(file_count_label)

# 📌 Create button layouts
buttons_layout = QVBoxLayout()  # Main button layout

# 1️⃣ Horizontal Layout for "Add Scan Target" and "Remove Scan Target"
add_remove_layout = QHBoxLayout()

# Add Scan Target Button
select_path_button = QPushButton("Add Scan Target")
select_path_button.clicked.connect(select_scan_path)
add_remove_layout.addWidget(select_path_button)

# Remove Scan Targets Button
remove_scan_button = QPushButton("Remove Scan Target")
remove_scan_button.clicked.connect(open_remove_scan_dialog)
add_remove_layout.addWidget(remove_scan_button)

# 2️⃣ Add the horizontal layout to the main buttons layout
buttons_layout.addLayout(add_remove_layout)

# 3️⃣ Stack the remaining buttons below
# Create a horizontal layout for Start Scan and Detailed Scan buttons
scan_buttons_layout = QHBoxLayout()

# Start Scan Button
start_scan_button = QPushButton("Start Scan")
start_scan_button.clicked.connect(start_scanner)
scan_buttons_layout.addWidget(start_scan_button)

# Detailed Scan Button
detailed_scan_button = QPushButton("Detailed Scan")
detailed_scan_button.clicked.connect(start_detailed_scan)  # Calls the scan function
scan_buttons_layout.addWidget(detailed_scan_button)
buttons_layout.addLayout(scan_buttons_layout)

# Progress Bar for Detailed Scan
progress_bar = QProgressBar()
progress_bar.setValue(0)  # Start at 0%
progress_bar.setVisible(False)  # Hide initially
main_layout.addWidget(progress_bar)

logs_button = QPushButton("Open Logs")
logs_button.clicked.connect(open_logs)
buttons_layout.addWidget(logs_button)

# 📌 Combine all layouts
main_layout.addLayout(switches_layout)
main_layout.addLayout(buttons_layout)

window.setLayout(main_layout)

# Show the window
load_top_folders() #Load switches
update_file_count() #Load file count
window.show()

# Run the application event loop
sys.exit(app.exec())
