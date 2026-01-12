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
import traceback

from PySide6 import QtGui
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QVBoxLayout, QPushButton, QTableWidget, QComboBox, QTextEdit, QMessageBox,
    QTableWidgetItem, QLabel, QWidget, QCheckBox, QHBoxLayout, QProgressDialog, QWizard
)
from PySide6.QtCore import Qt, QFileInfo, QThreadPool, QFile
import os
import iso
import zip
import unzip
import burn
import utils
import config
import compute_ecc
import compute_repair
import visualization
from pprint import pformat, pprint
import assets # Might look like an unresolved reference but it isn't, see PySide6 *.qrc

class crypto_disco(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app # QApplication
        self.resize(config.app_width, config.app_height)
        self.disc_icon = QtGui.QIcon(config.disc_icon)
        self.default_files = config.default_files
        self.setWindowIcon(self.disc_icon)
        self.setWindowTitle(config.window_title)
        self.this_dir = os.path.dirname(__file__)
        self.setup_menu_bar()
        # Initialize variables
        self.current_ecc_dir = None
        self.count_ecc = 0
        self.total_size_bytes = 0
        self.file_list = [] # Store a dictionary of metadata of files
        self.file_list.extend(self.create_default_files())
        # Create main layout and central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.origin_layout = QHBoxLayout(self.central_widget)
        layout = QVBoxLayout()
        self.origin_layout.addLayout(layout)
        # Create add files button
        self.add_files_button = QPushButton("Add File(s)", self)
        self.add_files_button.clicked.connect(self.add_files)
        layout.addWidget(self.add_files_button)
        # Create Repair Button
        self.repair_button = QPushButton("Repair File Assistant", self)
        self.repair_button.clicked.connect(self.run_repair_wizard)
        self.wand_icon = QtGui.QIcon(config.wand_icon)
        self.repair_button.setIcon(self.wand_icon)
        layout.addWidget(self.repair_button)
        # Create table widget
        self.table_cols = config.table_cols
        self.table = QTableWidget(self)
        self.table.setColumnCount(len(self.table_cols))
        self.table.setHorizontalHeaderLabels(self.table_cols)
        self.table.setColumnWidth(self.table_cols.index("File Size"), config.file_size_col_w)
        self.table.setColumnWidth(self.table_cols.index("ECC"), config.ecc_col_w)
        self.table.setColumnWidth(self.table_cols.index("Clone"), config.clone_col_w)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumWidth(config.table_width)
        layout.addWidget(self.table)
        # Create the horizontal layout for disc type and media playback checkbox
        run_layout = QHBoxLayout()
        # Create combo box for disc sizes
        self.disc_size_combo = QComboBox(self)
        self.disc_size_list = config.disc_types
        self.disc_size_combo.addItems(self.disc_size_list)
        self.default_disc_type = config.default_disc_type
        self.disc_size_combo.setCurrentIndex(self.disc_size_list.index(self.default_disc_type))
        self.disc_size_combo.currentTextChanged.connect(self.update_totals)
        run_layout.addWidget(self.disc_size_combo)
        # Create checkbox for media playback image
        self.media_playback = QCheckBox(text="Media Playback")
        self.media_playback.setChecked(False)
        run_layout.addWidget(self.media_playback)
        # Create run application button
        self.run_button = QPushButton("Generate .ISO Image", self)
        self.run_button.clicked.connect(self.run_application)
        self.run_icon = QtGui.QIcon(config.download_icon)
        self.run_button.setIcon(self.run_icon)
        # Create burn ISO button
        self.burn_button = QPushButton("Burn to M-DISC", self)
        self.burn_icon = QtGui.QIcon(self.disc_icon)
        self.burn_button.clicked.connect(self.run_burn)
        self.burn_button.setIcon(self.burn_icon)
        # Extract ZIP Button
        self.extract_zip_button = QPushButton("Extract ZIP", self)
        self.extract_zip_button.clicked.connect(self.run_unzip)
        # Create ZIP Button
        self.zip_button = QPushButton("Create ZIP", self)
        self.zip_button.clicked.connect(self.run_zip_wizard)
        # Create Split ZIP Button
        self.split_button = QPushButton("Split ZIP", self)
        self.split_button.clicked.connect(self.run_split_wizard)
        # Add visualization
        self.nested_donuts = visualization.NestedDonuts(self.file_list, self.disc_size_combo.currentText())
        # Combine layouts
        utility_btn_layout = QHBoxLayout()
        utility_btn_layout.addWidget(self.zip_button)
        utility_btn_layout.addWidget(self.split_button)
        utility_btn_layout.addWidget(self.extract_zip_button)
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.run_button)
        right_layout.addWidget(self.burn_button)
        right_layout.addLayout(utility_btn_layout)
        right_layout.addWidget(self.nested_donuts)
        self.origin_layout.addLayout(right_layout)
        layout.addLayout(run_layout)
        # Create label for total size
        self.total_size_label = QLabel(f"{config.total_size_prefix} 0 ", self)
        layout.addWidget(self.total_size_label)
        # Thread management
        self.threadpool = QThreadPool()

    def setup_menu_bar(self):
        # Create menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        about_menu = menu_bar.addMenu("About")
        checkboxes_menu = menu_bar.addMenu("Checkboxes")
        # Add actions to File menu
        add_files_action = QtGui.QAction("Add files to staged .iso", self)
        add_files_action.triggered.connect(self.add_files)
        file_menu.addAction(add_files_action)
        clear_files_action = QtGui.QAction("Clear All files from staged .iso", self)
        clear_files_action.triggered.connect(self.clear_files)
        file_menu.addAction(clear_files_action)
        # Checkboxes operations
        uncheck_ecc = QtGui.QAction("Uncheck All ECC", self)
        uncheck_ecc.triggered.connect(lambda: self.change_check_col(False, "ECC"))
        checkboxes_menu.addAction(uncheck_ecc)
        uncheck_clone = QtGui.QAction("Uncheck All Clone", self)
        uncheck_clone.triggered.connect(lambda: self.change_check_col(False, "Clone"))
        checkboxes_menu.addAction(uncheck_clone)
        uncheck_ecc = QtGui.QAction("Check All ECC", self)
        uncheck_ecc.triggered.connect(lambda: self.change_check_col(True, "ECC"))
        checkboxes_menu.addAction(uncheck_ecc)
        uncheck_clone = QtGui.QAction("Check All Clone", self)
        uncheck_clone.triggered.connect(lambda: self.change_check_col(True, "Clone"))
        checkboxes_menu.addAction(uncheck_clone)
        # Add action to About menu
        about_action = QtGui.QAction("About", self)
        file = QFile(":/assets/README.md")
        file.open(QFile.ReadOnly | QFile.Text)
        self.readme = file.readAll().data().decode('utf-8')
        file.close()
        about_action.triggered.connect(self.show_readme)
        about_menu.addAction(about_action)

    def change_check_col(self, change, col_name):
        state = None
        if change == True:
            state = Qt.Checked
        elif change == False:
            state = Qt.Unchecked
        for row in range(self.table.rowCount()):
            self.table.cellWidget(row, self.table_cols.index(col_name)).layout().itemAt(0).widget().setCheckState(state)

    def show_readme(self):
        self.about_box = QTextEdit()
        self.about_box.resize(500,300)
        self.about_box.setReadOnly(True)
        self.about_box.setMarkdown(self.readme)
        self.about_box.setWindowTitle("README.md Contents")
        self.about_box.show()

    def clear_files(self):
        self.table.setRowCount(0)
        self.total_size_bytes = 0
        self.file_list = [f for f in self.file_list if f["default_file"]]
        self.update_totals()

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
            size_str = utils.total_size_str(file_size)
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
            self.file_list.append(self.create_file_data(directory, file_name, file_size))
            current_row += 1
        # change the index labels to match visualization
        self.table.setVerticalHeaderLabels([str(i + len(self.default_files)) for i in range(len(self.file_list))])
        # Update total size display
        self.update_totals()

    def update_file_list_state(self, row, state, col_name):
        key = f"{col_name.lower()}_checked" # relevant key in dictionary
        index = row + len(self.default_files)
        if state == 2:
            self.file_list[index][key] = True
        else:
            self.file_list[index][key] = False
        self.update_totals()

    def update_totals(self):
        self.current_disc_type = self.disc_size_combo.currentText()
        self.total_size_clones = utils.get_clones_size(self.file_list, self.current_disc_type)
        self.total_size_label.setText(
            f"[{config.total_size_prefix} {utils.total_size_str(self.total_size_bytes)}]  "
            f"[Clones: {utils.total_size_str(self.total_size_clones)}]  "
            f"[ECC: {utils.total_size_str(utils.get_total_ecc_sizes(self.file_list))}]"
        )
        self.nested_donuts.update_all(self.file_list, self.current_disc_type, self.total_size_clones)

    def set_ecc_dir(self, ecc_dir):
        self.current_ecc_dir = ecc_dir

    def create_file_data(self, directory, file_name, file_size,
                         ecc_checked=True, clone_checked=True, default_file=False):
        data = {
            "directory": directory,
            "file_name": file_name,
            "file_size": file_size,
            "size_str": utils.total_size_str(file_size),
            "ecc_checked": ecc_checked,
            "clone_checked": clone_checked,
            "default_file": default_file,
        }
        return data

    def create_default_files(self):
        # setup default files here
        default_file_dir = os.path.join(self.this_dir, "default_files")
        if not os.path.exists(default_file_dir):
            os.makedirs(default_file_dir)
        default_file_list = []
        for default_file in self.default_files:
            #print(f"Processing default file {default_file}")
            file = QFile(default_file)
            file.open(QFile.ReadOnly)
            data = file.readAll()
            file.close()
            default_file_name = default_file.split("/")[-1]
            default_file_path = os.path.join(default_file_dir, default_file_name)
            with open(default_file_path, "wb") as f:
                f.write(data)
            # include in file list if it's not already there
            if default_file_name not in [f['file_name'] for f in self.file_list]:
                default_file_info = QFileInfo(file)
                default_file_size = default_file_info.size()
                default_file_list.append(self.create_file_data(default_file_dir, default_file_name, default_file_size,
                                                               clone_checked=False, default_file=True))
        return default_file_list

    def validate_disc_type(self):
        print("Validating Disc type . . . . ")
        # if there are no files
        file_list = [f for f in self.file_list if not f['default_file']]
        print(pformat(file_list))
        if len([f for f in self.file_list if not f['default_file']]) < 1:
            utils.error_popup("No files selected", {"exception": Exception("No files selected"),
                                                          "msg": f"File list: {self.file_list}"})
            return False
        else:
            print("No file selected pass")
        # validate whether the current file list will fit into the selected disc type
        disc_type_limit_bytes = utils.disc_type_bytes(self.disc_size_combo.currentText())
        remaining_bytes = disc_type_limit_bytes - self.total_size_bytes
        if remaining_bytes < 0:
            # total file sizes exceed usable bytes
            utils.error_popup("Exceeded usable file size", err={
                "exception": Exception("Total file size exceeds usable disc type"),
                "msg": (f"Disc type: {self.disc_size_combo.currentText()}\n"
                        f"Dis type size limit: {utils.total_size_str(disc_type_limit_bytes)}\n"
                        f"Current Total Size: {utils.total_size_str(self.total_size_bytes)}\n"
                        f"Exceeded bytes: {self.total_size_bytes - disc_type_limit_bytes}\n"
                        f"File list: \n{'\n'.join([pformat(f) for f in self.file_list])}")
            })
            return False
        else:
            print("File Size of ISO pass")
        clones_total_bytes = sum([f['file_size'] for f in self.file_list if f["clone_checked"]])
        if clones_total_bytes > remaining_bytes:
            utils.error_popup("Not enough space remaining for at least 1 clone for all checked clone files",
                                    err={"exception": Exception("Not enough space remaining for clones"),
                                         "msg": f"Files checked for clones:\n{'\n'.join(
                                             [pformat(f) for f in self.file_list if f['clone_checked']])}"})
            return False
        else:
            print("Number of Clones pass")
        return True

    def run_application(self):
        '''
        Prompt user for output ISO file path
        '''
        # validate files
        print("Button Clicked")
        validate = self.validate_disc_type()
        print(f"Validation Results: {validate}")
        if not validate:
            return validate
        output_path, filter = QFileDialog.getSaveFileName(
            None, "Save ISO", "", "ISO Files (*.iso)")
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
        print(f"Number of ECC files: {self.count_ecc}")
        if self.count_ecc > 0:
            # Display progress for ECC processing
            print("Processing error correcting codes (ECC) . . .")
            self.ecc_progress_dialog = QProgressDialog("Processing ECC...",
                                                  "Cancel", 0, 100, self)
            self.ecc_progress_dialog.setWindowModality(Qt.WindowModal)
            self.ecc_progress_dialog.setValue(0)
            ecc_worker = compute_ecc.EccWorker(self.file_list)
            # set ecc directory
            ecc_worker.signals.result.connect(self.set_ecc_dir)
            # after ECC is done, save out to ISO
            ecc_worker.signals.finished.connect(self.run_save_iso)
            ecc_worker.signals.progress.connect(self.ecc_progress_dialog.setValue)
            ecc_worker.signals.progress_text.connect(self.ecc_progress_dialog.setLabelText)
            # define error handling
            ecc_worker.signals.error.connect(
                lambda err: utils.error_popup("Failed Processing Error Correcting Codes (ECC)", err))
            ecc_worker.signals.cancel.connect(self.ecc_progress_dialog.cancel)
            self.ecc_progress_dialog.canceled.connect(ecc_worker.cancel_task)
            self.threadpool.start(ecc_worker)
        else:
            self.run_save_iso()

    def run_save_iso(self):
        print("Creating .iso file...")
        # Display progress bar for saving ISO
        worker = iso.IsoWorker(
            self.output_path, self.file_list, self.current_ecc_dir, self.disc_size_combo.currentText())
        progress_dialog = QProgressDialog("Saving ISO...", "Cancel", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setValue(0)
        progress_dialog.setMinimumDuration(0)
        worker.signals.progress.connect(progress_dialog.setValue)
        worker.signals.progress_end.connect(progress_dialog.setMaximum)
        worker.signals.progress_text.connect(progress_dialog.setLabelText)
        worker.signals.error.connect(
            lambda err: utils.error_popup(f"Failed to Create {self.output_path} Image", err))
        worker.signals.result.connect(
            lambda info_list: utils.info_popup(info_list[0], info_list[1], info_list[2])
        )
        worker.signals.cancel.connect(progress_dialog.cancel)
        progress_dialog.canceled.connect(worker.cancel_task)
        progress_dialog.forceShow()
        self.threadpool.start(worker)
        #cleanup
        self.file_list = [f for f in self.file_list if not f['default_file']]

    def run_repair_wizard(self):
        print("Starting repair wizard...")
        try:
            wizard = QWizard()
            wizard_worker = compute_repair.RepairWorker(wizard, self)
            wizard_worker.wizard.addPage(wizard_worker.select_file_page())
            wizard_worker.wizard.addPage(wizard_worker.select_ecc_page())
            wizard_worker.wizard.addPage(wizard_worker.select_repair_page())
            wizard_worker.wizard.show()
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            utils.error_popup("Error Applying ECC", {
                "exception": e,
                "msg": msg
            })

    def run_zip_wizard(self):
        print("Starting zip wizard...")
        try:
            wizard = QWizard()
            wizard_worker = zip.ZipWorker(wizard, self)
            wizard_worker.wizard.addPage(wizard_worker.select_files_page())
            wizard_worker.wizard.addPage(wizard_worker.select_output_page())
            wizard_worker.wizard.show()
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            utils.error_popup("Error Creating ZIP", {
                "exception": e,
                "msg": msg
            })

    def run_split_wizard(self):
        print("Starting split wizard...")
        try:
            wizard = QWizard()
            wizard_worker = zip.SplitZipWorker(wizard, self)
            wizard_worker.wizard.addPage(wizard_worker.select_zip_page())
            wizard_worker.wizard.addPage(wizard_worker.split_zip_page())
            wizard_worker.wizard.show()
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            utils.error_popup("Error Splitting ZIP", {
                "exception": e,
                "msg": msg
            })

    def run_unzip(self):
        try:
            file_names, _ = QFileDialog.getOpenFileNames(None, "Select Files")
            print(file_names)
            if len(file_names) < 1:
                return
            worker = unzip.UnzipWorker(file_names)
            progress_dialog = QProgressDialog("Extracting ZIP...", "Cancel", 0, 100, self)
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setValue(0)
            worker.signals.progress.connect(progress_dialog.setValue)
            worker.signals.progress_end.connect(progress_dialog.setMaximum)
            worker.signals.progress_text.connect(progress_dialog.setLabelText)
            worker.signals.error.connect(
                lambda err: utils.error_popup(f"Failed to Extract {file_names}", err))
            worker.signals.request_pwd.connect(lambda: utils.pwd_dialogue(worker.signals.retrieve_pwd))
            worker.signals.cancel.connect(progress_dialog.cancel)
            progress_dialog.canceled.connect(worker.cancel_task)
            progress_dialog.show()
            self.threadpool.start(worker)
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            utils.error_popup("Error Extracting ZIP", {
                "exception": e,
                "msg": msg
            })

    def run_burn(self):
        print("Starting burn wizard...")
        try:
            wizard = QWizard()
            wizard_worker = burn.BurnWorker(wizard, self)
            wizard_worker.wizard.addPage(wizard_worker.select_iso_page())
            wizard_worker.wizard.addPage(wizard_worker.burn_drive_page())
            wizard_worker.wizard.show()
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            utils.error_popup("Error Burning ISO Image", {
                "exception": e,
                "msg": msg
            })