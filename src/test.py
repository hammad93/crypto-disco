import unittest
import sys
import os
from pprint import pprint
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
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
        base_dir = os.path.abspath(os.path.dirname(__file__))
        pdf_path = os.path.join(base_dir, 'tests', 'test.pdf')
        with patch('PySide6.QtWidgets.QFileDialog.getOpenFileNames') as mock_dialog:
            mock_dialog.return_value = ([pdf_path], "PDF Files (*.pdf)")
            # Simulate the User Click
            QTest.mouseClick(self.window.add_files_button, Qt.MouseButton.LeftButton)
            pprint(self.window.file_list)
            self.assertEqual(len(self.window.file_list), 1, "File list should have 1 entry")
            file_data = self.window.file_list[0]
            self.assertEqual(file_data['file_name'], 'test.pdf')
            self.assertEqual(file_data['ecc_checked'], True)
            self.assertEqual(file_data['clone_checked'], True)
            expected_directory = os.path.dirname(pdf_path)
            self.assertEqual(file_data['directory'], expected_directory)
            self.assertEqual(file_data['file_size'], 8121)

if __name__ == '__main__':
    unittest.main(verbosity=2)