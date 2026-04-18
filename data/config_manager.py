from __future__ import annotations

import logging

from data.models import AppConfig
from data.json_store import AtomicJsonStore
from utils.paths import config_path, default_config_template_path


class ConfigManager:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self._config_path = config_path()
        self._template_path = default_config_template_path()
        self._store = AtomicJsonStore(self._config_path, logger, flush_interval_ms=300)

    @property
    def path(self):
        return self._config_path

    def load(self) -> AppConfig:
        payload = self._store.load(lambda: self._load_default_template().to_dict())
        return AppConfig.from_dict(payload)

    def save(self, config: AppConfig, *, immediate: bool = False) -> None:
        self._store.save(config.to_dict(), immediate=immediate)

    def flush(self) -> None:
        self._store.flush()

    def _load_default_template(self) -> AppConfig:
        if self._template_path.exists():
            try:
                import json

                payload = json.loads(self._template_path.read_text(encoding="utf-8"))
                return AppConfig.from_dict(payload)
            except Exception:
                self.logger.exception("Default config template is invalid. Falling back to dataclass.")
        return AppConfig.default()
