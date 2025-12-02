import pycdlib
from PySide6.QtCore import QRunnable, Slot, QObject, Signal
import traceback

class IsoWorker(QRunnable):
    def __init__(self, output_path, file_list, ecc_dir):
        super().__init__()
        self.output_path = output_path
        self.file_list = file_list
        self.ecc_dir = ecc_dir
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        '''
        - For iso_path,
          In standard ISO interchange level 3, filenames have a maximum of 30 characters, followed by a required
          dot, followed by an extension, followed by a semicolon and a version. The filename and the extension are
          both optional, but one or the other must exist. Only uppercase letters, numbers, and underscore are
          allowed for either the name or extension. If any of these rules are violated, PyCdlib will
          throw an exception.
        - If multiple files have the same ISO path, only the most recent one will be written
        - Rock ridge (rr_name) must be in relative format.
        '''
        output_iso = pycdlib.PyCdlib()
        # https://clalancette.github.io/pycdlib/pycdlib-api.html#PyCdlib-new
        # Interchange 3 is recommended
        output_iso.new(interchange_level=3, joliet=3, rock_ridge="1.09", xa=True)
        # create ECC directory if applicable
        iso_ecc_dir = '/ECC'
        if any([file_metadata["ecc_checked"] for file_metadata in self.file_list]):
            output_iso.add_directory(iso_ecc_dir,
                                     rr_name=iso_ecc_dir[1:], # must be relative
                                     joliet_path=iso_ecc_dir)
        # add files in ISO
        for file_metadata in self.file_list:
            standardized = self.standardize_filenames(file_metadata)
            print(f'\tFile Path: {standardized["file_path"]}')
            print(f'\t\tSize: {file_metadata["size_str"]}')
            output_iso.add_file(standardized["file_path"],
                                iso_path=standardized["iso_path"],
                                rr_name=standardized["rr_name"],
                                joliet_path=standardized["joliet_path"])
            print(f'\t\tECC: {file_metadata["ecc_checked"]}')
            if file_metadata["ecc_checked"]:
                # two files added, .txt is the database and .idx is the index (reference pyFileFixity)
                for ecc_ext in ['.txt', '.txt.idx']:
                    ecc_file = self.standardize_filenames({
                        "file_name": file_metadata["file_name"] + ecc_ext,
                        "directory": self.ecc_dir
                    })
                    ecc_iso_path = f'{iso_ecc_dir}{ecc_file["iso_path"]}'
                    ecc_rr_name = f'{ecc_file["rr_name"]}'
                    ecc_joliet_path = f'{iso_ecc_dir}{ecc_file["joliet_path"]}'
                    for param in [ecc_file["file_path"], ecc_iso_path, ecc_rr_name, ecc_joliet_path]:
                        print(f"\t\t{param}")
                    try:
                        output_iso.add_file(ecc_file["file_path"],
                                            iso_path=ecc_iso_path,
                                            rr_name=ecc_rr_name,
                                            joliet_path=ecc_joliet_path)
                    except Exception as e:
                        traceback.print_exc()
                        print(e)
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

    def standardize_filenames(self, file_metadata):
        # sanitize iso name
        iso_name = "".join(file_metadata["file_name"].split("."))[:-1].upper()
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
        return {
            "file_path": f'{file_metadata["directory"]}/{file_metadata["file_name"]}',
            "iso_name": iso_name,
            "iso_path": f"/{iso_name}.{iso_ext};1",
            "joliet_path": joliet_path,
            "rr_name": file_metadata["file_name"]
        }

    def get_ext(self, filename):
        return "" if len(filename.split(".")) > 0 else filename.split(".")[-1]


class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(float)