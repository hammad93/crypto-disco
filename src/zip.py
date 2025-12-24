from PySide6.QtCore import QRunnable, Slot, QObject, Signal, Qt, QFileInfo
from PySide6.QtWidgets import (QWizardPage, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit,
                               QDialog, QComboBox, QWizard, QTableWidget, QTableWidgetItem, QMessageBox)
import pyzipper
import zipfile
import traceback
import config
import utils
import pathlib
import os

class ZipWorker(QRunnable):
    def __init__(self, wizard, gui, zip_config=False):
        super().__init__()
        self.wizard = wizard
        self.gui = gui
        self.signals = ZipWorkerSignals()
        self.zip_config = zip_config or {
            'file_list': [],
            'password': None,
            'split_size': None, # bytes
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
        def write_zip(paths, zf):
            for path in paths:
                if os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Maintain directory structure relative to the folder
                            zf.write(file_path,
                                       arcname=os.path.relpath(file_path, start=os.path.dirname(path)))
                else:
                    zf.write(path, arcname=os.path.basename(path))
        if not password:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                write_zip(file_list, zipf)
        else:
            print(f"Writing to {output_path}")
            with pyzipper.AESZipFile(output_path, 'w', compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES) as zipf:
                zipf.setpassword(password.encode())
                write_zip(file_list, zipf)
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

        self.file_list_bytes_label = QLabel("Total Uncompressed Size: 0")
        layout.addWidget(self.file_list_bytes_label)

        open_zip_layout = QHBoxLayout()
        open_zip_label = QLabel("Decompress .zip or split with .01, .02 . . .")
        open_zip_layout.addWidget(open_zip_label)
        open_zip_button = QPushButton("Open Split ZIP File(s)")
        open_zip_button.clicked.connect(lambda: self.select_files("zip_file"))
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

        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("(Optional) Set password for ZIP file: "))
        password_button = QPushButton("Set Password")
        password_button.clicked.connect(self.set_password)
        password_layout.addWidget(password_button)
        layout.addLayout(password_layout)

        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("(Optional) Choose max ZIP split size:"))
        self.split_dropdown = QComboBox()
        self.split_dropdown.addItems(["None"] + config.disc_types)
        self.split_dropdown.setCurrentText("None")
        self.split_dropdown.currentTextChanged.connect(self.change_split_size)
        options_layout.addWidget(self.split_dropdown)
        layout.addLayout(options_layout)

        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Select output file for the ZIP file:"))
        output_button = QPushButton("Select Output File(s)")
        output_button.clicked.connect(self.output_file)
        output_layout.addWidget(output_button)
        layout.addLayout(output_layout)

        self.output_path_text = QLineEdit()
        self.output_path_text.setPlaceholderText("No folder selected...")
        self.output_path_text.setReadOnly(True)
        page.registerField("output_path*", self.output_path_text)
        #layout.addWidget(self.output_path_text)

        start_zip_button = QPushButton("Compress and Save ZIP file")
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

    def set_password(self):
        dialog = QDialog()
        dialog.setWindowTitle("Set Password")
        layout = QVBoxLayout()
        dialog.setFixedSize(350, 125)
        dialog.setLayout(layout)

        pwd_input_1 = QLineEdit()
        pwd_input_1.setEchoMode(QLineEdit.Password)
        pwd_input_1.setPlaceholderText("Password")
        layout.addWidget(pwd_input_1)
        pwd_input_2 = QLineEdit()
        pwd_input_2.setEchoMode(QLineEdit.Password)
        pwd_input_2.setPlaceholderText("Confirm Password")
        layout.addWidget(pwd_input_2)

        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(lambda: self.validate_password(dialog, pwd_input_1.text(), pwd_input_2.text()))
        layout.addWidget(submit_button)

        if dialog.exec() == QDialog.Accepted:
            print("Password set")
        else:
            print("Password not set")

    def validate_password(self, dialog, pwd1, pwd2):
        if pwd1 == "":
            self.validate_password_message("Please enter a password.")
        elif pwd1 == pwd2:
            self.zip_config["password"] = pwd1
            dialog.accept()
        else:
            self.validate_password_message("Passwords do not match")

    def validate_password_message(self, text):
        popup = QMessageBox()
        popup.setIcon(QMessageBox.Warning)
        popup.setWindowTitle("Password Validation")
        popup.setText("There was an error validating the password:")
        popup.setInformativeText(text)
        return popup.exec()

    def change_split_size(self):
        current_split_size = self.split_dropdown.currentText()
        if current_split_size == "None":
            self.zip_config["split_size"] = None
        else:
            split_size = utils.disc_type_bytes(current_split_size)
            self.zip_config["split_size"] = split_size

    def start_zip(self):
        try:
            self.output_status_text.show()
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

    def output_file(self):
        file_name, _ = QFileDialog.getSaveFileName(
            None, "Save ZIP File", "", "ZIP Files (*.zip)")
        if file_name.split(".")[-1].lower() != "zip":
            print("Appending .zip to output path.")
            file_name += ".zip"
        print(f"Output file path is {file_name}")
        if os.path.exists(file_name):
            popup = QMessageBox.warning(
                None, "File already exists", "Overwriting existing files is not permitted.")
            return popup
        else:
            self.zip_config["output_path"] = file_name

    def process_path(self, var_name, path_name):
        if path_name:
            if isinstance(path_name, list):
                text = "\n".join(path_name)
                self.zip_config["file_list"].extend(path_name)
            else:
                text = path_name
                self.zip_config["file_list"].append(path_name)
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
            self.file_list_bytes_label.setText(f"Total Uncompressed Size: {utils.total_size_str(self.file_list_bytes)}")

class ZipWorkerSignals(QObject):
    finished = Signal(str)
    cancel = Signal()
    error = Signal(object)
    result = Signal(object)