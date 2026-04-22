from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from data.models import WeatherAlertState, WeatherSnapshot
from utils.time_utils import now_local


DEFAULT_WEATHER_ALERT_COOLDOWN_HOURS = 3
WEATHER_CHANGE_TTL_MS = 6_200
VALID_SENSITIVITIES = {"low", "standard", "high"}

SENSITIVITY_THRESHOLDS = {
    "low": {
        "temp": 5.0,
        "temp_strong": 6.0,
        "feels_like": 5.0,
        "wind_scale": 3.0,
        "wind_speed": 12.0,
        "humidity": 25.0,
        "pop_jump": 45.0,
    },
    "standard": {
        "temp": 3.0,
        "temp_strong": 5.0,
        "feels_like": 3.0,
        "wind_scale": 2.0,
        "wind_speed": 8.0,
        "humidity": 20.0,
        "pop_jump": 35.0,
    },
    "high": {
        "temp": 2.0,
        "temp_strong": 4.0,
        "feels_like": 2.0,
        "wind_scale": 1.0,
        "wind_speed": 5.0,
        "humidity": 15.0,
        "pop_jump": 25.0,
    },
}

RAIN_CODES = {
    300,
    301,
    302,
    303,
    304,
    305,
    306,
    307,
    308,
    309,
    310,
    311,
    312,
    313,
    314,
    315,
    316,
    317,
    318,
    350,
    351,
    399,
    404,
    405,
    406,
    456,
}
SNOW_CODES = {400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 456, 457, 499, 1030}
THUNDER_CODES = {302, 303, 304, 1031, 1020, 1014}
WIND_CODES = {503, 504, 1001, 1002, 1006}
FOG_CODES = {500, 501, 502, 509, 510, 511, 512, 513, 514, 515, 1017, 1019, 1029}
HEAVY_RAIN_CODES = {307, 308, 310, 311, 312, 316, 317, 318, 1038}

RAIN_KEYWORDS = ("雨", "阵雨", "雷阵雨", "冻雨", "雨夹雪", "rain", "shower")
THUNDER_KEYWORDS = ("雷", "雷暴", "雷阵雨", "thunder")
SNOW_KEYWORDS = ("雪", "snow", "sleet")
WIND_KEYWORDS = ("大风", "风", "wind", "gust")
FOG_KEYWORDS = ("雾", "霾", "沙尘", "haze", "fog", "mist")
CLEAR_KEYWORDS = ("晴", "clear", "sunny")
CLOUD_KEYWORDS = ("阴", "云", "cloud", "overcast")


@dataclass(slots=True)
class WeatherChangeResult:
    significant: bool
    change_types: list[str] = field(default_factory=list)
    message: str | None = None
    signature: str | None = None
    severity_rank: int = 0
    bypass_cooldown: bool = False
    details: list[str] = field(default_factory=list)
    cooldown_hours: int = DEFAULT_WEATHER_ALERT_COOLDOWN_HOURS
    ttl_ms: int = WEATHER_CHANGE_TTL_MS
    context_reset: bool = False


@dataclass(slots=True)
class _ChangeCandidate:
    kind: str
    signature: str
    message: str
    score: int
    bypass_cooldown: bool = False
    detail: str | None = None


def weather_context_key(snapshot: WeatherSnapshot | None) -> str:
    if snapshot is None:
        return ""
    base = str(snapshot.location or snapshot.city or "").strip().lower()
    return base


