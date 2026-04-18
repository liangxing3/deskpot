from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from data.models import PetState
from utils.time_utils import ensure_local, now_local

STATE_PRIORITIES: dict[PetState, int] = {
    PetState.IDLE: 0,
    PetState.RANDOM_ANIMATING: 1,
    PetState.MANUAL_ACTION: 2,
    PetState.GROWING: 3,
    PetState.WEATHER_SHOWING: 4,
    PetState.TIME_REPORTING: 5,
    PetState.REMINDING_DRINK: 6,
    PetState.REMINDING_SEDENTARY: 6,
    PetState.INTERACTING: 7,
    PetState.DRAGGING: 8,
}


@dataclass(slots=True)
class PendingStateRequest:
    state: PetState
    ttl_ms: int | None
    payload: dict[str, Any]
    expires_at: datetime | None = None


class StateManager(QObject):
    state_changed = Signal(object, object)

    def __init__(self) -> None:
        super().__init__()
        self._current_state = PetState.IDLE
        self._payload: dict[str, Any] = {}
        self._pending_request: PendingStateRequest | None = None
        self._release_timer = QTimer(self)
        self._release_timer.setSingleShot(True)
        self._release_timer.timeout.connect(self._expire_current_state)

    @property
    def current_state(self) -> PetState:
        return self._current_state

    def current_priority(self) -> int:
        return STATE_PRIORITIES[self._current_state]

    @property
    def current_payload(self) -> dict[str, Any]:
        return dict(self._payload)

    def can_enter(self, state: PetState) -> bool:
        if state == self._current_state:
            return True
        return STATE_PRIORITIES[state] >= STATE_PRIORITIES[self._current_state]

    def request_state(
        self,
        state: PetState,
        ttl_ms: int | None = None,
        payload: dict[str, Any] | None = None,
        *,
        queue_if_blocked: bool = False,
        max_wait_ms: int | None = None,
    ) -> bool:
        if not self.can_enter(state):
            if queue_if_blocked:
                return self.enqueue_or_drop(
                    state,
                    ttl_ms=ttl_ms,
                    payload=payload,
                    max_wait_ms=max_wait_ms,
                )
            return False

        self._activate_state(state, ttl_ms=ttl_ms, payload=payload)
        return True

    def clear_state(self, state: PetState | None = None) -> None:
        if state is not None and state != self._current_state:
            return
        self._release_timer.stop()
        if self._activate_pending_if_any():
            return
        self._current_state = PetState.IDLE
        self._payload = {}
        self.state_changed.emit(self._current_state, {})

    def is_busy(self, minimum_priority: int) -> bool:
        return self.current_priority() >= minimum_priority

    def enqueue_or_drop(
        self,
        state: PetState,
        ttl_ms: int | None = None,
        payload: dict[str, Any] | None = None,
        *,
        max_wait_ms: int | None = None,
    ) -> bool:
        expires_at = None
        if max_wait_ms and max_wait_ms > 0:
            expires_at = now_local() + timedelta(milliseconds=max_wait_ms)

        candidate = PendingStateRequest(
            state=state,
            ttl_ms=ttl_ms,
            payload=payload or {},
            expires_at=expires_at,
        )

        if self._pending_request is None:
            self._pending_request = candidate
            return True

        if STATE_PRIORITIES[state] >= STATE_PRIORITIES[self._pending_request.state]:
            self._pending_request = candidate
            return True
        return False

    def _expire_current_state(self) -> None:
        self.clear_state()

    def _activate_state(
        self,
        state: PetState,
        *,
        ttl_ms: int | None,
        payload: dict[str, Any] | None,
    ) -> None:
        self._current_state = state
        self._payload = payload or {}
        self.state_changed.emit(self._current_state, dict(self._payload))

        if ttl_ms and ttl_ms > 0:
            self._release_timer.start(ttl_ms)
        else:
            self._release_timer.stop()

    def _activate_pending_if_any(self) -> bool:
        if self._pending_request is None:
            return False

        pending = self._pending_request
        self._pending_request = None
        expires_at = ensure_local(pending.expires_at)
        if expires_at is not None and now_local() > expires_at:
            return False

        self._activate_state(
            pending.state,
            ttl_ms=pending.ttl_ms,
            payload=pending.payload,
        )
        return True
