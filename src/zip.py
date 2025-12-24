from PySide6.QtCore import QRunnable, Slot, QObject, Signal, Qt, QFileInfo
from PySide6.QtWidgets import (QWizardPage, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit,
                               QCheckBox, QComboBox, QWizard, QTableWidget, QTableWidgetItem)
import pyzipper
import traceback
import config
import utils
import pathlib

class ZipWorker(QRunnable):
    def __init__(self, wizard, gui, zip_config=False):
        super().__init__()
        self.wizard = wizard
        self.gui = gui
        self.signals = ZipWorkerSignals()
        self.zip_config = zip_config or {
            'password': None,
            'split_size': None,  # in MB
            'split': False
        }
        self.file_list_bytes = 0

    @Slot()
    def run(self):
        try:
            self.create_zip(self.zip_config)
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            self.signals.error.emit({"exception": e, "msg": msg})

    def create_zip(self, config):
        file_list = self.zip_config['file_list']
        output_path = self.zip_config['output_path']
        password = config.get('password')
        split_size = config.get('split_size')
        split = config.get('split')

        with pyzipper.AESZipFile(output_path, 'w', compression=pyzipper.ZIP_LZMA) as zf:
            if password:
                zf.setpassword(password.encode())

            for file in file_list:
                zf.write(file)

            # Handle splitting logic if necessary
            # This is a simplified example; actual implementation may vary
            if split and split_size:
                # Implement splitting logic here
                pass

        self.signals.finished.emit(f"ZIP file created at {output_path}")

    def select_files_page(self):
        page = QWizardPage()
        page.setTitle("Select Files and Folders")
        layout = QVBoxLayout()

        label = QLabel("Select files and folders to compress:")
        layout.addWidget(label)

        zip_buttons_layout = QHBoxLayout()
        select_files_button = QPushButton("Add Files to ZIP file(s)")
        select_files_button.clicked.connect(lambda: self.select_files("file_list"))
        zip_buttons_layout.addWidget(select_files_button)

        select_folder_button = QPushButton("Add Folder to ZIP file(s)")
        select_folder_button.clicked.connect(lambda: self.select_dir("file_list"))
        zip_buttons_layout.addWidget(select_folder_button)
        layout.addLayout(zip_buttons_layout)

        self.file_list_text = QLineEdit()
        self.file_list_text.setPlaceholderText("No files selected...")
        self.file_list_text.setReadOnly(True)
        page.registerField("file_list*", self.file_list_text)
        #layout.addWidget(self.file_list_text)

        self.file_list_table = QTableWidget()
        self.file_list_table.setColumnCount(2)
        self.file_list_table.setHorizontalHeaderLabels(["Size", "File(s) and Folder(s)"])
        self.file_list_table.setColumnWidth(0, config.file_size_col_w)
        self.file_list_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.file_list_table)

        self.file_list_bytes_label = QLabel("Total Size: 0")
        layout.addWidget(self.file_list_bytes_label)

        open_zip_layout = QHBoxLayout()
        open_zip_label = QLabel("Decompress .zip or split with .01, .02 . . .")
        open_zip_layout.addWidget(open_zip_label)
        open_zip_button = QPushButton("Open Split ZIP File(s)")
        open_zip_button.clicked.connect(lambda: self.select_file("zip_file"))
        open_zip_layout.addWidget(open_zip_button)
        layout.addLayout(open_zip_layout)

        self.zip_file_text = QLineEdit()
        self.zip_file_text.setPlaceholderText("No ZIP file selected...")
        self.zip_file_text.setReadOnly(True)
        page.registerField("zip_file", self.zip_file_text)
        #layout.addWidget(self.zip_file_text)

        page.setLayout(layout)
        page.setFinalPage(False)
        self.select_files_page_wizard = page
        return page

    def select_output_page(self):
        page = QWizardPage()
        page.setTitle("Output and Advanced Configuration")
        layout = QVBoxLayout()

        label = QLabel("Select output folder for the ZIP file:")
        layout.addWidget(label)

        select_dir_button = QPushButton("Select Folder")
        select_dir_button.clicked.connect(lambda: self.select_dir("output_path"))
        layout.addWidget(select_dir_button)

        self.output_path_text = QLineEdit()
        self.output_path_text.setPlaceholderText("No folder selected...")
        self.output_path_text.setReadOnly(True)
        page.registerField("output_path*", self.output_path_text)
        layout.addWidget(self.output_path_text)

        password_label = QLabel("Password (optional):")
        layout.addWidget(password_label)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        split_label = QLabel("Enable file splitting:")
        layout.addWidget(split_label)
        self.split_checkbox = QCheckBox()
        layout.addWidget(self.split_checkbox)

        split_size_label = QLabel("Split size (MB):")
        layout.addWidget(split_size_label)
        self.split_size_input = QComboBox()
        self.split_size_input.addItems(["20", "40", "80", "100"])
        layout.addWidget(self.split_size_input)

        start_zip_button = QPushButton("Start ZIP")
        start_zip_button.clicked.connect(self.start_zip)
        layout.addWidget(start_zip_button)

        self.output_status_text = QLineEdit()
        self.output_status_text.setPlaceholderText("Processing . . .")
        self.output_status_text.setReadOnly(True)
        page.registerField("output_status*", self.output_status_text)
        layout.addWidget(self.output_status_text)

        self.output_status_text.hide()
        page.setLayout(layout)
        page.setFinalPage(True)
        self.select_output_page_wizard = page
        return page

    def start_zip(self):
        try:
            self.output_status_text.show()
            self.zip_config = {
                'file_list': self.select_files_page_wizard.field("file_list"),
                'output_path': self.select_output_page_wizard.field("output_path"),
                'password': self.password_input.text(),
                'split_size': int(self.split_size_input.currentText()) * 1024 * 1024 if self.split_checkbox.isChecked() else None,
                'split': self.split_checkbox.isChecked()
            }
            zip_worker = ZipWorker(self.wizard, self.gui, self.zip_config)
            zip_worker.signals.error.connect(lambda e: self.error_popup(f"Error creating ZIP", e))
            zip_worker.signals.finished.connect(self.output_status_text.setText)
            self.gui.threadpool.start(zip_worker)
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            self.signals.error.emit({"exception": e, "msg": msg})

    def select_files(self, var_name):
        file_names, _ = QFileDialog.getOpenFileNames(None, "Select Files")
        self.process_path(var_name, file_names)

    def select_dir(self, var_name):
        dir_name = QFileDialog.getExistingDirectory(None, "Select Output Directory")
        self.process_path(var_name, dir_name)

    def select_file(self, var_name):
        file_name, _ = QFileDialog.getOpenFileName(None, "Select ZIP File")
        self.process_path(var_name, file_name)

    def process_path(self, var_name, path_name):
        if path_name:
            if isinstance(path_name, list):
                text = "\n".join(path_name)
            else:
                text = path_name
            getattr(self, f"{var_name}_text").setText(text)
            if var_name == "file_list":
                # update table
                row_count = self.file_list_table.rowCount()
                if isinstance(path_name, list):
                    self.file_list_table.setRowCount(row_count + len(path_name))
                    for index, file in enumerate(path_name):
                        current_row = index + row_count
                        file_info = QFileInfo(file)
                        file_bytes = file_info.size()
                        self.file_list_bytes += file_bytes
                        self.file_list_table.setItem(
                            current_row, 0, QTableWidgetItem(utils.total_size_str(file_bytes)))
                        self.file_list_table.setItem(current_row, 1, QTableWidgetItem(file_info.fileName()))
                        self.file_list_table.item(current_row, 1).setToolTip(file_info.absolutePath())
                else: # it's a folder
                    # get total size of folder
                    folder_size = sum(f.stat().st_size for f in pathlib.Path(path_name).rglob("*") if f.is_file())
                    self.file_list_bytes += folder_size
                    self.file_list_table.insertRow(row_count)
                    self.file_list_table.setItem(
                        row_count, 0, QTableWidgetItem(utils.total_size_str(folder_size)))
                    self.file_list_table.setItem(row_count, 1, QTableWidgetItem(path_name))
                    self.file_list_table.item(row_count, 1).setToolTip("Full Folder Path")
            self.file_list_bytes_label.setText(f"Total Size: {utils.total_size_str(self.file_list_bytes)}")

class ZipWorkerSignals(QObject):
    finished = Signal(str)
    cancel = Signal()
    error = Signal(object)
    result = Signal(object)