def compare_weather_snapshots(
    previous: WeatherSnapshot | None,
    current: WeatherSnapshot | None,
    *,
    sensitivity: str = "standard",
) -> WeatherChangeResult:
    if previous is None or current is None:
        return WeatherChangeResult(significant=False)
    if weather_context_key(previous) != weather_context_key(current):
        return WeatherChangeResult(
            significant=False,
            change_types=["context_reset"],
            context_reset=True,
        )

    thresholds = SENSITIVITY_THRESHOLDS[_normalize_sensitivity(sensitivity)]
    candidates: list[_ChangeCandidate] = []
    change_types: list[str] = []
    details: list[str] = []

    alert_candidate = _compare_alerts(previous, current)
    if alert_candidate is not None:
        candidates.append(alert_candidate)
        change_types.append(alert_candidate.kind)
        if alert_candidate.detail:
            details.append(alert_candidate.detail)

    prev_family = _condition_family(previous)
    curr_family = _condition_family(current)
    prev_severity = _condition_severity(previous, prev_family)
    curr_severity = _condition_severity(current, curr_family)
    prev_precipitating = _has_precipitation(previous, prev_family)
    curr_precipitating = _has_precipitation(current, curr_family)

    if not prev_precipitating and curr_precipitating:
        candidate = _ChangeCandidate(
            kind="rain_start",
            signature="rain_start",
            message="小狗提醒你：外面好像开始下雨啦，出门记得看伞",
            score=95,
        )
        candidates.append(candidate)
        change_types.append(candidate.kind)
    elif curr_precipitating and curr_severity > prev_severity and curr_severity >= 3:
        candidate = _ChangeCandidate(
            kind="rain_stronger",
            signature=f"rain_upgrade_{curr_severity}",
            message="雨势比上一小时明显大了，出门记得多留意",
            score=90,
            bypass_cooldown=curr_severity >= 4,
        )
        candidates.append(candidate)
        change_types.append(candidate.kind)

    if prev_family != curr_family and "rain_start" not in change_types:
        candidate = _build_condition_shift_candidate(prev_family, curr_family)
        if candidate is not None:
            candidates.append(candidate)
            change_types.append(candidate.kind)

    temp_delta = _numeric_delta(current.current_temp, previous.current_temp)
    if temp_delta is not None and abs(temp_delta) >= thresholds["temp"]:
        strong = abs(temp_delta) >= thresholds["temp_strong"]
        if temp_delta <= 0:
            message = "现在比上一小时冷了不少，记得多穿一点"
            signature = f"temp_drop_{5 if strong else 3}"
            kind = "temp_drop"
        else:
            message = "外面一下子热了些，别忘了补水"
            signature = f"temp_rise_{5 if strong else 3}"
            kind = "temp_rise"
        candidate = _ChangeCandidate(
            kind=kind,
            signature=signature,
            message=message,
            score=82 if strong else 68,
            detail=f"温度变化 {temp_delta:+.1f}°C",
        )
        candidates.append(candidate)
        change_types.append(candidate.kind)
        details.append(candidate.detail or "")

    feels_like_delta = _numeric_delta(current.feels_like, previous.feels_like)
    if feels_like_delta is not None and abs(feels_like_delta) >= thresholds["feels_like"]:
        if feels_like_delta <= 0:
            candidate = _ChangeCandidate(
                kind="feels_like_drop",
                signature="feels_like_drop_3",
                message="体感温度降得有点快，注意别着凉",
                score=60,
                detail=f"体感变化 {feels_like_delta:+.1f}°C",
            )
        else:
            candidate = _ChangeCandidate(
                kind="feels_like_rise",
                signature="feels_like_rise_3",
                message="现在体感闷热了些，记得让自己舒服一点",
                score=58,
                detail=f"体感变化 {feels_like_delta:+.1f}°C",
            )
        candidates.append(candidate)
        change_types.append(candidate.kind)
        details.append(candidate.detail or "")

    wind_scale_delta = _numeric_delta(_wind_scale_value(current), _wind_scale_value(previous))
    wind_speed_delta = _numeric_delta(current.wind_speed, previous.wind_speed)
    if (
        wind_scale_delta is not None
        and wind_scale_delta >= thresholds["wind_scale"]
    ) or (
        wind_speed_delta is not None
        and wind_speed_delta >= thresholds["wind_speed"]
    ):
        magnitude = wind_scale_delta if wind_scale_delta is not None else wind_speed_delta
        candidate = _ChangeCandidate(
            kind="wind_up",
            signature=f"wind_up_{int(max(1, round(magnitude or 1)))}",
            message="风变大啦，注意别着凉",
            score=72,
            detail=f"风力增强 {magnitude:+.1f}" if magnitude is not None else None,
        )
        candidates.append(candidate)
        change_types.append(candidate.kind)
        if candidate.detail:
            details.append(candidate.detail)

    humidity_delta = _numeric_delta(current.humidity, previous.humidity)
    if humidity_delta is not None and abs(humidity_delta) >= thresholds["humidity"]:
        change_types.append("humidity_shift")
        details.append(f"湿度变化 {humidity_delta:+.0f}%")

    previous_pop = _as_float(previous.precipitation_probability)
    current_pop = _as_float(current.precipitation_probability)
    if (
        previous_pop is not None
        and current_pop is not None
        and not curr_precipitating
        and current_pop >= 50
        and (current_pop - previous_pop) >= thresholds["pop_jump"]
    ):
        candidate = _ChangeCandidate(
            kind="rain_risk_up",
            signature="rain_risk_up",
            message="降雨可能性在往上走，出门可以顺手带把伞",
            score=64,
            detail=f"降雨概率上升到 {current_pop:.0f}%",
        )
        candidates.append(candidate)
        change_types.append(candidate.kind)
        if candidate.detail:
            details.append(candidate.detail)

    aqi_candidate = _compare_aqi(previous, current)
    if aqi_candidate is not None:
        candidates.append(aqi_candidate)
        change_types.append(aqi_candidate.kind)
        if aqi_candidate.detail:
            details.append(aqi_candidate.detail)

    if not candidates:
        return WeatherChangeResult(significant=False, change_types=change_types, details=details)

    primary = max(candidates, key=lambda item: item.score)
    return WeatherChangeResult(
        significant=True,
        change_types=change_types or [primary.kind],
        message=primary.message,
        signature=primary.signature,
        severity_rank=primary.score,
        bypass_cooldown=primary.bypass_cooldown,
        details=[detail for detail in details if detail],
    )


