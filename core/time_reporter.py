from __future__ import annotations

from datetime import datetime

from utils.time_utils import hour_key, is_within_hourly_window, now_local


class TimeReporter:
    def __init__(self) -> None:
        self.last_hourly_report_hour: str | None = None
        self.pending_hour_key: str | None = None

    def should_report(self, now: datetime | None = None) -> bool:
        current = now or now_local()
        if not is_within_hourly_window(current):
            return False
        current_key = hour_key(current)
        return current_key != self.last_hourly_report_hour

    def mark_reported(self, now: datetime | None = None) -> None:
        current = now or now_local()
        self.last_hourly_report_hour = hour_key(current)
        self.pending_hour_key = None

    def schedule_pending(self, now: datetime | None = None) -> None:
        current = now or now_local()
        self.pending_hour_key = hour_key(current)

    def can_emit_pending(self, now: datetime | None = None) -> bool:
        current = now or now_local()
        if not self.pending_hour_key:
            return False
        return self.pending_hour_key == hour_key(current) and current.minute == 0
