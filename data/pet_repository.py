from __future__ import annotations

import logging

from data.json_store import AtomicJsonStore
from data.pet_models import PetStatus
from utils.paths import pet_status_path


class PetRepository:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self._path = pet_status_path()
        self._store = AtomicJsonStore(self._path, logger, flush_interval_ms=5000)

    @property
    def path(self):
        return self._path

    def load(self) -> PetStatus:
        payload = self._store.load(lambda: PetStatus.default().to_dict())
        status = PetStatus.from_dict(payload)
        status.normalize()
        return status

    def save(self, status: PetStatus, *, immediate: bool = False) -> None:
        status.normalize()
        self._store.save(status.to_dict(), immediate=immediate)

    def flush(self) -> None:
        self._store.flush()
