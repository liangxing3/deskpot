from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from data.models import PetVitals
from utils.time_utils import date_key, ensure_local, now_local


@dataclass(frozen=True, slots=True)
class DaypartWindow:
    name: str
    start_hour: int
    end_hour: int

    def matches(self, current: datetime) -> bool:
        return self.start_hour <= current.hour <= self.end_hour


class DaypartWeatherReporter:
    WINDOWS: tuple[DaypartWindow, ...] = (
        DaypartWindow("morning", 7, 10),
        DaypartWindow("noon", 11, 14),
        DaypartWindow("evening", 18, 21),
    )
    FIELD_MAP = {
        "morning": "weather_morning_date",
        "noon": "weather_noon_date",
        "evening": "weather_evening_date",
    }

    def __init__(self, vitals: PetVitals) -> None:
        self.vitals = vitals

    def current_daypart(self, now: datetime | None = None) -> str | None:
        current = ensure_local(now) or now_local()
        for window in self.WINDOWS:
            if window.matches(current):
                return window.name
        return None

    def has_reported_current_daypart(self, now: datetime | None = None) -> bool:
        daypart = self.current_daypart(now)
        if daypart is None:
            return False
        return self.has_reported(daypart, now)

    def has_reported(self, daypart: str, now: datetime | None = None) -> bool:
        expected = date_key(now)
        field_name = self.FIELD_MAP[daypart]
        return getattr(self.vitals, field_name, None) == expected

    def should_auto_report(self, now: datetime | None = None) -> bool:
        daypart = self.current_daypart(now)
        if daypart is None:
            return False
        return not self.has_reported(daypart, now)

    def mark_reported_for_current_daypart(self, now: datetime | None = None) -> str | None:
        daypart = self.current_daypart(now)
        if daypart is None:
            return None
        setattr(self.vitals, self.FIELD_MAP[daypart], date_key(now))
        return daypart
