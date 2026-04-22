from __future__ import annotations

from data.models import WeatherAdviceResult, WeatherSnapshot


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

BAD_WEATHER_CODES = {
    301,
    302,
    303,
    304,
    307,
    308,
    310,
    311,
    312,
    403,
    410,
    500,
    501,
    502,
    503,
    504,
    507,
    508,
    509,
    510,
    511,
    512,
    513,
    514,
    515,
}

RAIN_KEYWORDS = (
    "雨",
    "阵雨",
    "雷阵雨",
    "小雨",
    "中雨",
    "大雨",
    "暴雨",
    "冻雨",
    "雨夹雪",
)

BAD_WEATHER_KEYWORDS = (
    "大风",
    "寒潮",
    "暴雪",
    "雷暴",
    "台风",
    "龙卷风",
    "沙尘",
    "冰雹",
    "浓雾",
    "霾",
)


class WeatherCareAdvisor:
    PRIORITY = ("bad_weather", "rain", "cold", "hot", "temperature_gap")
    CATEGORY_MAP = {
        "cold": "weather_clothing",
        "temperature_gap": "weather_temperature_gap",
        "rain": "weather_take_umbrella",
        "hot": "weather_hot_day",
        "bad_weather": "weather_bad_weather",
    }

    def evaluate(self, snapshot: WeatherSnapshot) -> WeatherAdviceResult | None:
        candidates: list[str] = []
        if self._is_bad_weather(snapshot):
            candidates.append("bad_weather")
        if self._needs_umbrella(snapshot):
            candidates.append("rain")
        if self._is_cold(snapshot):
            candidates.append("cold")
        if self._is_hot(snapshot):
            candidates.append("hot")
        if self._has_large_temperature_gap(snapshot):
            candidates.append("temperature_gap")

        for advice_type in self.PRIORITY:
            if advice_type not in candidates:
                continue
            return WeatherAdviceResult(
                advice_type=advice_type,
                dialog_category=self.CATEGORY_MAP[advice_type],
                suggest_take_umbrella=advice_type in {"rain", "bad_weather"},
                suggest_extra_layer=advice_type in {"cold", "temperature_gap"},
                suggest_light_clothing=advice_type == "hot",
            )
        return None

    def _is_cold(self, snapshot: WeatherSnapshot) -> bool:
        current_temp = self._as_float(snapshot.current_temp)
        low_temp = self._as_float(snapshot.low_temp)
        return (current_temp is not None and current_temp <= 12) or (
            low_temp is not None and low_temp <= 10
        )

    def _has_large_temperature_gap(self, snapshot: WeatherSnapshot) -> bool:
        high_temp = self._as_float(snapshot.high_temp)
        low_temp = self._as_float(snapshot.low_temp)
        if high_temp is None or low_temp is None:
            return False
        return (high_temp - low_temp) >= 8

    def _is_hot(self, snapshot: WeatherSnapshot) -> bool:
        current_temp = self._as_float(snapshot.current_temp)
        high_temp = self._as_float(snapshot.high_temp)
        return (current_temp is not None and current_temp >= 30) or (
            high_temp is not None and high_temp >= 32
        )

    def _needs_umbrella(self, snapshot: WeatherSnapshot) -> bool:
        if self._weather_code(snapshot) in RAIN_CODES:
            return True
        if any(keyword in (snapshot.summary or "") for keyword in RAIN_KEYWORDS):
            return True
        probability = self._as_float(snapshot.precipitation_probability)
        return probability is not None and probability >= 40

    def _is_bad_weather(self, snapshot: WeatherSnapshot) -> bool:
        weather_code = self._weather_code(snapshot)
        if weather_code in BAD_WEATHER_CODES or (weather_code is not None and weather_code >= 1001):
            return True
        return any(keyword in (snapshot.summary or "") for keyword in BAD_WEATHER_KEYWORDS)

    @staticmethod
    def _as_float(value: str | int | float | None) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _weather_code(snapshot: WeatherSnapshot) -> int | None:
        try:
            if snapshot.weather_code is None:
                return None
            return int(snapshot.weather_code)
        except (TypeError, ValueError):
            return None
