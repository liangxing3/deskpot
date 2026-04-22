from __future__ import annotations

import faulthandler
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import threading
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from app.app_metadata import APP_DISPLAY_NAME, APP_VERSION
from app.controller import AppController
from utils.app_icon import load_app_icon
from utils.paths import logs_dir


def _startup_log(logger: logging.Logger, stage: str) -> None:
    logger.info(
        "[main-startup] %s | thread=%s ident=%s",
        stage,
        threading.current_thread().name,
        threading.get_ident(),
    )


def _install_hang_diagnostics(logger: logging.Logger) -> None:
    try:
        faulthandler.enable()
        faulthandler.dump_traceback_later(10, repeat=True)
        logger.info("[main-startup] faulthandler dump_traceback_later armed every 10s")
    except Exception:
        logger.exception("Failed to enable faulthandler hang diagnostics.")


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("desktop_pet")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    crash_handler = TimedRotatingFileHandler(
        logs_dir() / "crash.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    crash_handler.setFormatter(formatter)
    crash_handler.suffix = "%Y%m%d"
    logger.addHandler(crash_handler)
    logger.propagate = False
    return logger


def install_exception_hook(logger: logging.Logger) -> None:
    def _handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error("Unhandled exception\n%s", text)
        print(text, file=sys.stderr, flush=True)

    sys.excepthook = _handle_exception


def main() -> int:
    logger = configure_logging()
    _install_hang_diagnostics(logger)
    install_exception_hook(logger)
    app: QApplication | None = None

    try:
        _startup_log(logger, "before QApplication")
        app = QApplication(sys.argv)
        _startup_log(logger, "after QApplication")
        app.setQuitOnLastWindowClosed(False)
        app.setApplicationName(APP_DISPLAY_NAME)
        app.setApplicationDisplayName(APP_DISPLAY_NAME)
        app.setApplicationVersion(APP_VERSION)
        icon = load_app_icon()
        if icon is not None:
            app.setWindowIcon(icon)

        _startup_log(logger, "before AppController init")
        controller = AppController(app=app, logger=logger)
        _startup_log(logger, "after AppController init")
        app._desktop_pet_controller = controller
        _startup_log(logger, "before controller.start()")
        controller.start()
        _startup_log(logger, "after controller.start()")

        _startup_log(logger, "before app.exec()")
        exit_code = app.exec()
        _startup_log(logger, f"after app.exec() -> {exit_code}")
        try:
            faulthandler.cancel_dump_traceback_later()
        except Exception:
            logger.exception("Failed to cancel faulthandler hang diagnostics.")
        return exit_code
    except Exception as exc:
        text = traceback.format_exc()
        logger.error("Startup failed\n%s", text)
        print(text, file=sys.stderr, flush=True)

        if app is not None:
            QMessageBox.critical(None, "Startup failed", f"{exc}\n\n{text}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
