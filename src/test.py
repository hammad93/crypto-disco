import unittest
import sys
import os
from pprint import pprint
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QWizard, QPushButton
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
import gui

class TestCryptoDisco(unittest.TestCase):
    '''
    - Tests are functions in this class that start with "test_"
    '''

    @classmethod
    def setUpClass(cls):
        """
        Set up the QApplication once for the entire test suite.
        This prevents the "A QApplication instance already exists" error.
        """
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """
        Run before *each* test. Creates a fresh window instance.
        """
        self.window = gui.crypto_disco(self.app)
        self.base_dir = os.path.abspath(os.path.dirname(__file__))
        self.tests_dir = os.path.join(self.base_dir, 'tests')

    def test_basic_imports(self):
        """
        - Simple import check to ensure modules exist and don't create syntax errors
        - Otherwise, simple syntax errors might be caught much later on
        """
        try:
            import app
            import assets
            import ecc
            import compute_ecc
            import repair
            import compute_repair
            import gui
            import iso
            import utils
        except ImportError as e:
            self.fail(f"Import failed: {e}")

    def test_startup(self):
        """
        Tests that the application starts (is visible) and exits (closes) correctly.
        """
        self.window.show()
        self.assertTrue(self.window.isVisible(), "Window should be visible after show()")
        # Simluate closing the window
        closed = self.window.close()
        self.assertTrue(closed, "Window failed to close")
        self.assertFalse(self.window.isVisible(), "Window should be hidden after close()")

    def test_add_file_pdf(self):
        """
        Tests clicking 'add_files_button' and selecting 'tests/test.pdf'.
        Uses mocking to bypass the actual native OS file dialog.
        """
        print("Begin test add file.")
        self.base_dir = os.path.abspath(os.path.dirname(__file__))
        pdf_path = os.path.join(self.base_dir, self.tests_dir, 'test.pdf')
        with patch('PySide6.QtWidgets.QFileDialog.getOpenFileNames') as mock_dialog:
            mock_dialog.return_value = ([pdf_path], "PDF Files (*.pdf)")
            # Simulate the User Click
            QTest.mouseClick(self.window.add_files_button, Qt.MouseButton.LeftButton)
            pprint(self.window.file_list)
            expected_total_files = 1 + len(self.window.default_files)
            self.assertEqual(
                len(self.window.file_list),
                expected_total_files,
                f"File list should have {expected_total_files} entry")
            file_data = self.window.file_list[-1]
            self.assertEqual(file_data['file_name'], 'test.pdf')
            self.assertEqual(file_data['ecc_checked'], True)
            self.assertEqual(file_data['clone_checked'], True)
            expected_directory = os.path.dirname(pdf_path)
            self.assertEqual(file_data['directory'], expected_directory)
            self.assertEqual(file_data['file_size'], 8121)

    def test_repair(self, test_file='pismis-24-mini-poster.png'):
        """
        Tests out a pipeline of core functionality including:

        1. Create file with ECC
        2. Tamper the file
        3. Repair the file
        """
        import ecc
        import utils
        import hashlib
        print("Begin test repair.")
        # create output directory
        self.output_dir = os.path.join(self.tests_dir, f"test_output_{utils.datetime_str()}")
        os.makedirs(self.output_dir, exist_ok=False)
        src_path = os.path.join(self.base_dir, 'tests', test_file)
        # create error correcting codes
        ecc_path = os.path.join(self.output_dir, f'{test_file}.txt')
        print(f"Generating ECC at {ecc_path}. . .")
        ecc_result = ecc.generate_ecc(input_path=src_path, output_path=self.output_dir)
        self.assertTrue(ecc_result, "ECC result should be True")
        self.assertTrue(os.path.exists(ecc_path), "ECC file should exist")
        # calculate a hash that changes if the file has been tampered with
        md5_hash = utils.md5_file_hash(src_path)
        print(f"Generated MD5 hash for {src_path} is {md5_hash}")
        # tamper file
        print(f"Tampering {src_path}")
        tamper_result = utils.tamper_file(src_path)
        print(f"{tamper_result[0]} bytes tampered")
        tampered_md5_hash = utils.md5_file_hash(src_path)
        self.assertNotEqual(md5_hash, tampered_md5_hash)
        # configure threads
        def capture_start(runnable):
            # Call the actual start method so the code runs
            print("Running the repair in a blocking thread with the following configuration:")
            pprint(runnable.ecc_config)
            result = runnable.run()
            print("Done.")
            return result
        # start wizard
        with patch.object(self.window.threadpool, 'start', side_effect=capture_start):
            # 1. Open Wizard
            self.window.show()
            QTest.mouseClick(self.window.repair_button, Qt.MouseButton.LeftButton)
            # Locate the active QWizard instance
            wizard = None
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, QWizard) and widget.isVisible():
                    wizard = widget
                    break
            self.assertIsNotNone(wizard, "Wizard window did not open")
            with patch('PySide6.QtWidgets.QFileDialog.getOpenFileName') as mock_open, \
                    patch('PySide6.QtWidgets.QFileDialog.getExistingDirectory') as mock_dir:
                # Configure Side Effects for sequential calls
                # First call returns src_path, Second call returns ecc_path
                mock_open.side_effect = [(src_path, "Files"), (ecc_path, "Files")]
                mock_dir.return_value = self.output_dir
                # Page 1: Select Corrupted File
                print("Wizard: Selecting Corrupted File...")
                current_page = wizard.currentPage()
                # Find the "Select File" button on this page
                buttons = current_page.findChildren(QPushButton)
                select_btn = next((b for b in buttons if "Select File" in b.text()), None)
                self.assertIsNotNone(select_btn)
                # Click it -> Mocks getOpenFileName -> Populates QLineEdit
                QTest.mouseClick(select_btn, Qt.MouseButton.LeftButton)
                # Verify field is populated so 'Next' is enabled
                field_val = wizard.field("corrupted_file")
                self.assertEqual(field_val, src_path)
                # Click Next
                wizard.next()
                # --- Page 2: Select ECC File --
                print("Wizard: Selecting ECC File...")
                current_page = wizard.currentPage()
                buttons = current_page.findChildren(QPushButton)
                select_btn = next((b for b in buttons if "Select File" in b.text()), None)
                # Click it -> Mocks getOpenFileName (2nd call) -> Populates QLineEdit
                QTest.mouseClick(select_btn, Qt.MouseButton.LeftButton)
                field_val = wizard.field("ecc_file")
                self.assertEqual(field_val, ecc_path)
                # Click Next
                wizard.next()
                print("Wizard: Starting Repair...")
                current_page = wizard.currentPage()
                # Select Output Dir
                buttons = current_page.findChildren(QPushButton)
                dir_btn = next((b for b in buttons if "Select folder" in b.text()), None)
                QTest.mouseClick(dir_btn, Qt.MouseButton.LeftButton)
                # Click Start Repair
                repair_btn = next((b for b in buttons if "Start Repair" in b.text()), None)
                QTest.mouseClick(repair_btn, Qt.MouseButton.LeftButton)
            # Check if file exists
            expected_output = os.path.join(self.output_dir, test_file)
            self.assertTrue(os.path.exists(expected_output), "Repaired file was not created")
            # Validate Content (MD5)
            repaired_md5 = utils.md5_file_hash(expected_output)
            self.assertEqual(repaired_md5, md5_hash, "Repaired file MD5 does not match original!")
            # cleanup files
            tampered_file_path = os.path.join(self.output_dir, f"tampered_{test_file}")
            if os.path.exists(tampered_file_path):
                raise Exception("Tampered file already exists")
            else:
                # move tampered file into output folder
                os.rename(src_path, tampered_file_path)
                # move repaired file back
                os.rename(expected_output, src_path)
            print("Wizard test passed successfully.")
            wizard.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)