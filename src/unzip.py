from PySide6.QtCore import QRunnable, Slot, QObject, Signal
import os
import utils

class UnzipWorker(QRunnable):
    def __init__(self, files):
        super().__init__()
        self.files = files
        self.signals = utils.WorkerSignals()

    @Slot()
    def run(self):
        # TODO
        pass

    def decompress_zip(self, paths):
        # get first file to see what kind of operation we need to perform
        files = [os.path.basename(f) for f in paths]
        dir = os.path.dirname(paths[0])
        test_file = files[0]
        test_filename = os.path.basename(test_file)
        if test_filename.endswith(".zip"):
            if len(files) > 1:
                # TODO decompress 1 at a time, error out
                return False
            else:
                # TODO decompress zip file
                pass
        elif 'part' in test_filename.split('.')[-1]:
            # check to see if all parts are selected and prompt for more otherwise
            combined_filename = test_filename.split('.part')[0]
            total_parts = int(test_filename.split('_of_')[-1])
            expected_files = [
                os.path.join(dir, f"{combined_filename}.part{(i + 1)}_of_{total_parts}") for i in range(total_parts)]
            print(f"Expected files for ZIP part assembly: {expected_files}")
            if not all(os.path.exists(expected) for expected in expected_files):
                # TODO error message
                return False
            with open(os.path.join(dir, combined_filename), 'wb') as f:
                for expected in expected_files:
                    with open(expected, 'rb') as part_file:
                        f.write(part_file.read())