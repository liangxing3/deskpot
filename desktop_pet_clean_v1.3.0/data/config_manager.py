from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher

from app.signal_bus import get_bus
from data.models import AppConfig
from data.json_store import AtomicJsonStore
from utils.paths import config_path, default_config_template_path, runtime_state_path


class ConfigManager:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self._config_path = config_path()
        self._template_path = default_config_template_path()
        self._runtime_path = runtime_state_path()
        self._store = AtomicJsonStore(self._config_path, logger, flush_interval_ms=300)
        self._watcher: QFileSystemWatcher | None = None

    @property
    def path(self):
        return self._config_path

    def load(self) -> AppConfig:
        defaults = self._load_default_template().to_dict()
        user_layer = self._store.load(lambda: {})
        runtime_layer = self._load_runtime_overrides()
        payload = {}
        payload.update(defaults)
        payload.update(user_layer if isinstance(user_layer, dict) else {})
        payload.update(runtime_layer)
        return AppConfig.from_dict(payload)

    def save(self, config: AppConfig, *, immediate: bool = False) -> None:
        self._store.save(config.to_dict(), immediate=immediate)

    def flush(self) -> None:
        self._store.flush()

    def watch_user_config(self) -> None:
        if self._watcher is not None:
            return
        self._watcher = QFileSystemWatcher([str(self._config_path)], self._store)
        self._watcher.fileChanged.connect(self._on_user_config_changed)

    def _load_default_template(self) -> AppConfig:
        if self._template_path.exists():
            try:
                payload = json.loads(self._template_path.read_text(encoding="utf-8"))
                return AppConfig.from_dict(payload)
            except Exception:
                self.logger.exception("Default config template is invalid. Falling back to dataclass.")
        return AppConfig.default()

    def _load_runtime_overrides(self) -> dict:
        if not self._runtime_path.exists():
            return {}
        try:
            payload = json.loads(self._runtime_path.read_text(encoding="utf-8"))
        except Exception:
            self.logger.exception("Runtime config layer is invalid: %s", self._runtime_path)
            return {}
        if isinstance(payload, dict) and isinstance(payload.get("config_overrides"), dict):
            return dict(payload["config_overrides"])
        return {}

    def _on_user_config_changed(self, changed_path: str) -> None:
        if changed_path and changed_path not in {str(self._config_path), str(Path(changed_path))}:
            return
        if self._watcher is not None and str(self._config_path) not in self._watcher.files():
            self._watcher.addPath(str(self._config_path))
        get_bus().theme_changed.emit()
