from PySide6.QtCore import QRunnable, Slot, QObject, Signal, Qt, QTimer, QThreadPool
from PySide6.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox,
                               QCheckBox, QLineEdit, QProgressDialog)
import repair

class RepairWorker(QRunnable):
    def __init__(self, window, thread_pool, ecc_config=False):
        super().__init__()
        self.window = window
        self.threadpool = thread_pool
        self.selected_file = None
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
                damaged=self.ecc_config['self.selected_file'],
                repair_dir=self.ecc_config['output_dir'],
                ecc_file=self.ecc_config['ecc_file'],
                only_erasures=self.ecc_config['only_erasures'],
                enable_erasures=self.ecc_config['enable_erasures'],
                erasure_symbol=self.ecc_config['erasure_symbol'],
                fast_check=self.ecc_config['fast_check'],
                callback=self.ecc_config['callback']
            )
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Repair failed: {str(e)}")

    def select_file_page(self):
        page = QWizardPage()
        page.setTitle("Select File to Repair")
        layout = QVBoxLayout()
        label = QLabel("Please select the file you wish to repair:")
        layout.addWidget(label)

        select_file_button = QPushButton("Select File")
        select_file_button.clicked.connect(self.select_file)
        layout.addWidget(select_file_button)

        page.setLayout(layout)
        page.setFinalPage(False)  # Indicates that this is not the final page
        return page

    def select_ecc_page(self):
        page = QWizardPage()
        page.setTitle("ECC Configuration")

        layout = QVBoxLayout()

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

        # Logic to show/hide advanced configuration
        def toggle_advanced_config():
            if advanced_button.isChecked():
                layout.addLayout(advanced_layout)
            else:
                while advanced_layout.count():
                    item = advanced_layout.takeAt(0)
                    item.widget().deleteLater()

        advanced_button.clicked.connect(toggle_advanced_config)
        layout.addWidget(advanced_button)

        page.setLayout(layout)
        page.setFinalPage(False)
        return page

    def process_repair_page(self):
        page = QWizardPage()
        page.setTitle("Process Repair")

        layout = QVBoxLayout()

        output_dir_label = QLabel("Output Directory:")
        layout.addWidget(output_dir_label)

        output_dir_input = QLineEdit()
        layout.addWidget(output_dir_input)

        start_repair_button = QPushButton("Start Repair")
        layout.addWidget(start_repair_button)

        def start_repair():
            output_dir = output_dir_input.text()
            if not output_dir:
                QMessageBox.warning(None, "Warning", "Please specify an output directory.")
                return

            self.start_progress_dialog(output_dir)

        start_repair_button.clicked.connect(start_repair)

        page.setLayout(layout)
        page.setFinalPage(True)
        return page

    def start_progress_dialog(self, output_dir):
        progress_dialog = QProgressDialog("Repairing file...", "Abort", 0, 100, None)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(False)

        def callback(processed, total, elapsed_time):
            progress_dialog.setValue(int((processed / total) * 100))
            progress_dialog.setLabelText(
                f"Repairing... {processed}/{total} bytes processed. Time elapsed: {elapsed_time:.2f}s")
        self.ecc_config = {
            "damaged": self.selected_file,
            "repair_dir": output_dir,
            "ecc_file": "path/to/ecc_file",  # Update with actual ECC file path
            "only_erasures": self.ecc_config['only_erasures'],
            "enable_erasures": self.ecc_config['enable_erasures'],
            "erasure_symbol": self.ecc_config['erasure_symbol'],
            "fast_check": self.ecc_config['fast_check'],
            "callback": callback
        }
        repair_worker = RepairWorker(self.thread_pool, self.ecc_config)
        self.threadpool.start(repair_worker)
        progress_dialog.exec()

    def select_file(self):
        file_name, _ = QFileDialog.getOpenFileNames(self.window,"Select a file to repair")
        if file_name:
            self.selected_file = file_name
            QMessageBox.information(None, "File Selected", f"File selected: {file_name}")

class RepairWorkerSignals(QObject):
    finished = Signal()
    cancel = Signal()
    error = Signal(object)
    result = Signal(object)
    progress = Signal(float)
    progress_text = Signal(str)
