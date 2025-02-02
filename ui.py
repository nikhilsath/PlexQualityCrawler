import sys
import os
import platform
import subprocess
import logging
import database 
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QMessageBox, QFileDialog, QTableView, QVBoxLayout, QAbstractItemView
from PyQt6.QtCore import QAbstractTableModel, Qt

LOG_FILE = os.path.join(os.getcwd(), "plex_quality_crawler.log")  # Log file path

# Configure logging
logging.basicConfig(
    filename="plex_quality_crawler.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

#Model for displaying scanned file data in a QTableView."""
class FileTableModel(QAbstractTableModel):    
    def __init__(self):
        super().__init__()
        self.load_filtered_data()

    def load_filtered_data(self, query=None):
    #Fetch data from the database with optional filtering.
        if query:
            self.data = database.get_filtered_files(query)
        else:
            self.data = database.get_all_files()  # Default to all files

        self.layoutChanged.emit()  # Refresh UI
        file_count_label.setText(f"Total Files: {len(self.data)}")  # ✅ Update count dynamically
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

#Filters the table to display only video files.
def show_videos_only():
    query = "SELECT file_name, file_type, file_size, file_modified FROM FileRecords WHERE file_type IN ('.mp4', '.mkv', '.avi', '.mpg', '.mpeg', '.vob')"
    table_model.load_filtered_data(query)

def update_file_count():
    """Updates the file count label based on the current table data."""
    file_count_label.setText(f"Total Files: {len(table_model.data)}")

# Opens a file dialog to select the scan path and saves it."""
def select_scan_path():
    folder_path = QFileDialog.getExistingDirectory(window, "Select Scan Directory")
    
    if folder_path:
        database.save_scan_path(folder_path)  # ✅ Save path to database
        database.add_scan_request()  # ✅ Automatically add scan request
        logging.info(f"Scan path updated to: {folder_path}. Scan request added.")

        # ✅ Automatically start the scanner if it's not already running
        try:
            subprocess.Popen(["python3", "scanner.py"])  
            logging.info("Scanner started automatically from UI.")
        except Exception as e:
            logging.error(f"Error starting scanner from UI: {str(e)}")


# Function to open the logs (Cross-Platform)
def open_logs():
    # Opens the log file 
    if not os.path.exists(LOG_FILE):
        QMessageBox.warning(window, "Error", "Log file not found.")
        return

    system_name = platform.system()
    try:
        if system_name == "Windows":
            os.startfile(LOG_FILE)  # Windows
        elif system_name == "Darwin":  # macOS
            subprocess.run(["open", LOG_FILE])
        elif system_name == "Linux":
            subprocess.run(["xdg-open", LOG_FILE])  # Linux
    except Exception as e:
        QMessageBox.warning(window, "Error", f"Could not open log file: {str(e)}")

# Starts the scanner process from the UI.
def start_scanner():
    try:
        subprocess.Popen(["python3", "scanner.py"])  # Start scanner.py in the background
        QMessageBox.information(window, "Scanner Started", "The scanner has started in the background.")
        logging.info("Scanner started from UI.")
    except Exception as e:
        QMessageBox.warning(window, "Error", f"Could not start scanner: {str(e)}")
        logging.error(f"Error starting scanner from UI: {str(e)}")

# Create the application
app = QApplication(sys.argv)

# Create the main window
window = QWidget()
window.setWindowTitle("Plex Quality Crawler")  # Set window title
window.resize(600, 400)  # Window size

# Open Logs Button
logs_button = QPushButton("Open Logs", window)
logs_button.move(20, 130) 
logs_button.clicked.connect(open_logs)

layout = QVBoxLayout()
# File Count
file_count_label = QLabel("Total Files: 0")
layout.addWidget(file_count_label)

# Table View
table_view = QTableView()
table_model = FileTableModel()
table_view.setModel(table_model)

# Enable sorting & selection
table_view.setSortingEnabled(True)
table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

layout.addWidget(table_view)

# Buttons Section
buttons_layout = QVBoxLayout()

# Show Videos Only Button
show_videos_button = QPushButton("Show Videos Only")
buttons_layout.addWidget(show_videos_button)
show_videos_button.clicked.connect(show_videos_only)

# Select Scan Path Button
select_path_button = QPushButton("Select Scan Path")
select_path_button.clicked.connect(select_scan_path)
buttons_layout.addWidget(select_path_button)

# Open Logs Button
logs_button = QPushButton("Open Logs")
logs_button.clicked.connect(open_logs)
buttons_layout.addWidget(logs_button)

layout.addLayout(buttons_layout)

window.setLayout(layout)

# Show the window
window.show()

# Run the application event loop
sys.exit(app.exec())
