import sys
from gui import crypto_disco
from PySide6.QtWidgets import QApplication

if __name__ == "__main__":
    print("Starting Crypto Disco . . .")
    app = QApplication(sys.argv)
    window = crypto_disco(app)
    window.show()
    sys.exit(app.exec())