def should_emit_weather_change(
    result: WeatherChangeResult,
    alert_state: WeatherAlertState,
    *,
    current_time=None,
) -> bool:
    if not result.significant or not result.signature or not result.message:
        return False
    now = current_time or now_local()
    prune_weather_alert_cooldowns(alert_state, current_time=now, cooldown_hours=result.cooldown_hours)
    if result.bypass_cooldown:
        return True
    last_sent = alert_state.cooldown_signatures.get(result.signature)
    if last_sent is None:
        return True
    return now - last_sent >= timedelta(hours=result.cooldown_hours)


def record_weather_change(
    alert_state: WeatherAlertState,
    result: WeatherChangeResult,
    *,
    current_time=None,
) -> None:
    if not result.signature:
        return
    now = current_time or now_local()
    prune_weather_alert_cooldowns(alert_state, current_time=now, cooldown_hours=result.cooldown_hours)
    alert_state.cooldown_signatures[result.signature] = now


def prune_weather_alert_cooldowns(
    alert_state: WeatherAlertState,
    *,
    current_time=None,
    cooldown_hours: int = DEFAULT_WEATHER_ALERT_COOLDOWN_HOURS,
) -> None:
    now = current_time or now_local()
    expire_before = now - timedelta(hours=max(1, int(cooldown_hours)))
    alert_state.cooldown_signatures = {
        signature: timestamp
        for signature, timestamp in alert_state.cooldown_signatures.items()
        if timestamp is not None and timestamp >= expire_before
    }


def update_weather_alert_state_snapshot(
    alert_state: WeatherAlertState,
    snapshot: WeatherSnapshot,
    *,
    reset_context: bool = False,
) -> None:
    if reset_context:
        alert_state.cooldown_signatures.clear()
    alert_state.last_snapshot = snapshot
    alert_state.last_context_key = weather_context_key(snapshot)


