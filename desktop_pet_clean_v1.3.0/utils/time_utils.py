from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def now_local() -> datetime:
    return datetime.now().astimezone()


def ensure_local(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.astimezone()
    return value


def serialize_datetime(value: datetime | None) -> str | None:
    value = ensure_local(value)
    return value.isoformat() if value else None


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return ensure_local(value)
    if isinstance(value, str):
        return ensure_local(datetime.fromisoformat(value))
    raise TypeError(f"Unsupported datetime value: {type(value)!r}")


def hour_key(value: datetime | None = None) -> str:
    current = ensure_local(value) or now_local()
    return current.strftime("%Y-%m-%dT%H")


def date_key(value: datetime | None = None) -> str:
    current = ensure_local(value) or now_local()
    return current.strftime("%Y-%m-%d")


def is_within_hourly_window(value: datetime | None = None) -> bool:
    current = ensure_local(value) or now_local()
    return current.minute == 0


def seconds_since(reference: datetime | None, now: datetime | None = None) -> float:
    if reference is None:
        return 0.0
    current = ensure_local(now) or now_local()
    return (current - ensure_local(reference)).total_seconds()


def minutes_since(reference: datetime | None, now: datetime | None = None) -> float:
    return seconds_since(reference, now) / 60.0


def plus_hours(hours: int, now: datetime | None = None) -> datetime:
    current = ensure_local(now) or now_local()
    return current + timedelta(hours=hours)
