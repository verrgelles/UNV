from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow
import sys
import logging


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger("UNV")

def main():
    QCoreApplication.setApplicationName("UNV")
    QCoreApplication.setOrganizationDomain("NANOCENTER")
    app = QApplication([])
    logger = configure_logging()
    window = MainWindow(logger=logger)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()