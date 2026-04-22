from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from data.models import AppConfig
from ui.dialog_shell import DialogShell
from ui.theme import (
    ACCENT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    base_font_stack,
    line_edit_stylesheet,
    segmented_button_stylesheet,
    soft_card_stylesheet,
    toggle_button_stylesheet,
)


class WeatherSettingsDialog(DialogShell):
    config_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(title="天气设置", icon_name="weather", parent=parent)
        self.resize(320, 360)
        self._updating = False
        self._build_ui()

    def sync_from_config(self, config: AppConfig) -> None:
        self._updating = True
        try:
            self.city_input.setText(config.weather_city_override)
            self.auto_location_toggle.setChecked(config.weather_auto_location)
            self.auto_location_toggle.setText(_toggle_text(config.weather_auto_location))
            self.weather_bubble_toggle.setChecked(config.weather_bubble_enabled)
            self.weather_bubble_toggle.setText(_toggle_text(config.weather_bubble_enabled))
            self.severe_toggle.setChecked(config.weather_severe_alert_enabled)
            self.severe_toggle.setText(_toggle_text(config.weather_severe_alert_enabled))
            self._select_unit_button(config.weather_temperature_unit)
            index = self.time_combo.findData(config.weather_broadcast_time)
            self.time_combo.setCurrentIndex(max(0, index))
            self._sync_enabled_states()
        finally:
            self._updating = False

    def _build_ui(self) -> None:
        location_card = self._card()
        location_layout = QVBoxLayout(location_card)
        location_layout.setContentsMargins(12, 12, 12, 12)
        location_layout.setSpacing(10)
        location_layout.addWidget(self._group_label("位置"))

        self.city_input = QLineEdit(location_card)
        self.city_input.setPlaceholderText("输入城市 / 地区")
        self.city_input.setStyleSheet(line_edit_stylesheet())
        self.city_input.textChanged.connect(self._emit_config_changed)
        location_layout.addLayout(self._input_row("城市 / 地区", "关闭自动定位后优先使用这里的手动城市", self.city_input))

        self.auto_location_toggle = self._toggle_button(True)
        self.auto_location_toggle.clicked.connect(self._emit_config_changed)
        location_layout.addLayout(self._toggle_row("自动获取位置", "开启后优先使用自动定位", self.auto_location_toggle))

        preference_card = self._card()
        preference_layout = QVBoxLayout(preference_card)
        preference_layout.setContentsMargins(12, 12, 12, 12)
        preference_layout.setSpacing(10)
        preference_layout.addWidget(self._group_label("显示偏好"))

        self.unit_buttons = {}
        unit_row = QHBoxLayout()
        unit_row.setSpacing(6)
        unit_group = QButtonGroup(self)
        for value, label in (("C", "°C"), ("F", "°F")):
            button = QPushButton(label, preference_card)
            button.setCheckable(True)
            button.setProperty("unitValue", value)
            button.setStyleSheet(segmented_button_stylesheet())
            button.clicked.connect(self._emit_config_changed)
            unit_group.addButton(button)
            self.unit_buttons[value] = button
            unit_row.addWidget(button)
        preference_layout.addLayout(self._inline_row("温度单位", unit_row))

        self.weather_bubble_toggle = self._toggle_button(True)
        self.weather_bubble_toggle.clicked.connect(self._emit_config_changed)
        preference_layout.addLayout(
            self._toggle_row("天气提示气泡", "控制桌宠是否主动播报天气", self.weather_bubble_toggle)
        )

        self.time_combo = QComboBox(preference_card)
        self.time_combo.setStyleSheet(line_edit_stylesheet())
        for value, label in (
            ("07:30", "早上 7:30"),
            ("08:00", "早上 8:00"),
            ("09:00", "早上 9:00"),
            ("12:00", "中午 12:00"),
            ("18:00", "傍晚 18:00"),
        ):
            self.time_combo.addItem(label, value)
        self.time_combo.currentIndexChanged.connect(self._emit_config_changed)
        preference_layout.addLayout(self._input_row("播报时间", "每天首次天气气泡出现的时间", self.time_combo))

        self.severe_toggle = self._toggle_button(False)
        self.severe_toggle.clicked.connect(self._emit_config_changed)
        preference_layout.addLayout(
            self._toggle_row("恶劣天气提醒", "下雨、大风或极端天气时额外提醒", self.severe_toggle)
        )

        self.body_layout.addWidget(location_card)
        self.body_layout.addWidget(preference_card)
        self.body_layout.addStretch(1)

    def _emit_config_changed(self) -> None:
        if self._updating:
            return
        self._sync_enabled_states()
        config = AppConfig.default()
        config.weather_city_override = self.city_input.text().strip()
        config.weather_auto_location = self.auto_location_toggle.isChecked()
        config.weather_temperature_unit = "F" if self.unit_buttons["F"].isChecked() else "C"
        config.weather_bubble_enabled = self.weather_bubble_toggle.isChecked()
        config.weather_broadcast_time = str(self.time_combo.currentData() or "08:00")
        config.weather_severe_alert_enabled = self.severe_toggle.isChecked()
        self.auto_location_toggle.setText(_toggle_text(config.weather_auto_location))
        self.weather_bubble_toggle.setText(_toggle_text(config.weather_bubble_enabled))
        self.severe_toggle.setText(_toggle_text(config.weather_severe_alert_enabled))
        self.config_changed.emit(config)

    def _select_unit_button(self, unit: str) -> None:
        self.unit_buttons["F" if str(unit).upper() == "F" else "C"].setChecked(True)

    def _sync_enabled_states(self) -> None:
        self.city_input.setEnabled(not self.auto_location_toggle.isChecked())
        self.time_combo.setEnabled(self.weather_bubble_toggle.isChecked())

    @staticmethod
    def _card() -> QWidget:
        card = QWidget()
        card.setStyleSheet(f"QWidget {{{soft_card_stylesheet()}}}")
        return card

    @staticmethod
    def _group_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {ACCENT}; font-size: 10px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
        )
        return label

    @staticmethod
    def _label_pair(title: str, subtitle: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(1)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-family: {base_font_stack(include_emoji=True)};"
        )
        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-family: {base_font_stack(include_emoji=True)};"
        )
        layout.addWidget(title_label)
        layout.addWidget(sub_label)
        return layout

    @classmethod
    def _toggle_row(cls, title: str, subtitle: str, toggle: QPushButton) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addLayout(cls._label_pair(title, subtitle), 1)
        row.addWidget(toggle)
        return row

    @classmethod
    def _input_row(cls, title: str, subtitle: str, widget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addLayout(cls._label_pair(title, subtitle), 1)
        row.addWidget(widget)
        return row

    @classmethod
    def _inline_row(cls, title: str, content: QHBoxLayout) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        label = QLabel(title)
        label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-family: {base_font_stack(include_emoji=True)};"
        )
        row.addWidget(label)
        row.addStretch(1)
        row.addLayout(content)
        return row

    @staticmethod
    def _toggle_button(checked: bool) -> QPushButton:
        button = QPushButton(_toggle_text(checked))
        button.setCheckable(True)
        button.setChecked(checked)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(toggle_button_stylesheet())
        return button


def _toggle_text(value: bool) -> str:
    return "开启" if value else "关闭"


from ui.weather_settings_dialog import WeatherSettingsDialog as _CanonicalWeatherSettingsDialog

WeatherSettingsDialog = _CanonicalWeatherSettingsDialog
