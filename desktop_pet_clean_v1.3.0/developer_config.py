from __future__ import annotations

import os
from typing import Any


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

APP_NAME = "DesktopPetAssistantV1"
APP_EXE_NAME = "DesktopPetAssistantV1.exe"

UAPI_BASE_URL = os.getenv("DESKTOP_PET_UAPI_BASE_URL", "https://uapis.cn")
UAPI_TOKEN = os.getenv(
    "DESKTOP_PET_UAPI_TOKEN",
    "uapi-w-oqtkk3jGvyomTGMXsosOhvuSx517UwKb7lHkt4",
)
UAPI_TIMEOUT = float(os.getenv("DESKTOP_PET_UAPI_TIMEOUT", "5.0"))
UAPI_RANDOM_DIALOG_OPERATION = os.getenv("DESKTOP_PET_UAPI_OPERATION", "poem.get_saying")
UAPI_ANSWERBOOK_OPERATION = os.getenv(
    "DESKTOP_PET_UAPI_ANSWERBOOK_OPERATION",
    "random.get_answerbook_ask",
)

IP_CITY_BASE_URL = os.getenv("DESKTOP_PET_IP_CITY_BASE_URL", "")
IP_CITY_PATH = os.getenv("DESKTOP_PET_IP_CITY_PATH", "")
IP_CITY_TOKEN = os.getenv("DESKTOP_PET_IP_CITY_TOKEN", "")
IP_CITY_TIMEOUT = float(os.getenv("DESKTOP_PET_IP_CITY_TIMEOUT", "5.0"))

WEATHER_BASE_URL = os.getenv("DESKTOP_PET_WEATHER_BASE_URL", UAPI_BASE_URL)
WEATHER_PATH = os.getenv("DESKTOP_PET_WEATHER_PATH", "/api/v1/misc/weather")
WEATHER_TOKEN = os.getenv("DESKTOP_PET_WEATHER_TOKEN", UAPI_TOKEN)
WEATHER_TIMEOUT = float(os.getenv("DESKTOP_PET_WEATHER_TIMEOUT", "5.0"))
WEATHER_DEFAULT_CITY = os.getenv("DESKTOP_PET_WEATHER_CITY", "")
WEATHER_DEFAULT_ADCODE = os.getenv("DESKTOP_PET_WEATHER_ADCODE", "")
WEATHER_OPERATION = os.getenv("DESKTOP_PET_WEATHER_OPERATION", "misc.get_misc_weather")
WEATHER_LANG = os.getenv("DESKTOP_PET_WEATHER_LANG", "zh")
WEATHER_INCLUDE_EXTENDED = _env_bool("DESKTOP_PET_WEATHER_EXTENDED", True)
WEATHER_INCLUDE_FORECAST = _env_bool("DESKTOP_PET_WEATHER_FORECAST", True)
WEATHER_INCLUDE_HOURLY = _env_bool("DESKTOP_PET_WEATHER_HOURLY", False)
WEATHER_INCLUDE_MINUTELY = _env_bool("DESKTOP_PET_WEATHER_MINUTELY", False)
WEATHER_INCLUDE_INDICES = _env_bool("DESKTOP_PET_WEATHER_INDICES", False)

DEFAULT_DIALOG_DEDUP_TTL_SECONDS = 30 * 60
DEFAULT_CITY_CACHE_TTL_SECONDS = 24 * 60 * 60
DEFAULT_WEATHER_CACHE_TTL_SECONDS = 60 * 60
DEFAULT_REMOTE_DIALOG_CACHE_TTL_SECONDS = 60 * 60


def build_ip_city_request() -> dict[str, Any]:
    if not (IP_CITY_BASE_URL and IP_CITY_PATH):
        raise NotImplementedError("Configure IP city base URL and path in developer_config.py.")

    url = f"{IP_CITY_BASE_URL.rstrip('/')}/{IP_CITY_PATH.lstrip('/')}"
    headers = {}
    if IP_CITY_TOKEN:
        headers["Authorization"] = f"Bearer {IP_CITY_TOKEN}"
    return {"url": url, "params": {}, "headers": headers, "timeout": IP_CITY_TIMEOUT}


def parse_ip_city_response(payload: Any) -> str | None:
    candidates = (
        ("city",),
        ("data", "city"),
        ("location", "city"),
        ("result", "city"),
    )
    for path in candidates:
        current = payload
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if isinstance(current, str) and current.strip():
            return current.strip()
    return None


