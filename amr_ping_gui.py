import csv
import os
import platform
import subprocess
import time
import re
import sys
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QVBoxLayout, QWidget, QHBoxLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

# Robot configuration
ROBOTS = {
    "Utac01": "10.158.17.140",
    "Utac02": "10.158.17.43",
    "Utac03": "10.158.17.69",
    "Utac04": "10.158.17.38"
}

# Generate timestamped log filename
start_time = datetime.now()
LOG_FILE = f"status_log_{start_time.strftime('%Y%m%d_%H%M%S')}.csv"
LOG_HEADERS = ["Robot_Name", "IP", "Event", "Timestamp", "Latency (ms)"]

# Initialize status tracking
current_status = {name: None for name in ROBOTS}

# Import winsound for Windows beeps
if platform.system() == 'Windows':
    import winsound

def play_beep():
    """Play a short beep sound"""
    try:
        if platform.system() == 'Windows':
            winsound.Beep(1000, 200)  # 1000 Hz for 200 ms
        else:
            # For Linux/macOS, use terminal bell character
            os.system('echo -n "\a"')
    except Exception:
        pass  # Silently ignore any beep errors

def ping_host(ip):
    """Ping a host and return (status, latency) tuple"""
    if platform.system().lower() == 'windows':
        command = ['ping', '-n', '1', '-w', '1000', ip]
    else:
        command = ['ping', '-c', '1', '-W', '1', ip]
    
    try:
        # Run ping command and capture output
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3
        )
        
        # Check if ping was successful
        if result.returncode == 0:
            # Extract latency from output
            latency = parse_latency(result.stdout)
            return (True, latency)
        return (False, -1)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return (False, -1)

def parse_latency(output):
    """Extract latency value from ping output"""
    try:
        if platform.system().lower() == 'windows':
            # Windows output example: "Reply from 10.158.17.140: bytes=32 time=7ms TTL=58"
            match = re.search(r'time[=<>](\d+)ms', output)
            if match:
                return int(match.group(1))
        else:
            # Linux output example: "64 bytes from 10.158.17.140: icmp_seq=1 ttl=58 time=6.24 ms"
            match = re.search(r'time[=<>](\d+\.?\d*) ms', output)
            if match:
                return round(float(match.group(1)))
        return -1  # Latency not found in output
    except (ValueError, TypeError):
        return -1  # Conversion error

def log_event(robot_name, ip, event, latency):
    """Record status change event to CSV file with error handling"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            with open(LOG_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([robot_name, ip, event, timestamp, latency])
            print(f"[{timestamp}] {robot_name} ({ip}): {event} | Latency: {latency} ms")
            return True
        except PermissionError:
            if attempt < max_retries - 1:
                print(f"Warning: Log file busy (attempt {attempt+1}/{max_retries}), retrying...")
                time.sleep(retry_delay)
            else:
                print(f"ERROR: Failed to log event for {robot_name} after {max_retries} attempts")
        except Exception as e:
            print(f"ERROR: Unexpected error logging {robot_name} event: {str(e)}")
            return False
    
    return False

class RobotMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Monitor")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(300, 180)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Status label
        self.status_label = QLabel(f"Monitoring started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        main_layout.addWidget(self.status_label)
        
        # Create table
        self.table = QTableWidget()
        self.table.setRowCount(len(ROBOTS))
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Robot", "IP", "Status", "Time(ms)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        
        # Populate table with initial data
        for row, (name, ip) in enumerate(ROBOTS.items()):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(ip))
            self.table.setItem(row, 2, QTableWidgetItem("Initializing..."))
            self.table.setItem(row, 3, QTableWidgetItem(""))
        
        main_layout.addWidget(self.table)
        
        # Create log file
        self.create_log_file()
        
        # Footer with log info
        footer = QHBoxLayout()
        self.log_label = QLabel(f"Log file: {LOG_FILE}")
        footer.addWidget(self.log_label)
        footer.addStretch()
        main_layout.addLayout(footer)
        
        # Set up monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.monitor_robots)
        self.monitor_timer.start(10000)  # Check every 10 seconds
        
        print(f"Starting robot monitoring at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Logging to: {LOG_FILE}")

    def create_log_file(self):
        """Create log file with headers"""
        global LOG_FILE  # Declare we're modifying the global variable
        
        try:
            with open(LOG_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(LOG_HEADERS)
            print(f"Created new log file: {LOG_FILE}")
        except PermissionError:
            print(f"ERROR: Cannot create log file - permission denied. Using fallback name.")
            # Generate fallback filename with process ID
            LOG_FILE = f"status_log_{start_time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}.csv"
            with open(LOG_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(LOG_HEADERS)
            print(f"Created fallback log file: {LOG_FILE}")
            # Update the log label in UI
            self.log_label.setText(f"Log file: {LOG_FILE}")
        except Exception as e:
            print(f"FATAL ERROR: Cannot create log file: {str(e)}")
            self.status_label.setText(f"FATAL ERROR: Cannot create log file - {str(e)}")
    
    def update_table(self, name, status, latency):
        """Update robot status in the table"""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == name:
                self.table.item(row, 2).setText(status)
                self.table.item(row, 3).setText(str(latency) if latency >= 0 else "N/A")
                
                # Set color based on status
                if status == "Online":
                    self.table.item(row, 2).setBackground(QColor(0, 255, 0))  # Green
                else:
                    self.table.item(row, 2).setBackground(QColor(255, 0, 0))   # Red
                break
    
    def monitor_robots(self):
        """Check robot status and update UI"""
        for name, ip in ROBOTS.items():
            is_online, latency = ping_host(ip)
            
            # For offline events, force latency to -1
            if not is_online:
                latency = -1
            
            # Update status in UI
            status_text = "Online" if is_online else "Offline"
            self.update_table(name, status_text, latency)
            
            # Detect status change
            if current_status[name] is None:
                # Initial status
                current_status[name] = is_online
                log_event(name, ip, status_text, latency)
            elif current_status[name] != is_online:
                # Status changed
                log_event(name, ip, status_text, latency)
                current_status[name] = is_online
                
                # Play beep sound for status change
                play_beep()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RobotMonitorApp()
    window.show()
    sys.exit(app.exec_())