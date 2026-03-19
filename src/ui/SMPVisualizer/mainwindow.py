import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QSplashScreen
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QTimer

# Import your generated UI
from ui_form import Ui_MainWindow

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # Optional: set window title
        self.setWindowTitle("SMPVisualizer")
        self.setWindowIcon(QIcon("assets/icon.png"))


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # ------------------------
    # Step 1: Create Splash Screen
    # ------------------------
    pixmap = QPixmap("assets/splash.png")  # your ASCII art image
    splash = QSplashScreen(pixmap)
    splash.setWindowFlags(splash.windowFlags() | Qt.FramelessWindowHint)  # optional: no window frame
    splash.show()

    # ------------------------
    # Step 2: Create main window but DON'T show yet
    # ------------------------
    main_window = MainWindow()

    # ------------------------
    # Step 3: After 3 seconds, close splash and show main window
    # ------------------------
    QTimer.singleShot(3000, lambda: (main_window.show(), splash.close()))

    sys.exit(app.exec())