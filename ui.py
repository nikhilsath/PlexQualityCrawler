import sys
import os
import platform
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QMessageBox

# Function to handle button click
def start_scan():
    mac_address = mac_input.text()  # Get the text from input field
    if mac_address:
        QMessageBox.information(window, "Scan Started", f"Scanning machine: {mac_address}")
    else:
        QMessageBox.warning(window, "Error", "Please enter a MAC address.")

# Function to open the logs folder (Cross-Platform)
def open_logs():
    logs_path = os.path.expanduser("~/PlexQualityCrawlerLogs")  # Example logs folder
    if not os.path.exists(logs_path):
        QMessageBox.warning(window, "Error", "Logs folder not found.")
        os.makedirs(logs_path)  # Create folder if missing
    # Cross-platform way to open folder
    system_name = platform.system()
    if system_name == "Windows":
        os.startfile(logs_path)  # Windows
    elif system_name == "Darwin":  # macOS
        os.system(f'open "{logs_path}"')
    elif system_name == "Linux":
        os.system(f'xdg-open "{logs_path}"')  # Linux

# Function to handle cancel scan button click
def cancel_scan():
    QMessageBox.information(window, "Scan Canceled", "The scan has been canceled.")

# Create the application
app = QApplication(sys.argv)

# Create the main window
window = QWidget()
window.setWindowTitle("Plex Quality Crawler - Start Scan")  # Set window title
window.resize(400, 200)  # Window size

# Mac Address
label = QLabel("Enter MAC Address:", window)
label.move(20, 20)  # Label Position
mac_input = QLineEdit(window)
mac_input.move(20, 50)  # Position below the label
mac_input.resize(250, 30)  # Set width and height
# Mac Input Button
start_button = QPushButton("Start Scan", window)
start_button.move(20, 90)  # Position below the text input
start_button.clicked.connect(start_scan)  # Connect button click to function
# "Cancel Scan" button
cancel_button = QPushButton("Cancel Scan", window)
cancel_button.move(120, 90)  # Position it next to Start Scan
cancel_button.clicked.connect(cancel_scan)

# Open Logs Folder button
logs_button = QPushButton("Open Logs Folder", window)
logs_button.move(20, 130)  # Position below the other buttons
logs_button.clicked.connect(open_logs)

# Show the window
window.show()

# Run the application event loop
sys.exit(app.exec())
