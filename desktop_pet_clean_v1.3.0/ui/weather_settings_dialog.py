from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from data.models import AppConfig
from ui.dialog_shell import DialogShell
from ui.theme import (
    Colors,
    Metrics,
    Typography,
    base_font_stack,
    line_edit_stylesheet,
    segmented_button_stylesheet,
    toggle_button_stylesheet,
)


class WeatherSettingsDialog(DialogShell):
    config_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(title="天气设置", icon_name="weather", parent=parent)
        self.resize(360, 520)
        self.setMinimumSize(340, 500)
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
            self.background_monitor_toggle.setChecked(config.weather_background_monitor_enabled)
            self.background_monitor_toggle.setText(_toggle_text(config.weather_background_monitor_enabled))
            self.change_alert_toggle.setChecked(config.weather_change_alert_enabled)
            self.change_alert_toggle.setText(_toggle_text(config.weather_change_alert_enabled))
            self._select_unit_button(config.weather_temperature_unit)
            index = self.time_combo.findData(config.weather_broadcast_time)
            self.time_combo.setCurrentIndex(max(0, index))
            sensitivity_index = self.sensitivity_combo.findData(config.weather_change_alert_sensitivity)
            self.sensitivity_combo.setCurrentIndex(max(0, sensitivity_index))
            self._sync_enabled_states()
        finally:
            self._updating = False

    def _build_ui(self) -> None:
        self.body_layout.setContentsMargins(Metrics.PADDING_LG, Metrics.PADDING_LG, Metrics.PADDING_LG, Metrics.PADDING_LG)
        self.body_layout.setSpacing(12)

        hero = self._card(background=_rgba(Colors.BG_INPUT, 248), border_alpha=70, radius=Metrics.RADIUS_LG)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(14, 12, 14, 12)
        hero_layout.setSpacing(4)
        title = QLabel("天气偏好", hero)
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()};"
            f"font-size: {Typography.SIZE_H1}px;"
            "font-weight: 600;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        subtitle = QLabel("设置位置、单位与播报时间，让小狗更懂你。", hero)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()};"
            "font-size: 12px;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        self.body_layout.addWidget(hero)

        location_card = self._card(background=_rgba(Colors.BG_CARD, 252), border_alpha=78, radius=Metrics.RADIUS_MD)
        location_layout = QVBoxLayout(location_card)
        location_layout.setContentsMargins(16, 12, 16, 14)
        location_layout.setSpacing(8)
        location_layout.addWidget(self._group_label("位置"))

        self.city_input = QLineEdit(location_card)
        self.city_input.setPlaceholderText("输入城市 / 地区")
        self.city_input.setStyleSheet(line_edit_stylesheet())
        self.city_input.textChanged.connect(self._emit_config_changed)
        location_layout.addLayout(self._input_row("城市 / 地区", "手动输入时将优先使用这里的城市", self.city_input))

        self.auto_location_toggle = self._toggle_button(True)
        self.auto_location_toggle.clicked.connect(self._emit_config_changed)
        location_layout.addLayout(self._toggle_row("自动获取位置", "开启后优先使用自动定位", self.auto_location_toggle))

        preference_card = self._card(background=_rgba(Colors.BG_CARD, 252), border_alpha=78, radius=Metrics.RADIUS_MD)
        preference_layout = QVBoxLayout(preference_card)
        preference_layout.setContentsMargins(16, 12, 16, 14)
        preference_layout.setSpacing(8)
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

        monitor_card = self._card(background=_rgba(Colors.BG_CARD, 252), border_alpha=78, radius=Metrics.RADIUS_MD)
        monitor_layout = QVBoxLayout(monitor_card)
        monitor_layout.setContentsMargins(16, 12, 16, 14)
        monitor_layout.setSpacing(8)
        monitor_layout.addWidget(self._group_label("后台监测"))

        self.background_monitor_toggle = self._toggle_button(True)
        self.background_monitor_toggle.clicked.connect(self._emit_config_changed)
        monitor_layout.addLayout(
            self._toggle_row("后台天气监测", "每小时自动获取一次天气快照", self.background_monitor_toggle)
        )

        self.change_alert_toggle = self._toggle_button(True)
        self.change_alert_toggle.clicked.connect(self._emit_config_changed)
        monitor_layout.addLayout(
            self._toggle_row("显著变化提醒", "只在天气变化明显时给出气泡提醒", self.change_alert_toggle)
        )

        self.sensitivity_combo = QComboBox(monitor_card)
        self.sensitivity_combo.setStyleSheet(line_edit_stylesheet())
        for value, label in (
            ("low", "低"),
            ("standard", "标准"),
            ("high", "高"),
        ):
            self.sensitivity_combo.addItem(label, value)
        self.sensitivity_combo.currentIndexChanged.connect(self._emit_config_changed)
        monitor_layout.addLayout(
            self._input_row("提醒敏感度", "控制温度、风力与降雨变化的触发阈值", self.sensitivity_combo)
        )

        self.body_layout.addWidget(location_card)
        self.body_layout.addWidget(preference_card)
        self.body_layout.addWidget(monitor_card)
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
        config.weather_background_monitor_enabled = self.background_monitor_toggle.isChecked()
        config.weather_change_alert_enabled = self.change_alert_toggle.isChecked()
        config.weather_change_alert_sensitivity = str(self.sensitivity_combo.currentData() or "standard")
        self.auto_location_toggle.setText(_toggle_text(config.weather_auto_location))
        self.weather_bubble_toggle.setText(_toggle_text(config.weather_bubble_enabled))
        self.severe_toggle.setText(_toggle_text(config.weather_severe_alert_enabled))
        self.background_monitor_toggle.setText(_toggle_text(config.weather_background_monitor_enabled))
        self.change_alert_toggle.setText(_toggle_text(config.weather_change_alert_enabled))
        self.config_changed.emit(config)

    def _select_unit_button(self, unit: str) -> None:
        self.unit_buttons["F" if str(unit).upper() == "F" else "C"].setChecked(True)

    def _sync_enabled_states(self) -> None:
        self.city_input.setEnabled(not self.auto_location_toggle.isChecked())
        self.time_combo.setEnabled(self.weather_bubble_toggle.isChecked())
        self.change_alert_toggle.setEnabled(self.background_monitor_toggle.isChecked())
        self.sensitivity_combo.setEnabled(
            self.background_monitor_toggle.isChecked() and self.change_alert_toggle.isChecked()
        )

    @staticmethod
    def _card(*, background: str, border_alpha: int, radius: int) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            "QWidget {"
            f"background: {background};"
            f"border: 1px solid {_rgba(Colors.BORDER_DEFAULT, int(border_alpha))};"
            f"border-radius: {int(radius)}px;"
            "outline: none;"
            "}"
        )
        return card

    @staticmethod
    def _group_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()};"
            "font-size: 12px;"
            "font-weight: 600;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        return label

    @staticmethod
    def _label_pair(title: str, subtitle: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(1)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()};"
            "font-size: 12px;"
            "font-weight: 600;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet(
            f"color: {_rgba(Colors.TEXT_SECONDARY, 200)};"
            "font-size: 10px;"
            f"font-family: {base_font_stack(include_emoji=True)};"
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
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: 12px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
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


def _rgba(color, alpha: int | None = None) -> str:
    resolved_alpha = color.alpha() if alpha is None else int(alpha)
    return f"rgba({color.red()},{color.green()},{color.blue()},{resolved_alpha})"


def _toggle_text(value: bool) -> str:
    return "开启" if value else "关闭"
