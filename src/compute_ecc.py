from PySide6.QtCore import QRunnable, Slot, QObject, Signal
from datetime import datetime
import schedule
import time
import os
import ecc
import traceback

class EccWorker(QRunnable):
    def __init__(self, file_list):
        super().__init__()
        self.file_list = file_list
        self.signals = EccWorkerSignals()
        self.this_dir = os.path.dirname(__file__)
        self.working_dir = os.path.join(self.this_dir, "crypto-disco-ecc-files")
        self.current_file = None
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)
    @Slot()
    def run(self):
        '''
        References
        ----------
        - https://github.com/hammad93/crypto-disco/issues/4
        - https://github.com/lrq3000/pyFileFixity/blob/496b0518ebd51cdcd594fcd63a85066a13d1921c/pyFileFixity/structural_adaptive_ecc.py#L335
        '''
        # create current run dir path
        run_dir = os.path.join(self.working_dir, datetime.now().strftime('%Y%m%d%H%M%S'))
        self.signals.result.emit(run_dir)
        if not os.path.exists(run_dir):
            os.makedirs(run_dir)
        # iterate and create ecc files
        for file_metadata in self.file_list:
            # skip if ECC is unchecked
            if not file_metadata["ecc_checked"]:
                continue
            # main computation to generate ECC
            try:
                self.current_file = os.path.join(file_metadata['directory'], file_metadata['file_name'])
                self.signals.progress.emit(0)
                ecc.generate_ecc(input_path = self.current_file,
                                 output_path = run_dir,
                                 progress_function = self.update_progress)
                self.signals.progress.emit(100)
            except Exception as e:
                msg = traceback.format_exc()
                print(msg)
                self.signals.error.emit({"exception": e, "msg": msg})
                self.signals.cancel.emit()
                return False
        self.signals.finished.emit()
        return True

    def update_progress(self, progress, total, elapsed):
        '''
        Parameters
        ----------
        progress int
            The progress, units are bytes
        total int
            The total bytes needed to complete
        elapsed int
            The elapsed time in seconds
        '''
        self.signals.progress.emit((progress / total) * 100)
        filename = os.path.basename(self.current_file)
        details = f"[{[f['file_name'] for f in self.file_list].index(filename) + 1}/{len(self.file_list)}] "
        details += f"[{(progress / (1024**2)):.2f} MB/{(total / (1024**2)):.2f} MB] "
        details += f"[{((progress / (1024**2)) / elapsed):.2f} MB/s] "
        self.signals.progress_text.emit(f"Processing {filename}\n{details}")

class EccWorkerSignals(QObject):
    finished = Signal()
    cancel = Signal()
    error = Signal(object)
    result = Signal(object)
    progress = Signal(float)
    progress_text = Signal(str)
