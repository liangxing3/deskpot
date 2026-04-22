from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, QTimer


class AtomicJsonStore(QObject):
    """Small JSON-backed store with in-memory caching and debounced durable writes."""

    def __init__(
        self,
        path: Path,
        logger: logging.Logger,
        *,
        flush_interval_ms: int = 0,
    ) -> None:
        super().__init__()
        self.path = path
        self.logger = logger
        self._flush_interval_ms = max(0, int(flush_interval_ms))
        self._payload: Any = None
        self._dirty = False
        self._loaded = False

        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.timeout.connect(self.flush)

    def load(self, default_factory: Callable[[], Any]) -> Any:
        if self._loaded:
            return self._payload

        if not self.path.exists():
            self._payload = default_factory()
            self._loaded = True
            self.save(self._payload, immediate=True)
            return self._payload

        try:
            self._payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self._backup_broken_file()
            self.logger.exception("JSON store is invalid. Rebuilding defaults: %s", self.path)
            self._payload = default_factory()
            self._loaded = True
            self.save(self._payload, immediate=True)
            return self._payload

        self._loaded = True
        return self._payload

    def save(self, payload: Any, *, immediate: bool = False) -> None:
        self._payload = payload
        self._loaded = True
        self._dirty = True
        if immediate or self._flush_interval_ms <= 0:
            self.flush()
            return
        self._flush_timer.start(self._flush_interval_ms)

    def flush(self) -> bool:
        if not self._dirty or not self._loaded:
            return True

        self.path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(self._payload, ensure_ascii=False, indent=2)
        try:
            self._write_atomically(serialized)
        except OSError as exc:
            self.logger.warning("Failed to flush JSON store %s: %s", self.path, exc)
            self._schedule_retry()
            return False

        self._dirty = False
        return True

    def is_dirty(self) -> bool:
        return self._dirty

    def _write_atomically(self, serialized: str) -> None:
        backup_path = self.path.with_suffix(f"{self.path.suffix}.bak")
        had_original = self.path.exists()

        if had_original:
            try:
                shutil.copyfile(self.path, backup_path)
            except OSError as exc:
                self.logger.debug("Failed to create JSON backup %s: %s", backup_path, exc)

        try:
            self.path.write_text(serialized, encoding="utf-8")
        except OSError:
            if backup_path.exists():
                try:
                    shutil.copyfile(backup_path, self.path)
                except OSError as exc:
                    self.logger.debug("Failed to restore JSON backup %s: %s", backup_path, exc)
            raise
        finally:
            if backup_path.exists():
                try:
                    backup_path.unlink()
                except OSError:
                    self.logger.debug("Failed to clean up JSON backup: %s", backup_path)

    def _schedule_retry(self) -> None:
        if not self._dirty or self._flush_interval_ms <= 0:
            return
        self._flush_timer.start(max(self._flush_interval_ms, 500))

    def _backup_broken_file(self) -> None:
        backup_path = self.path.with_suffix(".broken.json")
        try:
            self.path.replace(backup_path)
        except OSError:
            self.logger.exception("Failed to back up broken JSON file: %s", self.path)
