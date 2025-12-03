import pycdlib
from PySide6.QtCore import QRunnable, Slot, QObject, Signal, QFileInfo
import traceback
import io
import math

class IsoWorker(QRunnable):
    def __init__(self, output_path, file_list, ecc_dir, disc_type):
        super().__init__()
        self.output_path = output_path
        self.file_list = file_list
        self.ecc_dir = ecc_dir
        self.disc_type = disc_type
        self.iso_clone_dir = '/CLONES'
        self.clone_dir_list = []
        self.max_clones = 50000 # max num of clones in a directory
        self.max_clones_total = self.max_clones * 1000 # max num of directories * max num of clones in a directory
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
        if any([f["ecc_checked"] for f in self.file_list]):
            ecc_dirs = self.standardize_directory(iso_ecc_dir)
            output_iso.add_directory(ecc_dirs["directory"],
                                     rr_name=ecc_dirs["rr_name"],
                                     joliet_path=ecc_dirs["joliet_path"])
        # create CLONE directory if applicable
        file_clones = False
        if any([f["clone_checked"] for f in self.file_list]):
            file_clones = True
            clones_dir = self.standardize_directory(self.iso_clone_dir)
            output_iso.add_directory(clones_dir["directory"],
                                     rr_name=clones_dir["rr_name"],
                                     joliet_path=clones_dir["joliet_path"])
        # add files and ECC in ISO
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
                    ecc_file_input = self.standardize_nested_file(iso_ecc_dir, ecc_file)
                    for name in ecc_file_input.keys():
                        print(f'\t\t{name}: {ecc_file_input[name]}')
                    try:
                        output_iso.add_file(ecc_file_input["directory"],
                                            iso_path=ecc_file_input["iso_path"],
                                            rr_name=ecc_file_input["rr_name"],
                                            joliet_path=ecc_file_input["joliet_path"])
                    except Exception:
                        print(traceback.format_exc())
        if file_clones:
            print("\tAdding clones to .iso . . .")
            file_clones_ref = self.calculate_file_clones(output_iso._get_iso_size())
            try:
                for file in file_clones_ref:
                    clone_ref = self.clones_dir_name(file)
                    clone_ref_dir = self.standardize_directory(clone_ref["directory"])
                    for name in clone_ref_dir.keys():
                        print(f'\t\t{name}: {clone_ref_dir[name]}')
                    output_iso.add_directory(clone_ref_dir["directory"],
                                             rr_name=clone_ref_dir["rr_name"],
                                             joliet_path=clone_ref_dir["joliet_path"])
                    print(f'\t\tAdded {clone_ref_dir["joliet_path"]}')
                    # Create folder structure if there are a large number of clone to ease file explorers
                    if file["num_dirs"] > 0:
                        print(f'\t\tCreating {file["num_dirs"]} folders for {file["num_clones"]} clones')
                        for i in range(file["num_dirs"]):
                            i_dir = f"/{i}"
                            output_iso.add_directory(clone_ref_dir["directory"] + i_dir,
                                             rr_name=str(i),
                                             joliet_path=clone_ref_dir["joliet_path"] + i_dir)
                    # add clones in directory
                    print(f'\tProcessing clones for {file["file_path"]}')
                    with open(file["file_path"], "rb") as f:
                        clone_content = f.read()
                    clone_content_len = len(clone_content)
                    clone_content_input = io.BytesIO(clone_content)
                    for i in range(file["num_clones"]):
                        if file["num_dirs"] > 0: # if there is a large number of possible clones, this organizes them
                            i_dir = f"{i // self.max_clones}/"
                        else:
                            i_dir = ""
                        current_clone_name = f"{i_dir}{i}.{clone_ref['extension']}"
                        current_clone_file = self.standardize_filenames({
                            "file_name": current_clone_name,
                            "directory": clone_ref_dir["joliet_path"]
                        })
                        current_clone_input = self.standardize_nested_file(
                            clone_ref_dir["joliet_path"], current_clone_file)
                        output_iso.add_fp(clone_content_input, clone_content_len,
                                          iso_path=current_clone_input["iso_path"],
                                          rr_name=current_clone_input["rr_name"],
                                          joliet_path=current_clone_input["joliet_path"])
                        if (i+1) % self.max_clones == 0:
                            print(f"\t\t\t{i+1}")
            except Exception:
                print(traceback.format_exc())
        print("Done adding files to .iso file")
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

    def standardize_nested_file(self, directory, file):
        iso_path = f'{directory}{file["iso_path"]}'.upper()
        rr_name = f'{file["rr_name"].split("/")[-1:]}' # must be relative
        joliet_path = f'{directory}{file["joliet_path"]}'
        # Displaying the paths can assist in debugging
        result = {
            "directory": file["file_path"],
            "iso_path": iso_path,
            "rr_name": rr_name,
            "joliet_path": joliet_path
        }
        return result

    def clones_dir_name(self, file):
        # construct candidate dir name for clones
        file_clones_dir = ""
        max_dir_len = 30 - len(f"{self.iso_clone_dir}/")
        for char in file["info"]["file_name"]:
            file_clones_dir += char if char.isalnum() else "_"
            if (len(file_clones_dir) + 1) > max_dir_len:
                break
        # check if it already exists, include numeral if it does
        if file_clones_dir in self.clone_dir_list:
            count = 2
            while file_clones_dir in self.clone_dir_list:
                postfix = str(count)
                file_clones_dir = file_clones_dir[:(max_dir_len - len(postfix))] + postfix
                count += 1
        self.clone_dir_list.append(file_clones_dir)
        return {
            "dir_name": file_clones_dir,
            "directory": f"{self.iso_clone_dir}/{file_clones_dir}",
            "extension": self.get_ext(file["info"]["file_name"])
        }

    def calculate_file_clones(self, iso_size):
        # based on the current iso size and the iso limit, we can fill in the rest with clones
        clone_ref = []
        for file in self.file_list:
            if not file["clone_checked"]: # skip files not marked for cloning
                continue
            file_path = f'{file["directory"]}/{file["file_name"]}'
            clone_ref.append({
                "file_path": file_path,
                "info": file,
                "size": file["file_size"],
                "num_clones": 0
            })
        # calculate number of clones we can fit in
        disc_limit = int(self.disc_type.split(" ")[0]) * (10**9)
        remaining = disc_limit - iso_size
        clone_magnitude = 1 # iterative counter
        # while there's enough space to fill with file clones
        while all([(clone_magnitude < self.max_clones_total),
                   (remaining > min([clone["size"] for clone in clone_ref])),
                   (remaining > 0)]):
            for clone in clone_ref:
                # if there's enough space, increase the file clone reference count by 1
                if (clone["num_clones"] < clone_magnitude) and (clone["size"] <= remaining):
                    clone["num_clones"] += 1
                    remaining -= clone["size"]
            clone_magnitude += 1
        print(f"\t{remaining} bytes on disc will be unused.")
        for ref in clone_ref:
            ref["num_dirs"] = math.ceil(ref["num_clones"]/self.max_clones) if ref["num_clones"] > self.max_clones else 0
        return clone_ref

    def standardize_filenames(self, file_metadata):
        # sanitize iso name
        iso_name = "".join(file_metadata["file_name"].split(".")[:-1]).upper()
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
        return "" if len(filename.split(".")) < 1 else filename.split(".")[-1]

    def standardize_directory(self, directory):
        return {
            "directory": directory.upper(),
            "rr_name": directory.split("/")[-1],  # must be relative
            "joliet_path": directory
        }
class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(float)