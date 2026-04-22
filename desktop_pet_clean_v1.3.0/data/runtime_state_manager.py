from __future__ import annotations

import logging

from data.models import PetVitals
from data.json_store import AtomicJsonStore
from utils.paths import runtime_state_path


class RuntimeStateManager:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self._runtime_state_path = runtime_state_path()
        self._store = AtomicJsonStore(self._runtime_state_path, logger, flush_interval_ms=5000)

    @property
    def path(self):
        return self._runtime_state_path

    def load(self) -> PetVitals:
        payload = self._store.load(lambda: PetVitals.default().to_dict())
        return PetVitals.from_dict(payload)

    def save(self, vitals: PetVitals, *, immediate: bool = False) -> None:
        self._store.save(vitals.to_dict(), immediate=immediate)

    def flush(self) -> None:
        self._store.flush()
