from PySide6.QtCore import QRunnable, Slot, Qt, QFileInfo
from PySide6.QtWidgets import (QWizardPage, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit,
                               QDialog, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox, QProgressBar,
                               QPlainTextEdit)
import traceback

from nuitka.build.inline_copy.jinja2.jinja2.lexer import TOKEN_DOT

import config
import utils
import pathlib
import os
import subprocess
import platform
import pyffmpeg

class PlaybackWorker(QRunnable):
    def __init__(self, wizard, gui, playback_config=False):
        super().__init__()
        self.wizard = wizard
        self.gui = gui
        self.signals = utils.WorkerSignals()
        self.playback_config = playback_config or {}

    @Slot()
    def run(self):
        try:
            # TODO
            pass
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            self.signals.error.emit({"exception": e, "msg": msg})

    def start(self):
        playback_config = {
            'output': self.output_file_path
        }
        playback_worker = PlaybackWorker(self.wizard, self.gui, playback_config)
        playback_worker.signals.progress.connect(self.mux_progress_bar.setValue)
        playback_worker.signals.progress_text.connect(self.progress_text.appendPlainText)
        playback_worker.signals.error.connect(lambda e: utils.error_popup("Error Muxing Media for Playback", e))
        playback_worker.signals.result.connect(self.mux_label.setText)
        self.gui.threadpool.start(playback_worker)


    def probe_files_page(self):
        page = QWizardPage()
        page.setTitle("Files Validation")
        layout = QVBoxLayout()

        label = QLabel("Probing files, please click start. All files must be validated before continuing.")
        layout.addWidget(label)

        probe_progress = QProgressBar()
        probe_progress.setRange(0, 100)
        layout.addWidget(probe_progress)

        self.probe_processed_text = QLineEdit()
        self.probe_processed_text.setPlaceholderText("Processing . . .")
        self.probe_processed_text.setReadOnly(True)
        # prevent going to next page until probing is complete
        page.registerField("probe*", self.probe_processed_text)

        probe_progress_text = QPlainTextEdit()
        probe_progress_text.setReadOnly(True)
        layout.addWidget(probe_progress_text)

        probe_start_button = QPushButton("Start")
        probe_start_button.clicked.connect(self.probe_files)
        layout.addWidget(probe_start_button)

        page.setLayout(layout)
        page.setFinalPage(False)
        self.probe_files_page_wizard = page
        return page

    def mux_page(self):
        page = QWizardPage()
        page.setTitle("Converting and Muxing Files to Playback .iso Image")
        layout = QVBoxLayout()

        # label instructing user to select output file
        label = QLabel("Select output file location:")
        layout.addWidget(label)
        # select output iso button as "Open"
        button = QPushButton("Open")
        button.clicked.connect(self.select_output_file)
        layout.addWidget(button)
        # progress bar
        self.mux_progress_bar = QProgressBar()
        self.mux_progress_bar.setRange(0, 100)
        layout.addWidget(self.mux_progress_bar)
        # text box for progress updates
        self.progress_text = QPlainTextEdit()
        self.progress_text.setReadOnly(True)
        layout.addWidget(self.progress_text)
        # start button that runs the new thread
        start_button = QPushButton("Start")
        start_button.clicked.connect(self.start)
        start_button.setEnabled(False)
        self.start_button = start_button
        layout.addWidget(self.start_button)
        # hidden label that changes to signal everything is done
        self.mux_label = QLineEdit()
        self.mux_label.setPlaceholderText("Processing . . .")
        self.mux_label.setReadOnly(True)
        page.registerField("mux*", self.mux_label)

        page.setFinalPage(True)
        self.mux_page_wizard = page
        return page

    def select_output_file(self):
        file_name, _ = QFileDialog.getSaveFileName(
            None, "Save ZIP File", "", "ZIP Files (*.zip)")
        if os.path.exists(file_name):
            popup = QMessageBox.warning(
                None, "File already exists", "Overwriting existing files is not permitted.")
            return popup
        else:
            self.output_file_path = file_name
            self.start_button.setEnabled(True)

    def probe_files(self):
        for file in self.gui.file_list:
            path = os.path.join(file['directory'], file['file_name'])
            self.probe_progress_text.appendPlainText(f"Probing {path} . . .")
            try:
                probe = pyffmpeg.FFprobe(path)
                self.probe_progress_text.appendPlainText(f"{probe.metadata}\nDone probing {file['file_name']}")
            except Exception as e:
                self.probe_progress_text.appendPlainText(f"Error when opening {path} with pyffmpeg.\n{e}")
                return False
        self.probe_processed_text.setPlaceholderText("Done.")
        return True