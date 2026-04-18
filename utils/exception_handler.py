from __future__ import annotations

import logging
import sys
import traceback
from typing import Callable


def install_global_exception_handler(logger: logging.Logger) -> None:
    def _handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error(
            "Unhandled exception\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        )

    sys.excepthook = _handle_exception


def guard_exceptions(logger: logging.Logger) -> Callable:
    def _decorator(func: Callable) -> Callable:
        def _wrapped(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.exception("Unhandled error in %s", func.__name__)
                return None

        return _wrapped

    return _decorator
