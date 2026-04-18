from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from data.json_store import AtomicJsonStore
from utils.paths import cache_path
from utils.time_utils import now_local, parse_datetime, serialize_datetime


class CacheService:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.path = cache_path()
        self._json_store = AtomicJsonStore(self.path, logger, flush_interval_ms=2000)
        self._store = self._json_store.load(dict)

    def get(self, key: str, *, allow_expired: bool = False) -> Any | None:
        entry = self._store.get(key)
        if not entry:
            return None
        expires_at = parse_datetime(entry.get("expires_at"))
        if expires_at and expires_at < now_local() and not allow_expired:
            return None
        return entry.get("value")

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        expires_at = None
        if ttl_seconds:
            expires_at = now_local() + timedelta(seconds=ttl_seconds)
        self._store[key] = {"value": value, "expires_at": serialize_datetime(expires_at)}
        self._save_store()

    def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]
            self._save_store()

    def flush(self) -> None:
        self._json_store.flush()

    def _save_store(self) -> None:
        self._json_store.save(self._store)
