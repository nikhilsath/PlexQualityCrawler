import sys
import os
import platform
import subprocess
import logging
import database
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QMessageBox, QFileDialog, QDialog, QListWidget,
    QTableView, QVBoxLayout, QHBoxLayout, QCheckBox, QAbstractItemView
)
from PyQt6.QtCore import QAbstractTableModel, Qt, QTimer

LOG_FILE = os.path.join(os.getcwd(), "plex_quality_crawler.log")  # Log file path

# Configure logging
logging.basicConfig(
    filename="plex_quality_crawler.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Model for displaying scanned file data in a QTableView.
class FileTableModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.load_filtered_data()

    def load_filtered_data(self, query=None):
        """Fetch data from the database with optional filtering."""
        if query:
            self.data = database.get_filtered_files(query)
        else:
            self.data = database.get_all_files()  # Default to all files

        self.layoutChanged.emit()  # Refresh UI
        file_count_label.setText(f"Total Files: {len(self.data)}")  # Update count dynamically
        self.headers = ["File Name", "File Type", "File Size", "Last Modified"]

    def rowCount(self, parent=None):
        return len(self.data)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.data[index.row()][index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

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
switches_layout = QVBoxLayout()  # Dedicated layout for toggles
buttons_layout = QVBoxLayout()
table_layout = QVBoxLayout()

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

def show_videos_only():
    """Filters the table to display only video files."""
    query = "SELECT file_name, file_type, file_size, file_modified FROM FileRecords WHERE file_type IN ('.mp4', '.mkv', '.avi', '.mpg', '.mpeg', '.vob')"
    table_model.load_filtered_data(query)

def update_file_count():
    """Updates the file count label based on the current table data."""
    file_count_label.setText(f"Total Files: {len(table_model.data)}")

def select_scan_path():
    """Allows the user to select a folder to scan, adds it as a scan target, and refreshes UI."""
    folder_path = QFileDialog.getExistingDirectory(window, "Select a Folder to Scan")

    if folder_path:
        folder_name = os.path.basename(folder_path)
        logging.info(f"User selected folder: {folder_name}")

        try:
            database.add_scan_target(folder_name)  # ✅ Add to DB
            QTimer.singleShot(500, load_top_folders)  # ✅ Wait 500ms before reloading UI
            QMessageBox.information(window, "Scan Target Added", f"'{folder_name}' has been added.")

        except Exception as e:
            logging.error(f"Error adding scan target '{folder_name}': {str(e)}")
            QMessageBox.warning(window, "Database Error", f"Could not add scan target: {str(e)}")

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
            database.delete_scan_target(folder_name)  # ✅ Delete from DB
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

def start_scanner():
    """Starts scanning all active scan targets."""
    selected_folders = database.get_selected_top_folders()
    logging.info(f"User clicked Start Scan. Active scan targets: {selected_folders}")

    if not selected_folders:
        logging.warning("No active scan targets found. Scanner will not start.")
        QMessageBox.warning(window, "No Scan Targets", "No active scan targets found. Select a folder first.")
        return

    try:
        logging.info("Attempting to start scanner.py")
        process = subprocess.Popen(["python3", "scanner.py"])
        logging.info(f"Scanner started successfully with PID: {process.pid}")
        QMessageBox.information(window, "Scanning Started", "Scanning has started for selected folders.")
    except Exception as e:
        logging.error(f"Error starting scanner: {str(e)}")
        QMessageBox.warning(window, "Error", f"Could not start scanner: {str(e)}")

def toggle_scan_target(state, folder):
    """Adds or removes a scan target based on the switch state."""
    if state == 2:  # Checked (ON)
        database.add_scan_target(folder)
    else:  # Unchecked (OFF)
        database.remove_scan_target(folder)

# Create the application
app = QApplication(sys.argv)

# Create the main window
window = QWidget()
window.setWindowTitle("Plex Quality Crawler")
window.resize(600, 400)

# File Count
file_count_label = QLabel("Total Files: 0")
table_layout.addWidget(file_count_label)

# Table View
table_view = QTableView()
table_model = FileTableModel()
table_view.setModel(table_model)

# Enable sorting & selection
table_view.setSortingEnabled(True)
table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

table_layout.addWidget(table_view)

# Buttons Section

#Add Scan Target
select_path_button = QPushButton("Add Scan Target")
select_path_button.clicked.connect(select_scan_path)
buttons_layout.addWidget(select_path_button)

# Remove Scan Targets Button
remove_scan_button = QPushButton("Remove Scan Target")
remove_scan_button.clicked.connect(open_remove_scan_dialog)
buttons_layout.addWidget(remove_scan_button)


start_scan_button = QPushButton("Start Scan")
start_scan_button.clicked.connect(start_scanner)
buttons_layout.addWidget(start_scan_button)

logs_button = QPushButton("Open Logs")
logs_button.clicked.connect(open_logs)
buttons_layout.addWidget(logs_button)

# Combine layouts
main_layout.addLayout(table_layout)
main_layout.addLayout(switches_layout)
main_layout.addLayout(buttons_layout)

window.setLayout(main_layout)

# Show the window
load_top_folders()
window.show()

# Run the application event loop
sys.exit(app.exec())
