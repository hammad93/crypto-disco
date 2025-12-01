from pyFileFixity import structural_adaptive_ecc as pff_ecc
from PySide6.QtCore import Qt, QRunnable, Slot, QObject, Signal

class EccWorker(QRunnable):
    def __init__(self, file_list):
        super().__init__()
        self.file_list = file_list
    @Slot()
    def run(self):
        '''
        TODO
        file = 
        pff_ecc.main(
            argv = ["-i", file, "-d", "ecc.txt", "-l", "log.txt", "-g", "-f", "-v", "--ecc_algo", "3"]
        )
        '''
        pass
class EccWorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(float)
