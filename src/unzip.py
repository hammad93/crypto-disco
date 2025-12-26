from PySide6.QtCore import QRunnable, Slot, QWaitCondition, Qt, QMutex
from PySide6.QtWidgets import (QWizardPage, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit,
                               QDialog, QComboBox, QWizard, QTableWidget, QTableWidgetItem, QMessageBox, QProgressBar,
                               QPlainTextEdit)
import os
import utils
import config
import traceback
import pyzipper
import zipfile
import re

class UnzipWorker(QRunnable):
    def __init__(self, files):
        super().__init__()
        self.input_files = files
        self.canceled = False
        self.signals = utils.WorkerSignals()
        self.output_dir = None # full path
        # set these flags to False and then verify them as true
        self.multipart = False
        self.zip_file = False

    @Slot()
    def run(self):
        '''
        For example, a time series dataset of images in 2019/ 2018/ 2017/ is compressed into example.zip using the
        Create Zip Wizard
        Selected files: [~/example.zip.part1_of_2, ~/example.zip.part2_of_2]
        Output dir: [~/example_data/]
        Run Outputs: [~/example_data/example.zip, ~./example_data/* (decompressed data)]
        '''
        test_file = self.input_files[0]
        test_filename = os.path.basename(test_file)
        print("Test filename: ", test_filename)
        dir = os.path.dirname(test_file)
        # example.zip.partX_of_Y
        self.multipart = True if re.search(r'^(.+)\.part\d+_of_\d+$', test_filename) else False
        # regular zip file supported
        self.zip_file = True if test_filename.endswith(".zip") else False
        print(f"Zip: {self.zip_file}, Multipart: {self.multipart}")
        # create output dir if applicable
        if self.multipart or self.zip_file:
            self.output_dir_name = test_filename.split('.')[0]
            self.output_dir = os.path.join(dir, self.output_dir_name)
            if os.path.exists(self.output_dir):
                print(f"Failed to create {self.output_dir}")
                self.signals.cancel.emit()
                self.signals.error.emit({
                    "exception": FileExistsError(f"{self.output_dir} already exists."),
                    "msg": "Please rename the existing folder or move it to another folder."
                })
                return False
            else:
                print("Creating output dir: ", self.output_dir)
                os.makedirs(self.output_dir)
        self.signals.progress.emit(25)
        if self.multipart: # Process example.zip.partX_of_Y
            combined_filename = test_filename.split('.part')[0]
            total_parts = int(test_filename.split('_of_')[-1])
            self.combined_file = os.path.join(self.output_dir, combined_filename)
            reassembled = self.reassemble_zip(dir, combined_filename, total_parts)
            if reassembled:
                self.signals.progress.emit(50)
            decompressed = self.decompress_zip(self.combined_file)
            if decompressed:
                self.signals.progress.emit(100)
            if not reassembled or not decompressed:
                print("Unknown error while reassembling and decompressing")
        elif self.zip_file: # Process example.zip
            print("Found single zip file.")
            if len(self.input_files) > 1:
                self.signals.cancel.emit()
                self.signals.error.emit({
                    "exception": Exception("Multiple ZIP Files in Incorrect Format"),
                    "msg": config.unzip_err["multiple_single_zip"]
                })
                return False
            else:
               self.decompress_zip(test_file)
        self.signals.progress.emit(100)
        return True

    def get_all_parts(self, dir, combined_filename, total_parts):
        '''

        '''
        self.all_parts = [
            os.path.join(dir, f"{combined_filename}.part{(i + 1)}_of_{total_parts}") for i in range(total_parts)]
        # verifies all parts exist in the directory
        if not all(os.path.exists(expected) for expected in self.all_parts):
            return False
        return self.all_parts

    def decompress_zip(self, zip_path):
        '''
        This function decompress the zip and prompts the user if there is a password.
        path is the full path of the .zip file.

        Notes
        -----
        - pyzipper is backwards compatible with zipfile (the built-in library with Python)
        - reducing the complexity of this function reduces the attack space
        '''
        if self.canceled:
            return False
        encryption_info = {detail: False for detail in ["has_password", "aes_encryption"]}
        try:
            with pyzipper.AESZipFile(zip_path, 'r') as zf:
                # Check each file in the archive
                for zip_info in zf.infolist():
                    if zip_info.flag_bits & 0x1:  # Check if the file is encrypted
                        encryption_info["has_password"] = True
                        # Check if AES encryption is used
                        if zip_info.flag_bits & 0x800:  # AES-256 encryption
                            encryption_info["aes_encryption"] = True
            if encryption_info["has_password"]:
                # prompt user for password
                self.signals.retrieve_pwd.connect(self.set_password)
                mutex = QMutex()
                mutex.lock()
                self.signals.request_pwd.emit()
                # wait until we have a password to try
                self.wait_for_password = QWaitCondition()
                self.wait_for_password.wait(mutex)
                mutex.unlock()
                print("Continuing after password was set")
                # utilize pyzipper for both AES 256 encryption and the deprecated ZipCrypto method
                with pyzipper.AESZipFile(zip_path, 'r') as zf:
                    zf.pwd = self.password.encode()
                    zf.extractall(path=self.output_dir)
            else:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(path=self.output_dir)
        except Exception as e:
            self.signals.error.emit({
                "exception": e,
                "msg": traceback.format_exc(),
            })
        return True

    def set_password(self, password):
        self.password = password
        print("Password set")
        self.wait_for_password.wakeAll()

    def reassemble_zip(self, dir, combined_filename, total_parts):
        '''
        dir = current working directory
        combined_filename = test.zip
        total_parts = 2
        test.zip = 9.0 GB
        test.zip.part1_of_2 = 4.5 GB
        test.zip.part2_of_2 = 4.5 GB
        M-Disc DVD 4.7 GB x 2 = 9.9 GB
        '''
        if self.canceled:
            return False
        self.combined_file = False
        expected_parts = self.get_all_parts(dir, combined_filename, total_parts)
        print(f"Expected files for ZIP part assembly: {expected_parts}")
        if not expected_parts:
            self.signals.cancel.emit()
            self.signals.error.emit({
                "exception": Exception("Missing Parts for Multipart ZIP Files"),
                "msg": f"{config.unzip_err['missing_parts']}\n{[f for f in self.all_parts if not os.path.exists(f)]}"
            })
            return False
        else:
            combined_file = os.path.join(self.output_dir, combined_filename)
            if not os.path.exists(combined_file):
                self.combined_file = combined_file
                with open(self.combined_file, 'wb') as f:
                    for expected in expected_parts:
                        with open(expected, 'rb') as part_file:
                            f.write(part_file.read())
            else:
                self.signals.cancel.emit()
                self.signals.error.emit({
                    "exception": Exception("File Already Exists"),
                    "msg": f"{combined_file} already exists"
                })
                return False
        return True

    def cancel_task(self):
        # set the class variable and exit when safe
        self.canceled = True