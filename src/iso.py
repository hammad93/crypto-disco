from PySide6.QtCore import QRunnable, Slot, QObject, Signal, QFile
import assets
import traceback
import math
import os
import sys
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
            self.cd_name = utils.get_iso_name(os.path.basename(self.output_path).replace(".iso", ""), truncate_len=30)
            self.setup_file_list()
            self.setup_ecc_files()
            self.setup_clone_files()
            # begin os dependent operations (write ISO file)
            os_type = platform.system()
            print(f"Identified as {os_type}")
            if os_type == "Linux":
                self.run_linux()
            elif os_type == "Darwin":  # Mac
                self.run_mac()
            elif os_type == "Windows":
                self.run_windows()
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
        self.signals.progress_end.emit(len(self.file_list) + 1)
        self.signals.progress.emit(1)
        for i, file_metadata in enumerate(self.file_list):
            self.signals.progress_text.emit(f"Copying {file_metadata['file_name']} to stage . . .")
            path = os.path.join(file_metadata["directory"], file_metadata["file_name"])
            dest_path = os.path.join(self.stage_dir, os.path.basename(path))
            print(f"Copying {path} to {dest_path}")
            if os.path.isfile(path):
                shutil.copy2(path, dest_path)
            elif os.path.isdir(path):
                # Copy directory recursively
                shutil.copytree(path, dest_path)
            self.signals.progress.emit(i + 1)
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
        print(f"Adding clones to .iso with {size_fmt_str(remaining_bytes)} remaining. . .")
        file_clones_ref = self.calculate_file_clones(current_size_bytes)
        print(pformat(file_clones_ref))
        if len(file_clones_ref) > 0:
            clone_dir_path = os.path.join(self.stage_dir, f"{self.iso_clone_dir}/")
            os.makedirs(clone_dir_path, exist_ok=True)
            for index, file in enumerate(file_clones_ref):
                print(f'\tProcessing clones for {file["file_path"]}')
                self.signals.progress.emit(1)
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
                # if we're cloning this file many times and it's a small file size (<1GB), load it into memory
                if file['num_clones'] > 100 and file['size'] < utils.disc_type_bytes("1 GB"):
                    with open(file["file_path"], "rb") as f:
                        # load clone in memory, note that this might be inefficient
                        clone_memory = f.read()
                else:
                    clone_memory = False
                for i in range(file["num_clones"]):
                    current_clone_name = f"{i}.{clone_ref['extension']}"
                    if file["num_dirs"] > 0:  # if there is a large number of possible clones, this organizes them
                        i_dir = f"{i // self.max_clones}/"
                        current_clone_path = os.path.join(os.path.join(clone_ref_path, i_dir), current_clone_name)
                    else:
                        current_clone_path = os.path.join(clone_ref_path, current_clone_name)
                    self.save_clone(file['file_path'], current_clone_path, clone_memory)
                    if (i + 1) % self.max_clones == 0:
                        print(f"\t\t\t{i + 1}")
                    self.signals.progress.emit((i + 1))
                    if self.shutdown:
                        raise self.cancel_exception
        else:
            print("No files selected for cloning")
        return True

    def save_clone(self, original_path, current_clone_path, clone_content=False):
        # efficiently saves the clone for cases where there are many clones with a small file size
        if clone_content:
            with open(current_clone_path, "wb") as f:
                # write the clone from data in memory
                f.write(clone_content)
        else:
            with open(original_path, "rb") as f:
                with open(current_clone_path, "wb") as clone:
                    clone.write(f.read())

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
        if len(clone_ref) < 1:
            return clone_ref # return empty list because no files are being cloned
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
        print(f"\t{remaining} bytes ({utils.total_size_str(remaining)}) bytes on disc will be unused.")
        for ref in clone_ref:
            ref["num_dirs"] = math.ceil(ref["num_clones"]/self.max_clones) if ref["num_clones"] > self.max_clones else 0
        return clone_ref

    def get_ext(self, filename):
        return "" if len(filename.split(".")) < 1 else filename.split(".")[-1]

    def cancel_task(self):
        self.shutdown = True
        return False

    def run_command(self, command, callback):
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as process:
            # Read from stdout in real-time
            for line in process.stdout:
                clean_line = line.strip()
                print(clean_line)
                callback(clean_line)
        return True

    def run_linux(self):
        # check to see if xorriso exists
        try:
            subprocess.run(["xorriso", "--version"], check=True)
        except:
            self.signals.error.emit({"exception": Exception("Please install xorriso"), "msg": traceback.format_exc()})
            self.signals.cancel.emit()
            return False
        # note that all other try catch is handled by calling function
        create_command = [
            'xorriso',
            '-as', 'mkisofs', '-v',
            '-iso-level', '3',
            '-full-iso9660-filenames',
            '-volid', self.cd_name,
            '-o', self.output_path,
            self.stage_dir
        ]
        print(f"Running command:\n{' '.join(create_command)}")
        self.signals.progress_text.emit(f"Writing {os.path.basename(self.output_path)}")
        self.signals.progress.emit(1)
        self.signals.progress_end.emit(100)
        def process_log(l):
            if '% done' in l:
                percent_progress = l.split('% done')[0].split('UPDATE :')[-1].strip()
                self.signals.progress.emit(float(percent_progress))
        self.run_command(create_command, process_log)
        print(f"ISO created: {self.output_path}")

        return True

    def run_mac(self):
        # note that try catch is handled by calling function
        # create the iso
        create_command = [
            'hdiutil', 'create', '-puppetstrings', '-volname', self.cd_name,
            '-fs', 'UDF', '-srcfolder', self.stage_dir,
            '-format', 'UDTO', self.output_path + '.cdr'
        ]
        print(f"Running command:\n{' '.join(create_command)}")
        process = subprocess.Popen(create_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.signals.progress_text.emit(f"Writing {os.path.basename(self.output_path)}")
        self.signals.progress.emit(1)
        self.signals.progress_end.emit(100)
        def process_log(l):
            if 'PERCENT:' in l:
                current_progress = l.strip().split('PERCENT:')[-1].strip()
                self.signals.progress.emit(float(current_progress))
        self.run_command(create_command, process_log)
        rename_command = ['mv', self.output_path + '.cdr', self.output_path]
        subprocess.run(rename_command, check=True)
        print(f"ISO created: {self.output_path}")

        return True
    
    def run_windows(self):
        '''
        Credit to https://github.com/TheDotSource/New-ISOFile/blob/main/New-ISOFile.ps1
        '''
        file = QFile(":/assets/New-ISOFile.ps1")
        file.open(QFile.ReadOnly | QFile.Text)
        isofile_script = file.readAll().data().decode('utf-8')
        file.close()
        script_path = os.path.join(os.getcwd(), "New-ISOFile-Runner.ps1")
        wrapper = f"""
        {isofile_script}
        New-ISOFile -source $args[0] -destinationISO $args[1] -title $args[2]
        """
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(wrapper)
        create_command = [
            "powershell.exe", 
            "-NoProfile", 
            "-ExecutionPolicy", "Bypass", 
            "-File", script_path, 
            self.stage_dir, 
            self.output_path, 
            self.cd_name
        ]
        def process_log(l):
            if '%' in l:
                print(f"-> {l}")
        self.run_command(create_command, process_log)
        return True