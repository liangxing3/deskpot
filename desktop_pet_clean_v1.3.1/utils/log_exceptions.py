from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from app.signal_bus import get_bus


def log_exceptions(*, signal_name: str | None = None, fallback=None):
    """Log service exceptions and optionally emit a bus error signal."""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:  # pragma: no cover - failure path
                logger = getattr(self, "logger", None)
                if logger is not None:
                    logger.exception("%s failed", func.__qualname__)
                if signal_name:
                    signal = getattr(get_bus(), signal_name, None)
                    if signal is not None:
                        signal.emit(str(exc))
                return fallback() if callable(fallback) else fallback

        return wrapper

    return decorator
