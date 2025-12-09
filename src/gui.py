'''
Hammad Usmani
November 25th, 2025

References
----------
https://doc.qt.io/qtforpython-6/
https://clalancette.github.io/pycdlib/example-creating-new-basic-iso.html
https://wiki.osdev.org/ISO_9660#Filenames
https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/
'''
from PySide6 import QtGui
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QVBoxLayout, QPushButton, QTableWidget, QComboBox, QTextEdit, QMessageBox,
    QTableWidgetItem, QLabel, QWidget, QCheckBox, QHBoxLayout, QProgressDialog
)
from PySide6.QtCore import Qt, QFileInfo, QThreadPool
import os
from pathlib import Path
import iso
import compute_ecc

class crypto_disco(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crypto Disco")
        self.this_dir = os.path.dirname(__file__)
        self.icon = QtGui.QIcon(os.path.join(self.this_dir, "disc-drive-reshot.svg"))
        self.setWindowIcon(self.icon)
        self.resize(600, 300)
        self.setup_menu_bar()
        # Initialize variables
        self.current_ecc_dir = None
        self.count_ecc = 0
        self.total_size_bytes = 0
        self.file_list = []  # Store a dictionary of metadata of files
        # Create main layout and central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        # Create add files button
        self.add_files_button = QPushButton("Add Files", self)
        self.add_files_button.clicked.connect(self.add_files)
        layout.addWidget(self.add_files_button)
        # Create table widget
        self.table_cols = ["File Size", "ECC", "Clone", "File Name"]
        self.table = QTableWidget(self)
        self.table.setColumnCount(len(self.table_cols))
        self.table.setHorizontalHeaderLabels(self.table_cols)
        self.table.setColumnWidth(self.table_cols.index("File Size"), 100)
        self.table.setColumnWidth(self.table_cols.index("ECC"), 50)
        self.table.setColumnWidth(self.table_cols.index("Clone"), 50)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        # Create the horizontal layout for run button and combo box
        run_layout = QHBoxLayout()
        # Create combo box for disc sizes
        self.disc_size_combo = QComboBox(self)
        self.disc_size_list = ["4.7 GB M-DISC DVD+R",
                               "25 GB M-DISC BD-R",
                               "50 GB M-DISC BD-R",
                               "100 GB M-DISC BDXL"]
        self.disc_size_combo.addItems(self.disc_size_list)
        self.disc_size_combo.setCurrentIndex(self.disc_size_list.index("25 GB M-DISC BD-R"))
        run_layout.addWidget(self.disc_size_combo)
        # Create run application button
        self.run_button = QPushButton("Generate .iso file", self)
        self.run_button.clicked.connect(self.run_application)
        run_layout.addWidget(self.run_button)
        # Add the run layout to the main layout
        layout.addLayout(run_layout)
        # Create label for total size
        self.total_size_label = QLabel("Total Size: 0 GB", self)
        layout.addWidget(self.total_size_label)
        # Thread management
        self.threadpool = QThreadPool()

    def setup_menu_bar(self):
        # Create menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        about_menu = menu_bar.addMenu("About")
        # Add actions to File menu
        add_files_action = QtGui.QAction("Add files to staged .iso", self)
        add_files_action.triggered.connect(self.add_files)
        file_menu.addAction(add_files_action)
        clear_files_action = QtGui.QAction("Clear All files from staged .iso", self)
        clear_files_action.triggered.connect(self.clear_files)
        file_menu.addAction(clear_files_action)
        # Add action to About menu
        about_action = QtGui.QAction("About", self)
        self.readme = "README.md not found"
        for test_path in [Path(__file__).parent, Path(__file__).parent.parent]:
            readme_path = test_path / "README.md"
            if os.path.exists(readme_path):
                with open(readme_path) as file:
                    self.readme = file.read()
                break
        about_action.triggered.connect(self.show_readme)
        about_menu.addAction(about_action)

    def show_readme(self):
        text_box = QTextEdit()
        text_box.resize(500,300)
        text_box.setReadOnly(True)
        text_box.setMarkdown(self.readme)
        text_box.setWindowTitle("README.md Contents")
        text_box.show()

    def clear_files(self):
        self.table.setRowCount(0)
        self.total_size_bytes = 0
        self.file_list = []
        self.update_total_size_label()

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
            self.table.setItem(current_row, self.table_cols.index("File Size"), QTableWidgetItem(size_str))
            # Create unchecked checkbox for ECC
            def create_checkbox(col_name):
                checkbox = QCheckBox(self.table)
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(
                    lambda state, row=current_row: self.update_file_list_state(row, state, col_name))
                container_widget = QWidget()
                container_layout = QHBoxLayout(container_widget)
                container_layout.addWidget(checkbox)
                container_layout.setAlignment(Qt.AlignCenter)
                container_layout.setContentsMargins(0, 0, 0, 0)
                return container_widget
            for checkbox_col in ["ECC", "Clone"]:
                self.table.setCellWidget(
                    current_row, self.table_cols.index(checkbox_col), create_checkbox(checkbox_col))
            self.table.setItem(current_row, self.table_cols.index("File Name"), QTableWidgetItem(file_name))
            self.table.item(current_row, self.table_cols.index("File Name")).setToolTip(directory)
            self.file_list.append({
                "directory": directory,
                "file_name": file_name,
                "file_size": file_size,
                "size_str": size_str,
                "ecc_checked": True,
                "clone_checked": True
            })
            current_row += 1
        # Update total size display
        self.update_total_size_label()

    def update_file_list_state(self, row, state, col_name):
        key = f"{col_name.lower()}_checked" # relevant key in dictionary
        if state == 2:
            self.file_list[row][key] = True
        else:
            self.file_list[row][key] = False

    def update_total_size_label(self):
        total_size_gb = self.total_size_bytes / (1024**3)
        total_size_mb = self.total_size_bytes / (1024**2)
        total_size_str = f"{total_size_gb:.2f} GB" if total_size_gb >= 1 else f"{total_size_mb:.2f} MB"
        self.total_size_label.setText(f"Total Size: {total_size_str}")

    def set_ecc_dir(self, ecc_dir):
        self.current_ecc_dir = ecc_dir
        ecc_monitor = compute_ecc.EccMonitor(self.count_ecc, ecc_dir)
        ecc_progress_dialog = QProgressDialog("Processing ECC...",
                                              "Cancel", 0, (self.count_ecc * 100), self)
        ecc_progress_dialog.setWindowModality(Qt.WindowModal)
        ecc_progress_dialog.setValue(0)
        ecc_monitor.signals.progress.connect(ecc_progress_dialog.setValue)
        ecc_monitor.signals.progress_text.connect(ecc_progress_dialog.setLabelText)
        self.threadpool.start(ecc_monitor)

    def run_application(self):
        '''
        Prompt user for output ISO file path

        Notes
        -----
        The following can be swapped out for potential performance improvements
        >>> options = QFileDialog.Options()
        >>> options |= QFileDialog.DontUseNativeDialog  # Force non-native dialog
        >>> QFileDialog.getSaveFileName(
        >>>     self, "Save ISO", "", "ISO Files (*.iso)", options=options)
        '''
        output_path, filter = QFileDialog.getSaveFileName(
            self, "Save ISO", "", "ISO Files (*.iso)")
        if not output_path:
            print("ISO creation cancelled.")
            return
        else:
            if output_path.split(".")[-1].lower() != "iso":
                print("Appending .iso to output path.")
                output_path = f"{output_path}.iso"
            print(f"Output file path is {output_path}")
            if os.path.exists(output_path):
                popup = QMessageBox.warning(
                    self, "File already exists", "Overwriting existing files is not permitted.")
                return popup
            self.output_path = output_path
        self.count_ecc = [f["ecc_checked"] for f in self.file_list].count(True)
        if self.count_ecc > 0:
            # Display progress for ECC processing
            print("Processing error correcting codes (ECC) . . .")
            ecc_worker = compute_ecc.EccWorker(self.file_list)
            # set ecc directory and begin monitor
            ecc_worker.signals.result.connect(self.set_ecc_dir)
            # after ECC is done, save out to ISO
            ecc_worker.signals.finished.connect(self.run_save_iso)
            self.threadpool.start(ecc_worker)
        else:
            self.run_save_iso()

    def run_save_iso(self):
        print("Creating .iso file...")
        # Display progress bar for saving ISO
        progress_dialog = QProgressDialog("Saving ISO...", "Cancel", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setValue(0)
        worker = iso.IsoWorker(
            self.output_path, self.file_list, self.current_ecc_dir, self.disc_size_combo.currentText())
        worker.signals.progress.connect(progress_dialog.setValue)
        worker.signals.progress_end.connect(progress_dialog.setMaximum)
        worker.signals.progress_text.connect(progress_dialog.setLabelText)
        self.threadpool.start(worker)
