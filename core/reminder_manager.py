from __future__ import annotations

from datetime import datetime

from data.models import AppConfig, PetState
from utils.time_utils import now_local


class ReminderManager:
    ANY_REMINDER_GAP_SECONDS = 5 * 60

    def __init__(self) -> None:
        self.last_drink_remind_time: datetime | None = None
        self.last_sedentary_remind_time: datetime | None = None
        self.last_any_reminder_time: datetime | None = None

    def should_pause(self, config: AppConfig, now: datetime | None = None) -> bool:
        current = now or now_local()
        pause_until = config.reminder_pause_until
        return bool(pause_until and current < pause_until)

    def due_reminder(
        self,
        config: AppConfig,
        *,
        last_interaction_time: datetime,
        now: datetime | None = None,
    ) -> PetState | None:
        current = now or now_local()
        if self.should_pause(config, current):
            return None
        if self.last_any_reminder_time and (
            current - self.last_any_reminder_time
        ).total_seconds() < self.ANY_REMINDER_GAP_SECONDS:
            return None

        inactive_minutes = (current - last_interaction_time).total_seconds() / 60.0
        if inactive_minutes >= config.sedentary_remind_interval_minutes and self._can_repeat(
            current, self.last_sedentary_remind_time, 30
        ):
            return PetState.REMINDING_SEDENTARY
        if inactive_minutes >= config.drink_remind_interval_minutes and self._can_repeat(
            current, self.last_drink_remind_time, 15
        ):
            return PetState.REMINDING_DRINK
        return None

    def mark_reminded(self, state: PetState, now: datetime | None = None) -> None:
        current = now or now_local()
        self.last_any_reminder_time = current
        if state == PetState.REMINDING_DRINK:
            self.last_drink_remind_time = current
        elif state == PetState.REMINDING_SEDENTARY:
            self.last_sedentary_remind_time = current

    def reminder_recent(self, now: datetime | None = None, within_seconds: int = 120) -> bool:
        current = now or now_local()
        if self.last_any_reminder_time is None:
            return False
        return (current - self.last_any_reminder_time).total_seconds() <= within_seconds

    @staticmethod
    def _can_repeat(now: datetime, last_time: datetime | None, min_gap_minutes: int) -> bool:
        if last_time is None:
            return True
        return (now - last_time).total_seconds() >= min_gap_minutes * 60
