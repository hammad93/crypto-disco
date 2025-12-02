from pyFileFixity import structural_adaptive_ecc as pff_ecc
from PySide6.QtCore import QRunnable, Slot, QObject, Signal
from datetime import datetime
import os

class EccWorker(QRunnable):
    def __init__(self, file_list, working_dir="./"):
        super().__init__()
        self.file_list = file_list
        self.signals = EccWorkerSignals()
        self.working_dir = f"{working_dir}crypto-disco-ecc-files"
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
        run_dir = f"{self.working_dir}/{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.signals.result.emit(run_dir)
        if not os.path.exists(run_dir):
            os.makedirs(run_dir)
        # iterate and create ecc files
        count = 0
        for file_metadata in self.file_list:
            # skip if ECC is unchecked
            if not file_metadata["ecc_checked"]:
                continue
            pff_ecc.main(
                argv = ["-i", f"{file_metadata['directory']}/{file_metadata['file_name']}",
                        "-d", f"{run_dir}/{file_metadata['file_name']}.txt",
                        "-l", f"{run_dir}/log.txt",
                        "-g", "--silent"]
            )
            count += 1
            self.signals.progress.emit(count)
        self.signals.finished.emit()
        return True
class EccWorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(float)