from PySide6.QtCore import QRunnable, Slot, QObject, Signal
import traceback
import io
import math
import os
import utils
import config
import shutil
import subprocess
import platform
from pprint import pformat

class IsoWorker(QRunnable):
    def __init__(self, output_path, file_list, ecc_dir, disc_type):
        super().__init__()
        self.output_path = output_path
        self.file_list = file_list
        self.ecc_dir = ecc_dir
        self.disc_type = disc_type
        self.iso_ecc_dir = 'ECC'
        self.iso_clone_dir = 'CLONES'
        self.clone_dir_list = []
        self.joliet_max = 64 # filename, excluding extension, max characters for joliet
        self.max_clones = 50000 # max num of clones in a directory
        self.max_clones_total = self.max_clones * 1000 # max num of directories * max num of clones in a directory
        self.signals = utils.WorkerSignals()
        self.shutdown = False # set to True to begin shutdown at next opportunity
        self.cancel_exception = Exception("ISO creation canceled.")

    @Slot()
    def run(self):
        try:
            self.setup_file_list()
            self.setup_ecc_files()
            self.setup_clone_files()
            # begin os dependent operations (write ISO file)
            os_type = platform.system()
            print(os_type)
            if os_type == "Darwin":  # Mac
                self.run_mac()
            self.signals.progress.emit(100)
            return True
        except Exception as e:
            msg = traceback.format_exc()
            print(msg)
            self.signals.error.emit({"exception": e, "msg": msg})
            self.signals.cancel.emit()
            return False

    def setup_file_list(self):
        # copies the file list to current directory
        self.stage_dir = f"output_{utils.datetime_str()}/"
        os.makedirs(self.stage_dir, exist_ok=True)
        self.signals.progress_end.emit(len(self.file_list))
        self.signals.progress.emit(0)
        for i, file_metadata in enumerate(self.file_list):
            self.signals.progress_text.emit(f"Copying {file_metadata['file_name']} to stage . . .")
            self.signals.progress.emit(i + 1)
            path = os.path.join(file_metadata["directory"], file_metadata["file_name"])
            dest_path = os.path.join(self.stage_dir, os.path.basename(path))
            print(f"Copying {path} to {dest_path}")
            if os.path.isfile(path):
                shutil.copy2(path, dest_path)
            elif os.path.isdir(path):
                # Copy directory recursively
                shutil.copytree(path, dest_path)
        return True

    def setup_ecc_files(self):
        # ECC is computed before this class is called
        for file_metadata in self.file_list:
            print(f"Copying ECC for {file_metadata['file_name']} into stage folder . . .")
            if file_metadata["ecc_checked"]:
                os.makedirs(os.path.join(self.stage_dir, f"{self.iso_ecc_dir}/"), exist_ok=True)
                # two files added, .txt is the database and .idx is the index (reference pyFileFixity)
                for ecc_ext in ['.txt', '.txt.idx']:
                    ecc_ext_filename = file_metadata["file_name"] + ecc_ext
                    ecc_ext_path = os.path.abspath(os.path.join(self.ecc_dir, ecc_ext_filename))
                    shutil.copy2(ecc_ext_path, os.path.join(self.stage_dir, f"{self.iso_ecc_dir}/"))
        return True

    def setup_clone_files(self):
        current_size_bytes = utils.get_path_size(self.stage_dir)
        print("Current size of files: ", current_size_bytes)
        remaining_bytes = utils.disc_type_bytes(self.disc_type) - current_size_bytes
        print(f"Adding clones to .iso with {remaining_bytes} . . .")
        file_clones_ref = self.calculate_file_clones(remaining_bytes)
        print(pformat(file_clones_ref))
        if len(file_clones_ref) > 0:
            clone_dir_path = os.path.join(self.stage_dir, f"{self.iso_clone_dir}/")
            os.makedirs(clone_dir_path, exist_ok=True)
            for index, file in enumerate(file_clones_ref):
                print(f'\tProcessing clones for {file["file_path"]}')
                self.signals.progress.emit(0)
                self.signals.progress_end.emit(file["num_clones"])
                self.signals.progress_text.emit(
                    f"{index + 1} out of {len(file_clones_ref)}\n"
                    f"Cloning {file['info']['file_name']} {file['num_clones']} times")
                os.makedirs(os.path.join(self.stage_dir, f"{self.iso_ecc_dir}/"), exist_ok=True)
                clone_ref = self.clones_dir_name(file) # sanitzed folder name based on file
                clone_ref_path = os.path.join(clone_dir_path, clone_ref["dir_name"])
                os.makedirs(clone_ref_path, exist_ok=True)
                # Create folder structure if there are a large number of clone to ease file explorers
                if file["num_dirs"] > 0:
                    print(f'\t\tCreating {file["num_dirs"]} folders for {file["num_clones"]} clones')
                    for i in range(file["num_dirs"]):
                        i_dir = f"/{i}"
                        os.makedirs(clone_ref_path + i_dir, exist_ok=True)
                # add clones in directory
                with open(file["file_path"], "rb") as f:
                    clone_content = f.read()
                # load clone in memory, note that this might be inefficient
                clone_content_input = io.BytesIO(clone_content)
                for i in range(file["num_clones"]):
                    current_clone_name = f"{i}.{clone_ref['extension']}"
                    if file["num_dirs"] > 0:  # if there is a large number of possible clones, this organizes them
                        i_dir = f"{i // self.max_clones}/"
                        current_clone_path = os.path.join(os.path.join(clone_ref_path, i_dir), current_clone_name)
                    else:
                        current_clone_path = os.path.join(clone_ref_path, current_clone_name)
                    with open(current_clone_path, "wb") as f:
                        # write the clone from data in memory
                        f.write(clone_content_input.getbuffer())
                    if (i + 1) % self.max_clones == 0:
                        print(f"\t\t\t{i + 1}")
                    self.signals.progress.emit((i + 1))
                    if self.shutdown:
                        raise self.cancel_exception
        else:
            print("No files selected for cloning")
        return True

    def run_mac(self):
        # create the iso
        create_command = [
            'hdiutil', 'create', '-puppetstrings', '-volname', 'MyVolume',
            '-fs', 'UDF', '-srcfolder', self.stage_dir,
            '-format', 'UDTO', self.output_path + '.cdr'
        ]
        try:
            print(f"Running command:\n{' '.join(create_command)}")
            process = subprocess.Popen(create_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.signals.progress_text.emit(f"Writing {os.path.basename(self.output_path)}")
            self.signals.progress.emit(0)
            self.signals.progress_end.emit(100)
            while True:
                stdout_line = process.stdout.readline()
                if process.poll() is not None:
                    break
                if stdout_line:
                    print(stdout_line, end='')
                    if 'PERCENT:' in stdout_line:
                        current_progress = stdout_line.strip().split('PERCENT:')[-1]
                        self.signals.progress.emit(float(current_progress))
            process.stdout.close()
            process.stderr.close()
            # Wait for the process to complete
            process.wait()
            rename_command = ['mv', self.output_path + '.cdr', self.output_path]
            subprocess.run(rename_command, check=True)
            self.signals.progress.emit(100)
            print(f"ISO created: {self.output_path}")

        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")

        return True

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
            file_path = os.path.join(file["directory"], file["file_name"])
            clone_ref.append({
                "file_path": file_path,
                "info": file,
                "size": file["file_size"],
                "num_clones": 0
            })
        # calculate number of clones we can fit in
        disc_limit = utils.disc_type_bytes(self.disc_type)
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

    def get_ext(self, filename):
        return "" if len(filename.split(".")) < 1 else filename.split(".")[-1]

    def cancel_task(self):
        self.shutdown = True
        return False