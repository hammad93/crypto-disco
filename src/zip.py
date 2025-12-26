from PySide6.QtCore import QRunnable, Slot, Qt, QFileInfo
from PySide6.QtWidgets import (QWizardPage, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit,
                               QDialog, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox, QProgressBar,
                               QPlainTextEdit)
import pyzipper
import zipfile
import traceback
import config
import utils
import pathlib
import os
import math

class ZipWorker(QRunnable):
    def __init__(self, wizard, gui, zip_config=False):
        super().__init__()
        self.wizard = wizard
        self.gui = gui
        self.signals = utils.WorkerSignals()
        self.zip_config = zip_config or {
            'file_list': [],
            'file_list_bytes': 0,
            'password': None,
            'split_size': None, # bytes
        }

    @Slot()
    def run(self):
        try:
            self.create_zip()
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            self.signals.error.emit({"exception": e, "msg": msg})

    def write_zip(self, paths, zf):
        self.processed_bytes = 0
        self.signals.progress.emit(0)

        def write_zip_wrapper(_file_path, _arcname, _zf):
            processed_bytes_iteration = self.processed_bytes + os.path.getsize(_file_path)
            self._write_file_in_chunks(_file_path, _arcname, _zf)
            self.processed_bytes = processed_bytes_iteration
            self.signals.progress.emit((self.processed_bytes / self.zip_config['file_list_bytes']) * 100)

        for index, path in enumerate(paths):
            self.signals.progress_text.emit(f"Processing {path} ...")
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        write_zip_wrapper(file_path, os.path.relpath(file_path, start=os.path.dirname(path)), zf)
            else:
                write_zip_wrapper(path, os.path.basename(path), zf)
            self.signals.progress_text.emit("Successfully processed file into ZIP.")

    def _write_file_in_chunks(self, file_path, arcname, zf):
        chunk_size = 16 * (1024 * 1024)  # 16MB
        with open(file_path, 'rb') as f:
            with zf.open(arcname, 'w', force_zip64=True) as archive_file:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    archive_file.write(chunk)
                    self.processed_bytes += len(chunk)
                    self.signals.progress.emit((self.processed_bytes / self.zip_config['file_list_bytes']) * 100)

    def create_zip(self):
        file_list = self.zip_config['file_list']
        output_path = self.zip_config['output_path']
        password = self.zip_config['password']
        split_size = self.zip_config['split_size']
        if not password:
            self.signals.progress_text.emit(f"Creating ZIP output file: {output_path}")
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                self.write_zip(file_list, zipf)
        else:
            self.signals.progress_text.emit(f"Creating AES 256 password protected ZIP output file: {output_path} ...")
            with pyzipper.AESZipFile(
                    output_path, 'w', compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES) as zipf:
                zipf.setpassword(password.encode())
                self.write_zip(file_list, zipf)
        if split_size not in [None, "None"]:
            self.split_zip(output_path, split_size)
        self.signals.result.emit(f"ZIP file created at {output_path}")

    def split_zip(self, zip, split_size, overwrite=False):
        '''
        Split file into parts. Although split_zip implemented for zip files, the logic can be used for any file

        zip = example.zip (8.0 GB)
        split_size = 4.7 GB M-Disc DVD (other include 25 GB M-Disc Blu-ray)
        example.zip.part1_of_2 = 4 GB (byte 0 --> 4 GB)
        example.zip.part2_of_2 = 4 GB (byte 4 GB --> 8 GB)
        M-Disc DVD x 2 = 9.9 GB
        example.zip.part1_of_2 (4 GB < 4.7 GB) on 1st M-Disc DVD
        example.zip.part2_of_2 (4 GB < ... ) on 2nd M-Disc DVD

        Parameters
        ----------
        zip -> str
            The full path to the zip
        split_size -> int
            The number in bytes the zip can be split on. For example, 25 GB = 25000000000000000
        overwrite -> bool
            The zip can be quite large, in the hundreds of GB's. In production scenarios, if this function works, then
            there is no need to keep the full zip produced by combining files and folders. Setting this to true creates
            this production validation.
        '''
        self.signals.progress_text.emit(f"Splitting size based on {split_size} ...")
        self.signals.progress.emit(0)
        total_zip_bytes = os.path.getsize(zip)
        self.signals.progress_text.emit(f"Total size of the zipe file: {utils.total_size_str(total_zip_bytes)}")
        num_splits = math.ceil(total_zip_bytes / split_size)
        self.signals.progress_text.emit(f"Number of parts: {num_splits}")
        bytes_per_part = math.ceil(total_zip_bytes / num_splits)
        self.signals.progress_text.emit(f"Max size per part: {utils.total_size_str(bytes_per_part)}")
        with open(zip, 'rb') as f:
            for i in range(num_splits):
                part_data = f.read(bytes_per_part)
                self.signals.progress.emit(1)
                if not part_data:
                    break
                part_file_name = f"{zip}.part{i + 1}_of_{num_splits}"
                with open(part_file_name, 'wb') as part_file:
                    part_file.write(part_data)
                self.signals.progress_text.emit(f"Created part: {part_file_name}")
                self.signals.progress.emit(((i + 1) / num_splits) * 100)
        if overwrite:
            self.signals.progress_text.emit(f"Deleting {zip} in order to save space.")
            os.remove(zip)  # remove full file

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

        page.setLayout(layout)
        page.setFinalPage(False)
        self.select_files_page_wizard = page
        return page

    def select_output_page(self):
        page = QWizardPage()
        page.setTitle("Output and Advanced Configuration")
        layout = QVBoxLayout()

        password_layout = QHBoxLayout()
        password_layout_label = QLabel("*(Optional)* Set password for ZIP file: ")
        password_layout_label.setTextFormat(Qt.MarkdownText)
        password_layout.addWidget(password_layout_label)
        password_button = QPushButton("Set Password")
        password_button.clicked.connect(self.set_password)
        password_layout.addWidget(password_button)
        layout.addLayout(password_layout)

        options_layout = QHBoxLayout()
        options_layout_label = QLabel("*(Optional)* Choose max ZIP split size:")
        options_layout_label.setTextFormat(Qt.MarkdownText)
        options_layout.addWidget(options_layout_label)
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

        self.start_zip_button = QPushButton("Compress and Save ZIP file")
        self.start_zip_button.clicked.connect(self.start_zip)
        self.start_zip_button.setEnabled(False)
        layout.addWidget(self.start_zip_button)

        self.output_status_text = QLineEdit()
        self.output_status_text.setPlaceholderText("Processing . . .")
        self.output_status_text.setReadOnly(True)
        page.registerField("output_status*", self.output_status_text)
        layout.addWidget(self.output_status_text)

        self.output_status_text.hide()
        page.setLayout(layout)
        page.setFinalPage(True)
        self.select_output_page_wizard = page
        self.select_output_page_wizard_layout = layout
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
            utils.error_popup("Please enter a password", {
                "exception": Exception("Password is empty"),
                "msg": "While creating the password for the ZIP file, the password field was empty"})
        elif pwd1 == pwd2:
            self.zip_config["password"] = pwd1
            dialog.accept()
        else:
            utils.error_popup("Passwords do not match", {
                "exception": Exception("Password Confirmation Failed. Please Try Again"),
                "msg": "The two password fields are different"})

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
            self.progress = QProgressBar()
            self.progress.setRange(0, 100)
            self.progress_text = QPlainTextEdit()
            self.progress_text.setReadOnly(True)
            self.select_output_page_wizard_layout.addWidget(self.progress)
            self.select_output_page_wizard_layout.addWidget(self.progress_text)
            zip_worker = ZipWorker(self.wizard, self.gui, self.zip_config)
            zip_worker.signals.progress.connect(self.progress.setValue)
            zip_worker.signals.progress_text.connect(self.progress_text.appendPlainText)
            zip_worker.signals.error.connect(lambda e: utils.error_popup(f"Error creating ZIP", e))
            zip_worker.signals.result.connect(self.output_status_text.setText)
            self.gui.threadpool.start(zip_worker)
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            self.signals.error.emit({"exception": e, "msg": msg})

    def select_files(self, var_name):
        file_names, _ = QFileDialog.getOpenFileNames(None, "Select Files")
        self.process_path(var_name, file_names)

    def select_dir(self, var_name):
        dir_name = QFileDialog.getExistingDirectory(None, "Select Folder")
        self.process_path(var_name, dir_name)

    def output_file(self):
        file_name, _ = QFileDialog.getSaveFileName(
            None, "Save ZIP File", "", "ZIP Files (*.zip)")
        if os.path.exists(file_name):
            popup = QMessageBox.warning(
                None, "File already exists", "Overwriting existing files is not permitted.")
            return popup
        else:
            if file_name.split(".")[-1].lower() != "zip":
                file_name += ".zip"
                print("Appended .zip to output path: ", file_name)
            self.output_path_text.setText(f"Output file path is {file_name}")
            self.zip_config["output_path"] = file_name
            self.start_zip_button.setEnabled(True)

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
                        self.zip_config['file_list_bytes'] += file_bytes
                        self.file_list_table.setItem(
                            current_row, 0, QTableWidgetItem(utils.total_size_str(file_bytes)))
                        self.file_list_table.setItem(current_row, 1, QTableWidgetItem(file_info.fileName()))
                        self.file_list_table.item(current_row, 1).setToolTip(file_info.absolutePath())
                else: # it's a folder
                    # get total size of folder
                    folder_size = sum(f.stat().st_size for f in pathlib.Path(path_name).rglob("*") if f.is_file())
                    self.zip_config['file_list_bytes'] += folder_size
                    self.file_list_table.insertRow(row_count)
                    self.file_list_table.setItem(
                        row_count, 0, QTableWidgetItem(utils.total_size_str(folder_size)))
                    self.file_list_table.setItem(row_count, 1, QTableWidgetItem(path_name))
                    self.file_list_table.item(row_count, 1).setToolTip("Full Folder Path")
            self.file_list_bytes_label.setText(f"Total Uncompressed Size: {utils.total_size_str(self.zip_config['file_list_bytes'])}")
