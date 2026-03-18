import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication

if getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(sys._MEIPASS) / 'src'))
else:
    sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AutoApiTest")
    app.setApplicationVersion("1.0.0")
    
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
