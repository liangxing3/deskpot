from __future__ import annotations

from datetime import datetime
from enum import Enum

from data.models import AppConfig
from utils.time_utils import now_local


class ClickAction(str, Enum):
    DIALOG = "dialog"
    TIME = "time"
    WEATHER = "weather"


class InteractionManager:
    def __init__(self) -> None:
        self.last_interaction_time = now_local()
        self.last_random_dialog_time: datetime | None = None
        self.last_weather_update_time: datetime | None = None
        self._last_click_at: datetime | None = None
        self._rotation = [ClickAction.DIALOG, ClickAction.TIME, ClickAction.WEATHER]
        self._rotation_index = 0

    def can_click(self, config: AppConfig, now: datetime | None = None) -> bool:
        current = now or now_local()
        if self._last_click_at is None:
            return True
        delta = (current - self._last_click_at).total_seconds()
        return delta >= config.dialog_cooldown_seconds

    def register_interaction(
        self,
        now: datetime | None = None,
        *,
        update_click_cooldown: bool = False,
    ) -> None:
        current = now or now_local()
        if update_click_cooldown:
            self._last_click_at = current
        self.last_interaction_time = current

    def register_click(self, now: datetime | None = None) -> None:
        self.register_interaction(now, update_click_cooldown=True)

    def next_click_action(self, has_weather_cache: bool) -> ClickAction:
        attempts = 0
        while attempts < len(self._rotation):
            action = self._rotation[self._rotation_index % len(self._rotation)]
            self._rotation_index = (self._rotation_index + 1) % len(self._rotation)
            if action != ClickAction.WEATHER or has_weather_cache:
                return action
            attempts += 1
        return ClickAction.DIALOG

    def can_emit_random_dialog(
        self,
        config: AppConfig,
        *,
        state_priority: int = 0,
        reminder_recent: bool = False,
    ) -> bool:
        if not config.random_dialog_enabled:
            return False
        if state_priority > 0 or reminder_recent:
            return False
        return True

    def should_trigger_random_dialog(
        self,
        config: AppConfig,
        *,
        now: datetime | None = None,
        state_priority: int = 0,
        reminder_recent: bool = False,
    ) -> bool:
        _ = now
        return self.can_emit_random_dialog(
            config,
            state_priority=state_priority,
            reminder_recent=reminder_recent,
        )

    def mark_random_dialog_shown(self, now: datetime | None = None) -> None:
        current = now or now_local()
        self.last_random_dialog_time = current

    def mark_weather_updated(self, now: datetime | None = None) -> None:
        self.last_weather_update_time = now or now_local()
