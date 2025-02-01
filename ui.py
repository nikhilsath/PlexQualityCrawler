import sys
import os
import platform
import subprocess
import logging
import database 
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QMessageBox, QFileDialog, QTableView, QVBoxLayout, QAbstractItemView
from PyQt6.QtCore import QAbstractTableModel, Qt

LOG_FILE = os.path.join(os.getcwd(), "plex_quality_crawler.log")  # Log file path

# Configure logging
logging.basicConfig(
    filename="plex_quality_crawler.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class FileTableModel(QAbstractTableModel):
    """Model for displaying scanned file data in a QTableView."""
    
    def __init__(self):
        super().__init__()
        self.load_data()

    def load_data(self):
        """Fetch data from the database."""
        self.data = database.get_all_files()  # Fetch file records from DB
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


#Opens a file dialog to select the scan path and saves it."""
def select_scan_path():
    folder_path = QFileDialog.getExistingDirectory(window, "Select Scan Directory")
    
    if folder_path:
        database.save_scan_path(folder_path)  # Save path to the database
        scan_path_label.setText(f"Selected Scan Path: {folder_path}")  # Update label
        QMessageBox.information(window, "Scan Path Set", f"Scan path updated to: {folder_path}")
        logging.info(f"Scan path updated to: {folder_path}")


# Function to handle button click
def start_scan(): #Starts a scan request
    logging.info("User clicked 'Add Scan'")
    database.add_scan_request()  # No MAC address needed
    QMessageBox.information(window, "Scan Started", "Scan request has been added.")


# Function to open the logs (Cross-Platform)
def open_logs():
    #Opens the log file 
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

#Starts the scanner process from the UI.
def start_scanner():
    try:
        subprocess.Popen(["python3", "scanner.py"])  # Start scanner.py in the background
        QMessageBox.information(window, "Scanner Started", "The scanner has started in the background.")
        logging.info("Scanner started from UI.")
    except Exception as e:
        QMessageBox.warning(window, "Error", f"Could not start scanner: {str(e)}")
        logging.error(f"Error starting scanner from UI: {str(e)}")

# Function to handle cancel scan button click
def cancel_scan():
    QMessageBox.information(window, "Scan Canceled", "The scan has been canceled.")

# Create the application
app = QApplication(sys.argv)

# Create the main window
window = QWidget()
window.setWindowTitle("Plex Quality Crawler")  # Set window title
window.resize(600, 400)  # Window size

# Label to display the selected scan path
scan_path_label = QLabel("Selected Scan Path: Not Set", window)
scan_path_label.move(20, 20)  # Adjust position
scan_path_label.resize(350, 30)  # Set width and height

# Start Scan Button
start_button = QPushButton("Add Scan", window)
start_button.move(20, 50) 
start_button.clicked.connect(start_scan)

# Cancel Scan Button
cancel_button = QPushButton("Cancel Scan", window)
cancel_button.move(120, 50) 
cancel_button.clicked.connect(cancel_scan)

# Start Scanner Button
start_scanner_button = QPushButton("Start Scanner", window)
start_scanner_button.move(230, 50) 
start_scanner_button.clicked.connect(start_scanner)

# Select Scan Path Button
select_path_button = QPushButton("Select Scan Path", window)
select_path_button.move(20, 100)
select_path_button.clicked.connect(select_scan_path)

# Open Logs Button
logs_button = QPushButton("Open Logs", window)
logs_button.move(20, 130) 
logs_button.clicked.connect(open_logs)

layout = QVBoxLayout()

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

# Start Scan Button
start_button = QPushButton("Add Scan")
start_button.clicked.connect(start_scan)
buttons_layout.addWidget(start_button)

# Start Scanner Button
start_scanner_button = QPushButton("Start Scanner")
start_scanner_button.clicked.connect(start_scanner)
buttons_layout.addWidget(start_scanner_button)

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

