from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from core.pet_controller import AppController
from utils.exception_handler import install_global_exception_handler
from utils.font_loader import configure_application_font
from utils.logger import configure_logging


def main() -> int:
    logger = configure_logging()
    install_global_exception_handler(logger)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    configure_application_font(app, logger)
    controller = AppController(app, logger)
    app._desktop_pet_controller = controller
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