def _compare_alerts(previous: WeatherSnapshot, current: WeatherSnapshot) -> _ChangeCandidate | None:
    previous_tokens = set(_alert_tokens(previous))
    current_tokens = _alert_tokens(current)
    if current_tokens:
        first_token = current_tokens[0]
        current_level = max((_alert_level(token) for token in current_tokens), default=0)
        previous_level = max((_alert_level(token) for token in previous_tokens), default=0)
        if set(current_tokens) - previous_tokens:
            return _ChangeCandidate(
                kind="new_weather_alert",
                signature=f"new_weather_alert_{_alert_signature(first_token, current_level)}",
                message="刚刚有新的天气预警，记得关注一下哦",
                score=100,
                bypass_cooldown=True,
                detail=first_token,
            )
        if current_level > previous_level and current_level > 0:
            return _ChangeCandidate(
                kind="alert_level_up",
                signature=f"weather_alert_level_up_{current_level}",
                message="天气预警级别升高了，出门前记得多看一眼",
                score=98,
                bypass_cooldown=True,
                detail=first_token,
            )
    return None


def _build_condition_shift_candidate(previous_family: str, current_family: str) -> _ChangeCandidate | None:
    if not current_family:
        return None
    message = {
        ("clear", "cloud"): "外面转阴了，出门前可以顺手看下天气",
        ("cloud", "clear"): "外面放晴了一些，不过出门前还是可以多看一眼",
        ("clear", "fog"): "外面能见度差了一些，出门记得多留神",
        ("cloud", "fog"): "外面雾气重了一些，出门记得多留神",
        ("clear", "wind"): "外面起风了，出门记得护好自己",
    }.get((previous_family, current_family))
    if message is None:
        if current_family == "fog":
            message = "外面能见度差了一些，出门记得多留神"
        elif current_family == "wind":
            message = "外面风大了一些，记得别着凉"
        elif current_family == "snow":
            message = "外面下雪啦，出门记得注意脚下"
        else:
            message = "外面的天气和刚才不太一样了，出门前可以顺手看一眼"
    return _ChangeCandidate(
        kind="condition_shift",
        signature=f"condition_{previous_family or 'unknown'}_to_{current_family}",
        message=message,
        score=56,
    )


def _compare_aqi(previous: WeatherSnapshot, current: WeatherSnapshot) -> _ChangeCandidate | None:
    previous_grade = _aqi_grade(_as_float(previous.aqi))
    current_grade = _aqi_grade(_as_float(current.aqi))
    if current_grade is None or previous_grade is None:
        return None
    if current_grade["index"] < 2:
        return None
    if current_grade["index"] <= previous_grade["index"]:
        return None
    return _ChangeCandidate(
        kind="aqi_worse",
        signature=f"aqi_worse_{current_grade['slug']}",
        message="空气质量变差了，出门可以留意一下",
        score=78 if current_grade["index"] >= 3 else 70,
        detail=f"AQI 等级变为 {current_grade['label']}",
    )


def _alert_tokens(snapshot: WeatherSnapshot) -> list[str]:
    if snapshot.warning_texts:
        return [str(item).strip() for item in snapshot.warning_texts if str(item).strip()]
    if snapshot.alerts:
        rendered: list[str] = []
        for alert in snapshot.alerts:
            text = _first_non_empty(
                alert.get("title"),
                alert.get("name"),
                alert.get("warning"),
                alert.get("text"),
                alert.get("content"),
                alert.get("description"),
            )
            if text:
                rendered.append(text)
        return rendered
    return []


def _alert_level(text: str) -> int:
    normalized = _normalize_text(text)
    if "红" in normalized or "red" in normalized:
        return 4
    if "橙" in normalized or "orange" in normalized:
        return 3
    if "黄" in normalized or "yellow" in normalized:
        return 2
    if "蓝" in normalized or "blue" in normalized:
        return 1
    return 0


def _alert_signature(text: str, level: int) -> str:
    normalized = _normalize_text(text)
    if "暴雨" in normalized:
        label = "storm"
    elif "雷" in normalized:
        label = "thunder"
    elif "大风" in normalized or "风" in normalized:
        label = "wind"
    elif "高温" in normalized:
        label = "heat"
    elif "寒潮" in normalized:
        label = "cold"
    else:
        label = "general"
    return f"{label}_{level}" if level else label


