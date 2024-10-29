import sys
import os
import requests
import psutil
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QDialog,
    QAbstractItemView,
    QLabel,
    QLineEdit,
    QComboBox,
)
from PyQt5.QtCore import QTimer, Qt, QPoint

class AboutDialog(QDialog):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        developer_label = QLabel("Developer: Surelle")
        year_label = QLabel("Year: 2023")

        layout.addWidget(developer_label)
        layout.addWidget(year_label)

        self.setLayout(layout)
        self.setWindowTitle("About")

class AddApplicationDialog(QDialog):
    def __init__(self, running_apps):
        super().__init__()

        self.selected_apps = []

        layout = QVBoxLayout()

        self.app_list = QListWidget()
        self.app_list.setSelectionMode(QAbstractItemView.MultiSelection)  # Enable multi-selection
        layout.addWidget(self.app_list)

        self.priority_combobox = QComboBox()
        self.priority_combobox.addItems(["urgent", "high", "default", "low", "min"])  # Updated priority options
        layout.addWidget(self.priority_combobox)

        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.select_applications)
        layout.addWidget(self.select_button)

        self.setLayout(layout)
        self.setWindowTitle("Select Applications to Monitor")

        # Populate the list with running apps and their PIDs
        for app_name, pid in running_apps.items():
            item = QListWidgetItem(f"{app_name} (PID: {pid})")
            item.setData(Qt.UserRole, pid)  # Store the PID as user data
            self.app_list.addItem(item)

    def select_applications(self):
        selected_items = self.app_list.selectedItems()
        priority = self.priority_combobox.currentText()  # Get the selected priority
        self.selected_apps = [(item.text(), item.data(Qt.UserRole), priority) for item in selected_items]  # Retrieve app name, PID, and priority
        self.accept()

