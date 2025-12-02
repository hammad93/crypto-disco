import pycdlib
from PySide6.QtCore import Qt, QRunnable, Slot, QObject, Signal

class IsoWorker(QRunnable):
    def __init__(self, output_path, file_list):
        super().__init__()
        self.output_path = output_path
        self.file_list = file_list
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        '''
        For iso_path,
        In standard ISO interchange level 3, filenames have a maximum of 30 characters, followed by a required
        dot, followed by an extension, followed by a semicolon and a version. The filename and the extension are
        both optional, but one or the other must exist. Only uppercase letters, numbers, and underscore are
        allowed for either the name or extension. If any of these rules are violated, PyCdlib will
        throw an exception.
        '''
        print("Creating .iso file...")
        output_iso = pycdlib.PyCdlib()
        # https://clalancette.github.io/pycdlib/pycdlib-api.html#PyCdlib-new
        # Interchange 3 is recommended
        output_iso.new(interchange_level=3, joliet=3, rock_ridge="1.09", xa=True)
        for file_metadata in self.file_list:
            file_path = f'{file_metadata["directory"]}/{file_metadata["file_name"]}'
            print(f'\tFile Path: {file_path}')
            print(f'\t\tSize: {file_metadata["size_str"]}')
            print(f'\t\tECC: {file_metadata["ecc_checked"]}')
            iso_name = file_metadata["file_name"].split(".")[0].upper()
            # sanitize iso name
            for char in iso_name:
                if (not char.isalnum()) and (char != "_"):
                    iso_name = iso_name.replace(char, "")
            iso_ext = self.get_ext(file_metadata["file_name"]).upper()
            joliet_max = 64
            if len(file_metadata["file_name"]) > joliet_max:  # case where joliet name is longer than 64 characters
                # keep file extension
                joliet_ext = self.get_ext(file_metadata["file_name"])
                joliet_name = file_metadata["file_name"][:-len(joliet_ext)]
                joliet_path = f"/{joliet_name}{joliet_ext}"
            else:
                joliet_path = f'/{file_metadata["file_name"]}'
            output_iso.add_file(file_path,
                                    iso_path=f"/{iso_name}.{iso_ext};1",
                                    rr_name=file_metadata["file_name"],
                                    joliet_path=joliet_path)
        print("\tDone adding files to .iso file")

        def progress_dialog_update(done, total, args):
            done_ratio = (done / total) * 100
            self.signals.progress.emit(done_ratio)
        try:
            # Write the ISO file with progress updates
            output_iso.write(self.output_path, progress_cb=progress_dialog_update)
            output_iso.close()
            print(f"ISO successfully saved to {self.output_path}")
        except Exception as e:
            print(f"Error saving ISO: {e}")

    def get_ext(self, filename):
        return "" if len(filename.split(".")) > 0 else filename.split(".")[1]

class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(float)