def _condition_family(snapshot: WeatherSnapshot) -> str:
    text = _normalize_text(snapshot.condition_text or snapshot.summary)
    code = _weather_code(snapshot)
    if any(keyword in text for keyword in THUNDER_KEYWORDS) or code in THUNDER_CODES:
        return "thunder"
    if any(keyword in text for keyword in SNOW_KEYWORDS) or code in SNOW_CODES:
        return "snow"
    if any(keyword in text for keyword in RAIN_KEYWORDS) or code in RAIN_CODES:
        return "rain"
    if any(keyword in text for keyword in FOG_KEYWORDS) or code in FOG_CODES:
        return "fog"
    if any(keyword in text for keyword in WIND_KEYWORDS) or code in WIND_CODES:
        return "wind"
    if any(keyword in text for keyword in CLEAR_KEYWORDS):
        return "clear"
    if any(keyword in text for keyword in CLOUD_KEYWORDS):
        return "cloud"
    return "unknown"


def _condition_severity(snapshot: WeatherSnapshot, family: str) -> int:
    text = _normalize_text(snapshot.condition_text or snapshot.summary)
    code = _weather_code(snapshot)
    if family == "thunder":
        return 5
    if family == "rain":
        if "暴雨" in text or "大暴雨" in text or code in HEAVY_RAIN_CODES:
            return 4
        if "大雨" in text or "强降雨" in text:
            return 3
        if "中雨" in text:
            return 2
        return 1
    if family == "snow":
        if "暴雪" in text or "大雪" in text:
            return 4
        if "中雪" in text:
            return 2
        return 1
    if family in {"fog", "wind"}:
        return 2
    if family == "cloud":
        return 1
    return 0


def _has_precipitation(snapshot: WeatherSnapshot, family: str) -> bool:
    if family in {"rain", "snow", "thunder"}:
        return True
    precipitation = _as_float(snapshot.precipitation)
    pop = _as_float(snapshot.precipitation_probability)
    return (precipitation is not None and precipitation > 0) or (pop is not None and pop >= 60)


def _aqi_grade(value: float | None) -> dict[str, Any] | None:
    if value is None:
        return None
    if value <= 50:
        return {"index": 0, "label": "优", "slug": "excellent"}
    if value <= 100:
        return {"index": 1, "label": "良", "slug": "good"}
    if value <= 150:
        return {"index": 2, "label": "轻度污染", "slug": "light"}
    if value <= 200:
        return {"index": 3, "label": "中度污染", "slug": "moderate"}
    if value <= 300:
        return {"index": 4, "label": "重度污染", "slug": "heavy"}
    return {"index": 5, "label": "严重污染", "slug": "severe"}


def _wind_scale_value(snapshot: WeatherSnapshot) -> float | None:
    return _extract_max_number(snapshot.wind_scale)


def _numeric_delta(current: Any, previous: Any) -> float | None:
    current_value = _as_float(current)
    previous_value = _as_float(previous)
    if current_value is None or previous_value is None:
        return None
    return current_value - previous_value


def _extract_max_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value)
    numeric_parts: list[float] = []
    current = ""
    for char in text:
        if char.isdigit() or char == ".":
            current += char
            continue
        if current:
            try:
                numeric_parts.append(float(current))
            except ValueError:
                pass
            current = ""
    if current:
        try:
            numeric_parts.append(float(current))
        except ValueError:
            pass
    if not numeric_parts:
        return None
    return max(numeric_parts)


def _weather_code(snapshot: WeatherSnapshot) -> int | None:
    try:
        if snapshot.condition_code is not None:
            return int(snapshot.condition_code)
        if snapshot.weather_code is not None:
            return int(snapshot.weather_code)
    except (TypeError, ValueError):
        return None
    return None


def _normalize_sensitivity(value: str) -> str:
    normalized = str(value or "standard").strip().lower()
    if normalized in VALID_SENSITIVITIES:
        return normalized
    return "standard"


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        if value not in (None, ""):
            rendered = str(value).strip()
            if rendered:
                return rendered
    return None


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
