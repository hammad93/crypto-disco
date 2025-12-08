from pyFileFixity import structural_adaptive_ecc as pff_ecc
from PySide6.QtCore import QRunnable, Slot, QObject, Signal
from datetime import datetime
import schedule
import time
import os

class EccWorker(QRunnable):
    def __init__(self, file_list):
        super().__init__()
        self.file_list = file_list
        self.signals = EccWorkerSignals()
        self.this_dir = os.path.dirname(__file__)
        self.working_dir = os.path.join(self.this_dir, "crypto-disco-ecc-files")
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
            pff_ecc.main(
                argv=["-i", os.path.join(file_metadata['directory'], file_metadata['file_name']),
                      "-d", os.path.join(run_dir, file_metadata['file_name']) + ".txt",
                      "-l", os.path.join(run_dir, "log.txt"),
                      "-g", "--silent"]
            )
        self.signals.finished.emit()
        return True

class EccMonitor(QRunnable):
    def __init__(self, ecc_count, ecc_dir, log_filename="log.txt", progress_rate=100):
        super().__init__()
        self.ecc_count = ecc_count
        self.ecc_dir = ecc_dir
        self.log_filename = log_filename
        self.progress_rate = progress_rate
        self.progress_complete = False
        self.signals = EccWorkerSignals()
    @Slot()
    def run(self):
        '''
        This function monitors the logs and produces progress signals and other tasks

        References
        ----------
        https://schedule.readthedocs.io/en/stable/
        '''
        schedule.every(2).seconds.do(self.update_progress)
        while not self.progress_complete:
            schedule.run_pending()
            time.sleep(1)
    def update_progress(self):
        # open logs and read all contents
        with open(os.path.join(self.ecc_dir, self.log_filename), "r") as log_file:
            log_lines = log_file.readlines()
        # calculate how many are completed
        complete_msg = "All done! Total number of files processed: 1"
        complete_count = sum(complete_msg in line for line in log_lines)
        total_progress = complete_count * self.progress_rate
        details = "" # to be included later
        if complete_count < self.ecc_count:
            for line in log_lines[::-1]: # from most recently appended in logs
                if "%|" in line: # e.g. 93%|#########3| 1.76G/1.88G [15:00<00:46, 2.71MB/s]
                    total_progress += int(line.strip().split("%")[0])
                    details = f'\n{line.split("|")[-1]}'
                    break
                if complete_msg in line: # end of previous file
                    break
        else:
            self.progress_complete = True
        self.signals.progress_text.emit(f'{complete_count + 1} out of {self.ecc_count} file(s) ECC processing . . .'
                                        f'{details}')
        self.signals.progress.emit(total_progress)

class EccWorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(float)
    progress_text = Signal(str)