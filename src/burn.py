from PySide6.QtCore import QRunnable, Slot, Qt, QFileInfo
from PySide6.QtWidgets import (QWizardPage, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit,
                               QDialog, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox, QProgressBar,
                               QPlainTextEdit)
import traceback
import config
import utils
import pathlib
import os
import subprocess
import platform

class BurnWorker(QRunnable):
    def __init__(self, wizard, gui, burn_config=False):
        super().__init__()
        self.wizard = wizard
        self.gui = gui
        self.signals = utils.WorkerSignals()
        self.os_type = platform.system()
        print(f"{self.os_type} detected")
        self.progress_text = QPlainTextEdit()
        self.progress_text.setReadOnly(True)
        self.burn_config = burn_config or {
            'iso_path': False
        }

    @Slot()
    def run(self):
        try:
            if self.os_type == "Darwin":
                self.run_mac()
            elif self.os_type == "Linux":
                self.run_linux()
            elif self.os_type == "Windows":
                self.run_windows()
            else:
                self.signals.error.emit({"exception": Exception("Unknown OS"), "msg": self.os_type})
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            self.signals.error.emit({"exception": e, "msg": msg})

    def select_iso_page(self):
        page = QWizardPage()
        page.setTitle("Select ISO Image")
        layout = QVBoxLayout()

        open_iso_layout = QHBoxLayout()
        label = QLabel("Select *.iso image")
        open_iso_layout.addWidget(label)
        select_iso_button = QPushButton("Open")
        select_iso_button.clicked.connect(lambda: self.select_iso())
        open_iso_layout.addWidget(select_iso_button)
        layout.addLayout(open_iso_layout)

        self.iso_file_text = QLineEdit()
        self.iso_file_text.setPlaceholderText("No *.iso image selected...")
        self.iso_file_text.setReadOnly(True)
        page.registerField("iso_path*", self.iso_file_text)
        layout.addWidget(self.iso_file_text)

        page.setLayout(layout)
        page.setFinalPage(False)
        self.select_iso_page_wizard = page
        return page

    def burn_drive_page(self):
        page = QWizardPage()
        page.setTitle("Burn ISO Image to Disc")
        layout = QVBoxLayout()

        if self.os_type != "Darwin": # Mac command doesn't require drive
            # TODO
            pass

        burn_button = QPushButton("Start Burn")
        burn_button.clicked.connect(self.start_burn)
        layout.addWidget(burn_button)
        layout.addWidget(self.progress_text)
        page.setLayout(layout)
        page.setFinalPage(True)
        self.burn_drive_page_wizard = page
        return page

    def start_burn(self):
        try:
            burn_worker = BurnWorker(wizard=self.wizard, gui=self.gui, burn_config={
                'iso_path': self.iso_path
            })
            burn_worker.signals.progress_text.connect(self.progress_text.appendPlainText)
            burn_worker.signals.error.connect(lambda e: utils.error_popup(f"Error creating ZIP", e))
            self.gui.threadpool.start(burn_worker)
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            self.signals.error.emit({"exception": e, "msg": msg})

    def select_iso(self):
        file_name, _ = QFileDialog.getOpenFileName(None, "Select ISO Image", "", "ISO Files (*.iso)")
        self.iso_path = file_name
        progress = "Selected ISO Image: " + self.iso_path
        self.progress_text.appendPlainText(progress)
        self.iso_file_text.setText(progress)

    def run_command(self, command, callback):
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as process:
            # Read from stdout in real-time
            for line in process.stdout:
                clean_line = line.strip()
                print(clean_line)
                callback(clean_line)
        return True

    def run_mac(self):
        '''
        References
        ----------
        https://ss64.com/mac/hdiutil.html
        '''
        burn_command = ["hdiutil", "burn", self.burn_config["iso_path"], "-puppetstrings"]
        print(f"Running command:\n{' '.join(burn_command)}")
        def process_log(l):
            self.signals.progress_text.emit(l)
        self.run_command(burn_command, process_log)
        print("ISO Burn Completed")
        return True

    def run_linux(self):
        # xorrecord -v dev=/dev/sr0 -dao ./test.iso
        #burn_command = ["hdiutil", "burn", self.burn_config["iso_path"], "-puppetstrings"]
        burn_command = ["xorrecord", "-v", "dev=/dev/sr0", "-dao", self.burn_config["iso_path"]]

        def process_log(l):
            self.signals.progress_text.emit(l)

        self.run_command(burn_command, process_log)
        print("ISO Burn Completed")

    def run_windows(self):
        burn_command = ["isoburn.exe", self.burn_config["iso_path"]]

        def process_log(l):
            self.signals.progress_text.emit(l)

        self.run_command(burn_command, process_log)
        self.signals.progress_text.emit("ISO Burn Completed")