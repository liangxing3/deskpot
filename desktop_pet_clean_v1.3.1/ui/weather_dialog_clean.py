from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from data.models import WeatherSnapshot
from ui.dialog_shell import DialogShell
from ui.theme import ACCENT, TEXT_MUTED, TEXT_PRIMARY, base_font_stack, soft_button_stylesheet, soft_card_stylesheet


class WeatherDialog(DialogShell):
    refresh_requested = Signal()
    open_settings_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(title="天气", icon_name="weather", parent=parent)
        self.resize(320, 280)
        self._unit = "C"
        self._build_ui()

    def set_temperature_unit(self, unit: str) -> None:
        self._unit = "F" if str(unit).upper() == "F" else "C"

    def set_loading(self) -> None:
        self.temp_label.setText("--")
        self.city_label.setText("正在更新")
        self.desc_label.setText("天气数据获取中...")

    def set_error(self, message: str) -> None:
        self.temp_label.setText("--")
        self.city_label.setText("天气不可用")
        self.desc_label.setText(message)
        self._set_metric_card(self.humidity_value, self.humidity_label, "--", "湿度")
        self._set_metric_card(self.wind_value, self.wind_label, "--", "风况")
        self._set_metric_card(self.feel_value, self.feel_label, "--", "高 / 低")

    def update_snapshot(self, snapshot: WeatherSnapshot | None) -> None:
        if snapshot is None:
            self.set_error("暂时没有可显示的天气数据。")
            return

        self.temp_label.setText(self._format_temp(snapshot.current_temp))
        self.city_label.setText(snapshot.city or "当前位置")
        self.desc_label.setText(snapshot.summary or "天气已更新")
        self._set_metric_card(
            self.humidity_value,
            self.humidity_label,
            f"{snapshot.humidity}%" if snapshot.humidity is not None else "--",
            "湿度",
        )
        self._set_metric_card(self.wind_value, self.wind_label, snapshot.wind or "--", "风况")
        high = self._format_temp(snapshot.high_temp, include_unit=True)
        low = self._format_temp(snapshot.low_temp, include_unit=True)
        self._set_metric_card(self.feel_value, self.feel_label, f"{high} / {low}", "高 / 低")

    def _build_ui(self) -> None:
        summary_card = QWidget()
        summary_card.setStyleSheet(f"QWidget {{{soft_card_stylesheet()}}}")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(14, 12, 14, 12)
        summary_layout.setSpacing(4)

        self.temp_label = QLabel("--", summary_card)
        self.temp_label.setAlignment(Qt.AlignCenter)
        self.temp_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 38px; font-weight: 300; font-family: {base_font_stack(include_emoji=True)};"
        )
        self.city_label = QLabel("等待更新", summary_card)
        self.city_label.setAlignment(Qt.AlignCenter)
        self.city_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-family: {base_font_stack(include_emoji=True)};"
        )
        self.desc_label = QLabel("打开后会自动刷新天气摘要。", summary_card)
        self.desc_label.setWordWrap(True)
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setStyleSheet(
            f"color: {ACCENT}; font-size: 12px; font-weight: 500; font-family: {base_font_stack(include_emoji=True)};"
        )
        summary_layout.addWidget(self.temp_label)
        summary_layout.addWidget(self.city_label)
        summary_layout.addWidget(self.desc_label)

        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(7)
        self.humidity_value, self.humidity_label, humidity_card = self._metric_card()
        self.wind_value, self.wind_label, wind_card = self._metric_card()
        self.feel_value, self.feel_label, feel_card = self._metric_card()
        metrics_grid.addWidget(humidity_card, 0, 0)
        metrics_grid.addWidget(wind_card, 0, 1)
        metrics_grid.addWidget(feel_card, 0, 2)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        refresh_button = QPushButton("刷新", self.body)
        refresh_button.setStyleSheet(soft_button_stylesheet(primary=False))
        refresh_button.clicked.connect(self.refresh_requested.emit)
        settings_button = QPushButton("天气设置...", self.body)
        settings_button.setStyleSheet(soft_button_stylesheet(primary=True))
        settings_button.clicked.connect(self.open_settings_requested.emit)
        button_row.addWidget(refresh_button)
        button_row.addWidget(settings_button)

        self.body_layout.addWidget(summary_card)
        self.body_layout.addLayout(metrics_grid)
        self.body_layout.addLayout(button_row)

    @staticmethod
    def _metric_card() -> tuple[QLabel, QLabel, QWidget]:
        card = QWidget()
        card.setStyleSheet(f"QWidget {{{soft_card_stylesheet()}}}")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        value = QLabel("--", card)
        value.setAlignment(Qt.AlignCenter)
        value.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 500; font-family: {base_font_stack(include_emoji=True)};"
        )
        label = QLabel("", card)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-family: {base_font_stack(include_emoji=True)};"
        )
        layout.addWidget(value)
        layout.addWidget(label)
        return value, label, card

    @staticmethod
    def _set_metric_card(value_label: QLabel, name_label: QLabel, value: str, name: str) -> None:
        value_label.setText(value)
        name_label.setText(name)

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
        return f"{rounded}°{self._unit}" if include_unit else f"{rounded}°"


from ui.weather_dialog import WeatherDialog as _CanonicalWeatherDialog

WeatherDialog = _CanonicalWeatherDialog
