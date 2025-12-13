from PySide6.QtCore import QRunnable, Slot, QObject, Signal, Qt
from PySide6.QtWidgets import (QWizardPage, QVBoxLayout, QLabel, QPushButton, QFileDialog, QPlainTextEdit,
                               QCheckBox, QLineEdit, QProgressBar)
import traceback
import repair
import os

class RepairWorker(QRunnable):
    def __init__(self, wizard, gui, ecc_config=False):
        super().__init__()
        self.wizard = wizard
        self.gui = gui
        self.signals = RepairWorkerSignals()
        if ecc_config:
            self.ecc_config = ecc_config
        else:
            # set defaults
            self.ecc_config = {
                'only_erasures': False,
                'enable_erasures': False,
                'erasure_symbol': 0,
                'fast_check': True
            }

    @Slot()
    def run(self):
        try:
            repair.correct_errors(
                damaged=self.ecc_config['damaged'],
                repair_dir=self.ecc_config['repair_dir'],
                ecc_file=self.ecc_config['ecc_file'],
                only_erasures=self.ecc_config['only_erasures'],
                enable_erasures=self.ecc_config['enable_erasures'],
                erasure_symbol=self.ecc_config['erasure_symbol'],
                fast_check=self.ecc_config['fast_check'],
                callback=self.ecc_config['callback']
            )
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            self.signals.error.emit({"exception": e, "msg": msg})

    def select_file_page(self):
        self.select_corrupted_file_wizard = QWizardPage()
        self.select_corrupted_file_wizard.setTitle("Select File to Repair")
        layout = QVBoxLayout()
        label = QLabel("Please select the file you wish to repair:")
        layout.addWidget(label)

        select_file_button = QPushButton("Select File")
        select_file_button.clicked.connect(lambda: self.select_file("Corrupted File", "corrupted_file"))
        layout.addWidget(select_file_button)

        self.select_corrupted_file_text = QLineEdit()
        self.select_corrupted_file_text.setPlaceholderText("No file selected...")
        self.select_corrupted_file_text.setReadOnly(True)  # Make it read-only
        self.select_corrupted_file_wizard.registerField("corrupted_file*", self.select_corrupted_file_text)
        layout.addWidget(self.select_corrupted_file_text)

        self.select_corrupted_file_wizard.setLayout(layout)
        self.select_corrupted_file_wizard.setFinalPage(False)
        return self.select_corrupted_file_wizard

    def select_ecc_page(self):
        self.select_ecc_file_wizard = QWizardPage()
        self.select_ecc_file_wizard.setTitle("ECC Configuration")
        self.ecc_layout = QVBoxLayout()
        label = QLabel("Please select the error correcting code (.txt) for the file you wish to repair:")
        self.ecc_layout.addWidget(label)
        select_file_button = QPushButton("Select File")
        select_file_button.clicked.connect(lambda: self.select_file("Error Correcting File", "ecc_file"))
        self.ecc_layout.addWidget(select_file_button)
        # Default configuration collapsed
        advanced_button = QPushButton("Advanced Configuration")
        advanced_button.setCheckable(True)
        advanced_layout = QVBoxLayout()

        only_erasures_checkbox = QCheckBox("Enable only erasures correction (no errors)")
        only_erasures_checkbox.setChecked(self.ecc_config['only_erasures'])
        only_erasures_checkbox.stateChanged.connect(
            lambda state: self.ecc_config.update({'only_erasures': state == Qt.Checked})
        )
        advanced_layout.addWidget(only_erasures_checkbox)

        enable_erasures_checkbox = QCheckBox("Enable errors-and-erasures correction")
        enable_erasures_checkbox.setChecked(self.ecc_config['enable_erasures'])
        enable_erasures_checkbox.stateChanged.connect(
            lambda state: self.ecc_config.update({'enable_erasures': state == Qt.Checked})
        )
        advanced_layout.addWidget(enable_erasures_checkbox)

        erasure_symbol_label = QLabel("Erasure Symbol:")
        erasure_symbol_input = QLineEdit()
        erasure_symbol_input.setText(str(self.ecc_config['erasure_symbol']))
        erasure_symbol_input.textChanged.connect(
            lambda text: self.ecc_config.update({'erasure_symbol': text})
        )
        advanced_layout.addWidget(erasure_symbol_label)
        advanced_layout.addWidget(erasure_symbol_input)

        fast_check_checkbox = QCheckBox("Enable fast hash check")
        fast_check_checkbox.setChecked(self.ecc_config['fast_check'])
        fast_check_checkbox.stateChanged.connect(
            lambda state: self.ecc_config.update({'fast_check': state == Qt.Checked})
        )

        advanced_layout.addWidget(fast_check_checkbox)
        self.ecc_advanced_layout = advanced_layout
        # Logic to show/hide advanced configuration
        def toggle_advanced_config(self):
            if self.ecc_advanced_button.isChecked():
                self.ecc_layout.addLayout(self.ecc_advanced_layout)
            else:
                self.ecc_layout.removeItem(self.ecc_advanced_layout)
        self.ecc_advanced_button = advanced_button
        self.ecc_advanced_button.clicked.connect(lambda: toggle_advanced_config(self))
        self.ecc_layout.addWidget(self.ecc_advanced_button)

        self.select_ecc_file_text = QLineEdit()
        self.select_ecc_file_text.setPlaceholderText("No file selected...")
        self.select_ecc_file_text.setReadOnly(True)  # Make it read-only
        self.select_ecc_file_wizard.registerField("ecc_file*", self.select_ecc_file_text)
        self.ecc_layout.addWidget(self.select_ecc_file_text)

        self.select_ecc_file_wizard.setLayout(self.ecc_layout)
        self.select_ecc_file_wizard.setFinalPage(False)
        return self.select_ecc_file_wizard

    def select_repair_page(self):
        self.select_repair_dir_wizard = QWizardPage()
        self.select_repair_dir_wizard.setTitle("Process Repair")
        self.select_repair_dir_layout = QVBoxLayout()

        self.select_repair_dir_label = QLabel("Please select the output folder for the repaired file:")
        self.select_repair_dir_layout.addWidget(self.select_repair_dir_label)

        select_dir_button = QPushButton("Select folder")
        select_dir_button.clicked.connect(lambda: self.select_dir("Repair Output", "repair_dir"))
        self.select_repair_dir_layout.addWidget(select_dir_button)

        self.select_repair_dir_text = QLineEdit()
        self.select_repair_dir_text.setPlaceholderText("No folder selected...")
        self.select_repair_dir_text.setReadOnly(True)  # Make it read-only
        self.select_repair_dir_wizard.registerField("repair_dir*", self.select_repair_dir_text)
        self.select_repair_dir_layout.addWidget(self.select_repair_dir_text)

        start_repair_button = QPushButton("Start Repair")
        start_repair_button.clicked.connect(self.start_repair)
        self.select_repair_dir_layout.addWidget(start_repair_button)

        self.select_repair_output_text = QLineEdit()
        self.select_repair_output_text.setPlaceholderText("Processing repair . . .")
        self.select_repair_output_text.setReadOnly(True)  # Make it read-only
        self.select_repair_dir_wizard.registerField("repair_output*", self.select_repair_output_text)
        self.select_repair_dir_layout.addWidget(self.select_repair_output_text)
        self.select_repair_output_text.hide()

        self.select_repair_dir_wizard.setLayout(self.select_repair_dir_layout)
        self.select_repair_dir_wizard.setFinalPage(True)
        return self.select_repair_dir_wizard

    def start_repair(self):
        self.select_repair_output_text.show()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress_text = QPlainTextEdit()
        self.progress_text.setReadOnly(True)
        self.select_repair_dir_layout.addWidget(self.progress)
        self.select_repair_dir_layout.addWidget(self.progress_text)
        ecc_config = {
            "damaged": self.select_corrupted_file_wizard.field("corrupted_file"),
            "repair_dir": self.select_repair_dir_wizard.field("repair_dir"),
            "ecc_file": self.select_ecc_file_wizard.field("ecc_file"),
            "only_erasures": self.ecc_config['only_erasures'],
            "enable_erasures": self.ecc_config['enable_erasures'],
            "erasure_symbol": self.ecc_config['erasure_symbol'],
            "fast_check": self.ecc_config['fast_check']
        }
        repair_worker = RepairWorker(self.wizard, self.gui, ecc_config)
        repair_worker.signals.error.connect(lambda e: self.error_popup(f"Error repairing{self.corrupted_file}", e))
        repair_worker.signals.progress.connect(self.progress.setValue)
        repair_worker.signals.progress_text.connect(self.progress_text.setPlainText)
        repair_worker.signals.finished.connect(self.select_repair_output_text.setText)
        repair_worker.repair_output_path = self.repair_output_path
        def callback(s, processed, total, message=""):
            progress_value = (processed / total) * 100
            s.signals.progress.emit(int(progress_value))
            if progress_value == 100:
                print("Repair Complete")
                s.signals.finished.emit(f"Repair complete. Saved to {s.repair_output_path}")
            if message != "":
                s.signals.progress_text.emit(message)
        repair_worker.ecc_config.update({'callback': lambda x,y,z: callback(repair_worker, x, y, z)})
        self.gui.threadpool.start(repair_worker)

    def select_file(self, title, var_name):
        file_name, _ = QFileDialog.getOpenFileName(None,title)
        self.process_path(var_name, file_name)

    def select_dir(self, title, var_name):
        dir_name = QFileDialog.getExistingDirectory(None,title)
        self.process_path(var_name, dir_name)
        if dir_name:
            self.repair_output_path = os.path.join(
                dir_name, os.path.basename(self.select_corrupted_file_wizard.field("corrupted_file")))

    def process_path(self, var_name, path_name):
        if path_name:
            getattr(self, f"select_{var_name}_text").setText(path_name)

class RepairWorkerSignals(QObject):
    finished = Signal(str)
    cancel = Signal()
    error = Signal(object)
    result = Signal(object)
    progress = Signal(float)
    progress_text = Signal(str)
