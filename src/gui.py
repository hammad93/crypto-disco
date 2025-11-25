from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QVBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QWidget, QCheckBox, QHBoxLayout
)
from PySide6.QtCore import Qt, QFileInfo

class crypto_disco(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("crypto-disco")
        self.resize(600, 300)
        # Initialize variables
        self.total_size_bytes = 0
        self.file_list = []  # Store tuples of (file_name, size_str, ecc_checked)
        # Create main layout and central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        # Create add files button
        self.add_files_button = QPushButton("Add Files", self)
        self.add_files_button.clicked.connect(self.add_files)
        layout.addWidget(self.add_files_button)
        # Create table widget
        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["File Size", "ECC", "File Name"])
        self.table.setColumnWidth(0, 100)  # Adjust width for File Size column
        self.table.setColumnWidth(1, 50)   # Adjust width for ECC column
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        # Create run application button
        self.run_button = QPushButton("Create .iso file(s)", self)
        self.run_button.clicked.connect(self.run_application)
        layout.addWidget(self.run_button)
        # Create label for total size
        self.total_size_label = QLabel("Total Size: 0 GB", self)
        layout.addWidget(self.total_size_label)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files")
        if not files:
            return
        current_row = self.table.rowCount()
        self.table.setRowCount(current_row + len(files))
        for file in files:
            file_info = QFileInfo(file)
            file_size = file_info.size()
            self.total_size_bytes += file_size
            file_name = file_info.fileName()
            directory = file_info.absolutePath()
            # Convert file size
            size_gb = file_size / (1024**3)
            size_mb = file_size / (1024**2)
            size_str = f"{size_gb:.2f} GB" if size_gb >= 1 else f"{size_mb:.2f} MB"
            self.table.setItem(current_row, 0, QTableWidgetItem(size_str))
            # Create unchecked checkbox for ECC
            ecc_checkbox = QCheckBox(self.table)
            ecc_checkbox.setChecked(False)
            ecc_checkbox.stateChanged.connect(lambda state, row=current_row: self.update_file_list_state(row, state))
            container_widget = QWidget()
            container_layout = QHBoxLayout(container_widget)
            container_layout.addWidget(ecc_checkbox)
            container_layout.setAlignment(Qt.AlignCenter)  # Center the widget in the layout
            container_layout.setContentsMargins(0, 0, 0, 0)  # Remove default margins
            self.table.setCellWidget(current_row, 1, container_widget)
            self.table.setItem(current_row, 2, QTableWidgetItem(file_name))
            self.table.item(current_row, 2).setToolTip(directory)
            self.file_list.append([directory, file_name, size_str, False])
            current_row += 1
        # Update total size display
        self.update_total_size_label()

    def update_file_list_state(self, row, state):
        if state == 2:
            self.file_list[row][-1] = True
        else:
            self.file_list[row][-1] = False

    def update_total_size_label(self):
        total_size_gb = self.total_size_bytes / (1024**3)
        total_size_mb = self.total_size_bytes / (1024**2)
        total_size_str = f"{total_size_gb:.2f} GB" if total_size_gb >= 1 else f"{total_size_mb:.2f} MB"
        self.total_size_label.setText(f"Total Size: {total_size_str}")

    def run_application(self):
        # Example function to demonstrate using the file_list
        for directory, file_name, size_str, ecc_checked in self.file_list:
            print(f"File Path: {directory + file_name}, Size: {size_str}, ECC: {'Checked' if ecc_checked else 'Unchecked'}")
