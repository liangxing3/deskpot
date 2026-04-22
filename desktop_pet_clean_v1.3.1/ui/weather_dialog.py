from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from data.models import WeatherSnapshot
from ui.dialog_shell import DialogShell
from ui.theme import Colors, Metrics, Typography, base_font_stack, soft_button_stylesheet, soft_card_stylesheet


def _rgba(color, alpha: int | None = None) -> str:
    resolved_alpha = color.alpha() if alpha is None else int(alpha)
    return f"rgba({color.red()},{color.green()},{color.blue()},{resolved_alpha})"


class WeatherDialog(DialogShell):
    refresh_requested = Signal()
    open_settings_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(title="天气", icon_name="weather", parent=parent)
        self.resize(312, 346)
        self.setMinimumWidth(300)
        self._unit = "C"
        self._weather_icon_text = "☁"
        self._build_ui()

    def set_temperature_unit(self, unit: str) -> None:
        self._unit = "F" if str(unit).upper() == "F" else "C"

    def set_loading(self) -> None:
        self._show_status_card("正在获取天气", "请稍等一下，小狗马上带回新的天气情况。", error=False)

    def set_error(self, message: str) -> None:
        self._show_status_card("天气暂时不可用", message or "当前没有可显示的天气数据。", error=True)

    def update_snapshot(self, snapshot: WeatherSnapshot | None) -> None:
        if snapshot is None:
            self.set_error("当前没有可显示的天气数据。")
            return

        self.status_card.hide()
        self.content_wrap.show()

        self.city_label.setText(snapshot.city or "当前位置")
        self.update_time_label.setText("刚刚更新")
        self.temp_value_label.setText(self._format_temp(snapshot.current_temp))
        self.temp_unit_label.setText(f"°{self._unit}")
        self.desc_label.setText(snapshot.summary or "天气已更新")
        self._weather_icon_text = self._icon_for_snapshot(snapshot)
        self.hero_icon_label.setText(self._weather_icon_text)

        feels_like = getattr(snapshot, "feels_like", None)
        visibility = getattr(snapshot, "visibility", None)
        precipitation_probability = getattr(snapshot, "precipitation_probability", None)
        high = self._format_temp(snapshot.high_temp, include_unit=True)
        low = self._format_temp(snapshot.low_temp, include_unit=True)

        self._set_metric_card(self.humidity_value_label, "湿度", self._format_humidity(snapshot.humidity))
        self._set_metric_card(self.wind_value_label, "风况", snapshot.wind or "--")
        self._set_metric_card(
            self.feels_like_value_label,
            "体感温度" if feels_like not in (None, "") else "最高 / 最低",
            self._format_temp(feels_like, include_unit=True) if feels_like not in (None, "") else f"{high} / {low}",
        )
        self._set_metric_card(
            self.visibility_value_label,
            "能见度" if visibility not in (None, "") else "降水概率",
            self._format_visibility(visibility) if visibility not in (None, "") else self._format_precipitation_probability(precipitation_probability),
        )

    def _build_ui(self) -> None:
        self.body_layout.setContentsMargins(10, 10, 10, 10)
        self.body_layout.setSpacing(0)

        self.content_panel = QWidget(self.body)
        self.content_panel.setStyleSheet(_content_panel_stylesheet())
        panel_layout = QVBoxLayout(self.content_panel)
        panel_layout.setContentsMargins(14, 14, 14, 14)
        panel_layout.setSpacing(12)

        self.content_wrap = QWidget(self.content_panel)
        content_layout = QVBoxLayout(self.content_wrap)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        content_layout.addLayout(self._build_location_row())
        content_layout.addWidget(self._build_hero_card())
        content_layout.addLayout(self._build_detail_grid())

        self.status_card = self._build_status_card()
        self.status_card.hide()

        panel_layout.addWidget(self.content_wrap, 1)
        panel_layout.addWidget(self.status_card, 1)
        self.body_layout.addWidget(self.content_panel, 1)

    def _build_location_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        left = QHBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(5)
        location_icon = QLabel("⌖", self.content_wrap)
        location_icon.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()}; font-size: 13px; font-family: {base_font_stack(include_emoji=True)};"
        )
        self.city_label = QLabel("等待更新", self.content_wrap)
        self.city_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: 14px; font-weight: 500; font-family: {base_font_stack(include_emoji=True)};"
        )
        left.addWidget(location_icon)
        left.addWidget(self.city_label)
        left.addStretch(1)

        right = QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(6)
        self.refresh_button = QPushButton("↻", self.content_wrap)
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setStyleSheet(_refresh_button_stylesheet())
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.update_time_label = QLabel("等待刷新", self.content_wrap)
        self.update_time_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()}; font-size: 11px; font-family: {base_font_stack(include_emoji=True)};"
        )
        right.addWidget(self.refresh_button)
        right.addWidget(self.update_time_label)

        row.addLayout(left, 1)
        row.addLayout(right, 0)
        return row

    def _build_hero_card(self) -> QWidget:
        card = QWidget(self.content_panel)
        card.setStyleSheet(
            f"QWidget {{{soft_card_stylesheet()} background: {_rgba(Colors.BG_INPUT, 232)};}}"
        )
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self.hero_icon_label = QLabel("☁", card)
        self.hero_icon_label.setAlignment(Qt.AlignCenter)
        self.hero_icon_label.setFixedSize(48, 48)
        self.hero_icon_label.setStyleSheet(
            f"color: {Colors.ACCENT_BLUE.name()}; font-size: 44px; font-family: {base_font_stack(include_emoji=True)};"
        )

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(4)

        temp_row = QHBoxLayout()
        temp_row.setContentsMargins(0, 0, 0, 0)
        temp_row.setSpacing(4)
        self.temp_value_label = QLabel("--", card)
        self.temp_value_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: 56px; font-weight: 300; font-family: {base_font_stack(include_emoji=True)};"
        )
        self.temp_unit_label = QLabel("°C", card)
        self.temp_unit_label.setAlignment(Qt.AlignBottom)
        self.temp_unit_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()}; font-size: 24px; font-family: {base_font_stack(include_emoji=True)}; margin-bottom: 6px;"
        )
        temp_row.addWidget(self.temp_value_label)
        temp_row.addWidget(self.temp_unit_label, 0, Qt.AlignBottom)
        temp_row.addStretch(1)

        self.desc_label = QLabel("等待天气数据", card)
        self.desc_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()}; font-size: 15px; font-family: {base_font_stack(include_emoji=True)};"
        )

        right.addLayout(temp_row)
        right.addWidget(self.desc_label)

        layout.addWidget(self.hero_icon_label, 0, Qt.AlignCenter)
        layout.addLayout(right, 1)
        return card

    def _build_detail_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        self.humidity_value_label, humidity_card = self._metric_card("湿度")
        self.wind_value_label, wind_card = self._metric_card("风况")
        self.feels_like_value_label, feels_like_card = self._metric_card("体感温度")
        self.visibility_value_label, visibility_card = self._metric_card("能见度")

        grid.addWidget(humidity_card, 0, 0)
        grid.addWidget(wind_card, 0, 1)
        grid.addWidget(feels_like_card, 1, 0)
        grid.addWidget(visibility_card, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        return grid

    def _build_status_card(self) -> QWidget:
        card = QWidget(self.content_panel)
        card.setStyleSheet(
            f"QWidget {{{soft_card_stylesheet()} background: {_rgba(Colors.BG_INPUT, 236)};}}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self.status_title_label = QLabel("天气状态", card)
        self.status_title_label.setStyleSheet(
            f"color: {Colors.PRIMARY_TEXT.name()}; font-size: 13px; font-weight: 500; font-family: {base_font_stack(include_emoji=True)};"
        )
        self.status_message_label = QLabel("", card)
        self.status_message_label.setWordWrap(True)
        self.status_message_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()}; font-size: 12px; font-family: {base_font_stack(include_emoji=True)};"
        )
        self.retry_button = QPushButton("重试", card)
        self.retry_button.setCursor(Qt.PointingHandCursor)
        self.retry_button.setStyleSheet(soft_button_stylesheet(primary=True))
        self.retry_button.clicked.connect(self.refresh_requested.emit)

        layout.addWidget(self.status_title_label)
        layout.addWidget(self.status_message_label)
        layout.addWidget(self.retry_button, 0, Qt.AlignLeft)
        return card

    def _metric_card(self, title: str) -> tuple[QLabel, QWidget]:
        card = QWidget(self.content_panel)
        card.setStyleSheet(
            f"QWidget {{{soft_card_stylesheet()} background: {_rgba(Colors.BG_CARD, 252)};}}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(4)

        name_label = QLabel(title, card)
        name_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()}; font-size: 11px; font-family: {base_font_stack(include_emoji=True)};"
        )
        value_label = QLabel("--", card)
        value_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: 18px; font-weight: 500; font-family: {base_font_stack(include_emoji=True)};"
        )

        layout.addWidget(name_label)
        layout.addWidget(value_label)
        return value_label, card

    def _show_status_card(self, title: str, message: str, *, error: bool) -> None:
        self.content_wrap.hide()
        self.status_card.show()
        self.status_title_label.setText(title)
        self.status_message_label.setText(message)
        self.retry_button.setVisible(error)
        accent = Colors.DANGER if error else Colors.PRIMARY
        tone_alpha = 34 if error else 24
        self.status_card.setStyleSheet(
            f"QWidget {{{soft_card_stylesheet()} background: {_rgba(accent, tone_alpha)};}}"
        )

    @staticmethod
    def _set_metric_card(value_label: QLabel, name: str, value: str) -> None:
        value_label.setText(value)
        value_label.setToolTip(f"{name}: {value}")

    def _format_temp(self, value, *, include_unit: bool = False) -> str:
        if value in (None, ""):
            return "--"
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)
        if self._unit == "F":
            numeric = numeric * 9 / 5 + 32
        rounded = int(round(numeric))
        return f"{rounded}°{self._unit}" if include_unit else f"{rounded}"

    @staticmethod
    def _format_humidity(value) -> str:
        if value in (None, ""):
            return "--"
        try:
            return f"{int(round(float(value)))}%"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_visibility(value) -> str:
        if value in (None, ""):
            return "--"
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)
        if numeric.is_integer():
            return f"{int(numeric)} km"
        return f"{numeric:.1f} km"

    @staticmethod
    def _format_precipitation_probability(value) -> str:
        if value in (None, ""):
            return "--"
        try:
            return f"{int(round(float(value)))}%"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _icon_for_snapshot(snapshot: WeatherSnapshot) -> str:
        summary = (snapshot.summary or "").lower()
        if "雨" in summary or "rain" in summary:
            return "☂"
        if "雪" in summary or "snow" in summary:
            return "❄"
        if "晴" in summary or "sun" in summary or "clear" in summary:
            return "☀"
        return "☁"


def _refresh_button_stylesheet() -> str:
    return f"""
    QPushButton {{
        background: transparent;
        border: none;
        color: {Colors.TEXT_SECONDARY.name()};
        font-size: 16px;
        font-family: {base_font_stack(include_emoji=True)};
        min-width: 22px;
        max-width: 22px;
    }}
    QPushButton:hover {{
        color: {Colors.PRIMARY_TEXT.name()};
    }}
    QPushButton:pressed {{
        color: {Colors.PRIMARY.name()};
    }}
    """


def _content_panel_stylesheet() -> str:
    return (
        "QWidget {"
        f"{soft_card_stylesheet()}"
        f"background: {_rgba(Colors.BG_CARD, 252)};"
        f"border-radius: {Metrics.RADIUS_LG}px;"
        "}"
    )