class AppMonitor(QWidget):
    def __init__(self):
        super().__init__()

        self.selected_apps = []  # List to store selected apps to monitor (name, PID, priority)
        self.monitoring = False  # Variable to track monitoring state
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_apps)

        layout = QVBoxLayout()

        server_layout = QHBoxLayout()
        self.server_label = QLabel("Server:")
        self.server_input = QLineEdit("https://ntfy.sh/")  # Removed setDisabled(True)
        server_layout.addWidget(self.server_label)
        server_layout.addWidget(self.server_input)
        layout.addLayout(server_layout)

        channel_layout = QHBoxLayout()
        self.channel_label = QLabel("Channel:")
        self.channel_input = QLineEdit("heustaquio_notif")  # Removed setDisabled(True)
        channel_layout.addWidget(self.channel_label)
        channel_layout.addWidget(self.channel_input)
        layout.addLayout(channel_layout)

        self.app_list = QListWidget()
        layout.addWidget(self.app_list)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Application")
        self.add_button.clicked.connect(self.add_application)
        button_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("Remove Application")
        self.remove_button.clicked.connect(self.remove_application)
        button_layout.addWidget(self.remove_button)

        self.start_button = QPushButton("Start Monitoring")
        self.start_button.clicked.connect(self.toggle_monitoring)
        button_layout.addWidget(self.start_button)

        about_button = QPushButton("About")
        about_button.clicked.connect(self.show_about)
        button_layout.addWidget(about_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setWindowTitle("App Monitor")

    def add_application(self):
        if self.monitoring:
            QMessageBox.warning(self, "Monitoring Ongoing", "Cannot add applications while monitoring is ongoing.")
            return

        running_apps = self.get_running_applications()
        dialog = AddApplicationDialog(running_apps)
        if dialog.exec_() == QDialog.Accepted:
            selected_apps = dialog.selected_apps
            for app_name, pid, priority in selected_apps:
                self.selected_apps.append((app_name, pid, priority))
                self.app_list.addItem(f"{app_name} (PID: {pid}, Priority: {priority})")

    def remove_application(self):
        if self.monitoring:
            QMessageBox.warning(self, "Monitoring Ongoing", "Cannot remove applications while monitoring is ongoing.")
            return

        selected_items = self.app_list.selectedItems()
        items_to_remove = []

        for item in selected_items:
            text = item.text()
            for app_name, pid, priority in self.selected_apps:
                if text.startswith(f"{app_name} (PID: {pid}, Priority: {priority})"):
                    items_to_remove.append((app_name, pid, priority))

        for app_name, pid, priority in items_to_remove:
            self.selected_apps.remove((app_name, pid, priority))

        for item in selected_items:
            self.app_list.takeItem(self.app_list.row(item))

    def get_running_applications(self):
        running_apps = {}
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            running_apps[proc.info['name']] = proc.info['pid']
        return running_apps

    def toggle_monitoring(self):
        if not self.monitoring:
            if not self.selected_apps:
                QMessageBox.warning(self, "No Applications Selected", "Please select applications to monitor.")
                return

            # Check if there are selected apps
            if not self.selected_apps:
                QMessageBox.warning(self, "No Applications Selected", "Please select applications to monitor.")
                return

            self.timer.start(5000)  # Set the timer to check every 5 seconds
            self.start_button.setText("Stop Monitoring")
            self.monitoring = True
            self.server_input.setDisabled(True)  # Disable the server input field
            self.channel_input.setDisabled(True)  # Disable the channel input field
            QMessageBox.information(self, "Monitoring Started", "Monitoring has started.")
        else:
            self.timer.stop()
            self.start_button.setText("Start Monitoring")
            self.monitoring = False
            self.server_input.setEnabled(True)  # Enable the server input field
            self.channel_input.setEnabled(True)  # Enable the channel input field

            # Check if there are still apps to monitor
            if not self.selected_apps:
                QMessageBox.information(self, "Monitoring Stopped", "Monitoring has been stopped. No applications to monitor.")

    def check_apps(self):
        if not self.selected_apps:
            return

        apps_to_remove = []
        for app_name, pid, priority in self.selected_apps:
            if not self.is_app_running(pid):
                # Notify when an app stops
                self.notify_app_stopped(app_name, priority)
                apps_to_remove.append((app_name, pid, priority))

        for app_name, pid, priority in apps_to_remove:
            self.selected_apps.remove((app_name, pid, priority))

            # Find all matching items and remove them
            items_to_remove = self.app_list.findItems(f"{app_name} (PID: {pid}, Priority: {priority})", Qt.MatchStartsWith)
            for item in items_to_remove:
                self.app_list.takeItem(self.app_list.row(item))

    def is_app_running(self, pid):
        try:
            # Check if the process exists
            return psutil.pid_exists(pid)
        except:
            return False

    def notify_app_stopped(self, app_name, priority):
        # Notify when an app stops
        server = self.server_input.text()
        channel = self.channel_input.text()
        url = f"{server}{channel}"
        data = f"{app_name} stopped working."
        tags = ""
        if priority == "urgent":
            tags = "skull, skull"
        elif priority == "high":
            tags = "skull"
        elif priority == "default":
            tags = "rotating_light"
        elif priority == "low":
            tags = "warning"
        elif priority == "min":
            tags = "loudspeaker"

        headers = {
            "Title": "Application Closed",
            "Priority": priority,
            "Tags": tags
        }
        requests.post(url, data=data, headers=headers)

    def show_about(self):
        about_dialog = AboutDialog()
        about_dialog.exec_()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setFixedSize(600, 400)  # Disable resizing
        self.setWindowTitle("App Monitor")

        # Get the screen dimensions to center the window
        screen_geometry = QApplication.desktop().screenGeometry()
        x = int((screen_geometry.width() - self.width()) / 2)
        y = int((screen_geometry.height() - self.height()) / 2)
        self.move(x, y)  # Center the window on the screen

        self.central_widget = AppMonitor()
        self.setCentralWidget(self.central_widget)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