def build_weather_request(city: str) -> dict[str, Any]:
    if not (WEATHER_BASE_URL and WEATHER_PATH):
        raise NotImplementedError("Configure weather base URL and path in developer_config.py.")

    url = f"{WEATHER_BASE_URL.rstrip('/')}/{WEATHER_PATH.lstrip('/')}"
    params = {"city": city}
    headers = {}
    if WEATHER_TOKEN:
        headers["Authorization"] = f"Bearer {WEATHER_TOKEN}"
    return {"url": url, "params": params, "headers": headers, "timeout": WEATHER_TIMEOUT}


def parse_weather_response(payload: Any, city: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Weather payload must be a dictionary.")

    data = payload.get("data", payload)
    forecast = data.get("forecast") or []
    first_forecast = forecast[0] if forecast and isinstance(forecast[0], dict) else {}
    wind_direction = data.get("wind_direction") or data.get("wind_dir")
    wind_power = data.get("wind_power") or data.get("wind_scale")
    city_name = data.get("city") or city
    district = data.get("district")
    if district and district != city_name:
        city_name = f"{city_name}·{district}"
    return {
        "city": city_name or city,
        "summary": data.get("summary") or data.get("weather") or data.get("text"),
        "current_temp": data.get("current_temp") or data.get("temp") or data.get("temperature"),
        "high_temp": data.get("high_temp")
        or data.get("temp_max")
        or first_forecast.get("temp_max"),
        "low_temp": data.get("low_temp")
        or data.get("temp_min")
        or first_forecast.get("temp_min"),
        "humidity": data.get("humidity"),
        "wind": " ".join(part for part in (wind_direction, wind_power) if part),
        "weather_code": data.get("weather_code") or data.get("weather_icon"),
    }


def invoke_uapi_dialog_operation(
    client: Any,
    operation_name: str,
    *,
    category: str,
    context: dict[str, Any] | None = None,
) -> Any:
    operation = client
    for part in operation_name.split("."):
        operation = getattr(operation, part, None)
        if operation is None:
            raise AttributeError(f"Unknown UAPI dialog operation: {operation_name}")

    if not callable(operation):
        raise TypeError(f"UAPI dialog operation is not callable: {operation_name}")

    params = build_uapi_dialog_params(category=category, context=context)
    return operation(**params)


def build_uapi_dialog_params(
    *,
    category: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = category
    _ = context
    return {}


def invoke_uapi_answerbook_operation(
    client: Any,
    operation_name: str,
    *,
    question: str,
) -> Any:
    operation = client
    for part in operation_name.split("."):
        operation = getattr(operation, part, None)
        if operation is None:
            raise AttributeError(f"Unknown UAPI answerbook operation: {operation_name}")

    if not callable(operation):
        raise TypeError(f"UAPI answerbook operation is not callable: {operation_name}")

    return operation(question=question)


def invoke_uapi_weather_operation(
    client: Any,
    operation_name: str,
    *,
    city: str | None = None,
    adcode: str | None = None,
) -> Any:
    operation = client
    for part in operation_name.split("."):
        operation = getattr(operation, part, None)
        if operation is None:
            raise AttributeError(f"Unknown UAPI weather operation: {operation_name}")

    if not callable(operation):
        raise TypeError(f"UAPI weather operation is not callable: {operation_name}")

    params = build_uapi_weather_params(city=city, adcode=adcode)
    return operation(**params)


def build_uapi_weather_params(
    *,
    city: str | None = None,
    adcode: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"lang": WEATHER_LANG}
    resolved_adcode = adcode or WEATHER_DEFAULT_ADCODE or None
    resolved_city = city or WEATHER_DEFAULT_CITY or None
    if resolved_adcode:
        params["adcode"] = resolved_adcode
    elif resolved_city:
        params["city"] = resolved_city

    if WEATHER_INCLUDE_EXTENDED:
        params["extended"] = True
    if WEATHER_INCLUDE_FORECAST:
        params["forecast"] = True
    if WEATHER_INCLUDE_HOURLY:
        params["hourly"] = True
    if WEATHER_INCLUDE_MINUTELY:
        params["minutely"] = True
    if WEATHER_INCLUDE_INDICES:
        params["indices"] = True
    return params

