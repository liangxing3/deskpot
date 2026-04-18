from __future__ import annotations

import logging
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal

from data.models import DialogMessage, UiMessage
from utils.time_utils import ensure_local, now_local


class NotificationCenter(QObject):
    """Centralized bubble arbitration with priority, cooldown, dedupe, and queueing."""

    message_ready = Signal(object)

    def __init__(self, *, logger: logging.Logger, state_manager) -> None:
        super().__init__()
        self.logger = logger
        self.state_manager = state_manager
        self._cooldowns: dict[str, datetime] = {}
        self._recent_dedupes: dict[str, datetime] = {}
        self._pending: list[UiMessage] = []
        self._active_message: UiMessage | None = None

        self._active_timer = QTimer(self)
        self._active_timer.setSingleShot(True)
        self._active_timer.timeout.connect(self._on_active_expired)

    def publish(self, message: UiMessage) -> bool:
        self._prune_expired()
        if self._should_drop(message):
            return False

        if self._active_message is None:
            self._display(message)
            return True

        if message.priority > self._active_message.priority:
            self._display(message)
            return True

        self._queue(message)
        return True

    def clear(self) -> None:
        self._pending.clear()
        self._active_message = None
        self._active_timer.stop()

    def _should_drop(self, message: UiMessage) -> bool:
        current_priority = self.state_manager.current_priority()
        if (
            message.drop_if_state_at_least is not None
            and current_priority >= message.drop_if_state_at_least
        ):
            return True

        if message.cooldown_key:
            cooldown_until = self._cooldowns.get(message.cooldown_key)
            if cooldown_until and cooldown_until > now_local():
                return True

        if message.dedupe_key:
            dedupe_until = self._recent_dedupes.get(message.dedupe_key)
            if dedupe_until and dedupe_until > now_local():
                return True
        return False

    def _display(self, message: UiMessage) -> None:
        now = now_local()
        self._active_message = message
        if message.cooldown_key and message.cooldown_ms > 0:
            self._cooldowns[message.cooldown_key] = now + timedelta(milliseconds=message.cooldown_ms)
        if message.dedupe_key and message.dedupe_ms > 0:
            self._recent_dedupes[message.dedupe_key] = now + timedelta(milliseconds=message.dedupe_ms)

        dialog = message.to_dialog_message()
        self.message_ready.emit(dialog)
        self._active_timer.start(max(1, message.ttl_ms))

    def _queue(self, message: UiMessage) -> None:
        dedupe_key = message.dedupe_key or f"{message.category}:{message.text}"
        self._pending = [
            existing
            for existing in self._pending
            if (existing.dedupe_key or f"{existing.category}:{existing.text}") != dedupe_key
        ]
        self._pending.append(message)
        self._pending.sort(key=lambda item: item.priority, reverse=True)
        if len(self._pending) > 8:
            self._pending = self._pending[:8]

    def _on_active_expired(self) -> None:
        self._active_message = None
        self._drain_queue()

    def _drain_queue(self) -> None:
        self._prune_expired()
        while self._pending:
            candidate = self._pending.pop(0)
            if self._should_drop(candidate):
                continue
            self._display(candidate)
            return

    def _prune_expired(self) -> None:
        now = now_local()
        self._cooldowns = {
            key: value for key, value in self._cooldowns.items() if ensure_local(value) and value > now
        }
        self._recent_dedupes = {
            key: value
            for key, value in self._recent_dedupes.items()
            if ensure_local(value) and value > now
        }
