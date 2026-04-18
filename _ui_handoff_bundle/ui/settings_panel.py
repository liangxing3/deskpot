from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from data.models import AppConfig
from utils.time_utils import serialize_datetime


class SettingsWindow(QDialog):
    config_changed = Signal(object)
    reset_position_requested = Signal()
    pause_reminders_requested = Signal()
    resume_reminders_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.setModal(False)
        self.resize(520, 380)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #FFF9FB;
                font-family: "Segoe UI Emoji", "Microsoft YaHei UI";
            }
            QListWidget {
                background-color: #FFFFFF;
                border: 2px solid #FFE4E1;
                border-radius: 12px;
                outline: 0;
            }
            QListWidget::item {
                height: 45px;
                border-radius: 8px;
                margin: 4px 8px;
                padding-left: 10px;
                color: #5A5A5A;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF9A9E, stop:1 #FECFEF);
                color: white;
                font-weight: bold;
            }
            QStackedWidget {
                background-color: transparent;
            }
            QLabel {
                color: #5A5A5A;
                font-size: 13px;
            }
            QSpinBox {
                border: 2px solid #FFE4E1;
                border-radius: 6px;
                padding: 4px;
                background: white;
                color: #5A5A5A;
            }
            QCheckBox {
                color: #5A5A5A;
                font-size: 13px;
            }
            QPushButton {
                background-color: #FFB3C6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF9A9E;
            }
            """
        )

        self._current_config = AppConfig.default()
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(300)
        self._save_timer.timeout.connect(self._emit_config)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(140)
        self.stacked_widget = QStackedWidget()

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        main_layout.addWidget(self.nav_list)
        main_layout.addWidget(self.stacked_widget, 1)

        self._init_pages()
        self.nav_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

    def _init_pages(self) -> None:
        general_page = QWidget()
        general_layout = QFormLayout(general_page)
        general_layout.setVerticalSpacing(20)
        self.auto_start_enabled = QCheckBox("🚀 开机自动运行")
        self.reset_position_button = QPushButton("🔄 重置宠物位置")
        self.close_button = QPushButton("关闭")
        general_layout.addRow("", self.auto_start_enabled)
        general_layout.addRow("", self.reset_position_button)
        general_layout.addRow("", self.close_button)

        reminder_page = QWidget()
        reminder_layout = QFormLayout(reminder_page)
        reminder_layout.setVerticalSpacing(15)
        self.drink_interval = QSpinBox()
        self.drink_interval.setRange(10, 240)
        self.sedentary_interval = QSpinBox()
        self.sedentary_interval.setRange(20, 360)
        self.hourly_report_enabled = QCheckBox("🔔 启用整点报时")
        self.pause_status = QLabel("ℹ️ 提醒状态：未暂停")
        self.pause_button = QPushButton("⏸️ 暂停提醒 1 小时")
        self.resume_button = QPushButton("▶️ 恢复提醒")

        reminder_buttons = QHBoxLayout()
        reminder_buttons.addWidget(self.pause_button)
        reminder_buttons.addWidget(self.resume_button)

        reminder_layout.addRow("💧 喝水间隔 (分钟)", self.drink_interval)
        reminder_layout.addRow("🪑 久坐间隔 (分钟)", self.sedentary_interval)
        reminder_layout.addRow("", self.hourly_report_enabled)
        reminder_layout.addRow(self.pause_status)
        reminder_layout.addRow(reminder_buttons)

        interact_page = QWidget()
        interact_layout = QFormLayout(interact_page)
        interact_layout.setVerticalSpacing(20)
        self.random_dialog_enabled = QCheckBox("💬 允许随机自言自语")
        self.cooldown_seconds = QSpinBox()
        self.cooldown_seconds.setRange(1, 30)
        interact_layout.addRow("", self.random_dialog_enabled)
        interact_layout.addRow("⏳ 点击对话冷却 (秒)", self.cooldown_seconds)

        weather_page = QWidget()
        weather_layout = QFormLayout(weather_page)
        weather_layout.setVerticalSpacing(20)
        self.weather_enabled = QCheckBox("⛅ 启用天气服务")
        self.weather_interval = QSpinBox()
        self.weather_interval.setRange(15, 360)
        weather_layout.addRow("", self.weather_enabled)
        weather_layout.addRow("🔄 刷新间隔 (分钟)", self.weather_interval)

        pages = (
            ("📱 常规", general_page),
            ("⏰ 提醒", reminder_page),
            ("🎮 交互", interact_page),
            ("⛅ 天气", weather_page),
        )
        for label, widget in pages:
            self.nav_list.addItem(label)
            self.stacked_widget.addWidget(widget)

        for widget in (
            self.drink_interval,
            self.sedentary_interval,
            self.cooldown_seconds,
            self.weather_interval,
            self.random_dialog_enabled,
            self.hourly_report_enabled,
            self.weather_enabled,
            self.auto_start_enabled,
        ):
            signal = getattr(widget, "valueChanged", None) or widget.toggled
            signal.connect(self._schedule_emit)

        self.pause_button.clicked.connect(self.pause_reminders_requested.emit)
        self.resume_button.clicked.connect(self.resume_reminders_requested.emit)
        self.reset_position_button.clicked.connect(self.reset_position_requested.emit)
        self.close_button.clicked.connect(self.hide)

    def sync_from_config(self, config: AppConfig) -> None:
        self._current_config = AppConfig.from_dict(config.to_dict())
        blockers = [
            QSignalBlocker(self.drink_interval),
            QSignalBlocker(self.sedentary_interval),
            QSignalBlocker(self.cooldown_seconds),
            QSignalBlocker(self.weather_interval),
            QSignalBlocker(self.random_dialog_enabled),
            QSignalBlocker(self.hourly_report_enabled),
            QSignalBlocker(self.weather_enabled),
            QSignalBlocker(self.auto_start_enabled),
        ]
        self.drink_interval.setValue(config.drink_remind_interval_minutes)
        self.sedentary_interval.setValue(config.sedentary_remind_interval_minutes)
        self.cooldown_seconds.setValue(config.dialog_cooldown_seconds)
        self.weather_interval.setValue(config.weather_update_interval_minutes)
        self.random_dialog_enabled.setChecked(config.random_dialog_enabled)
        self.hourly_report_enabled.setChecked(config.hourly_report_enabled)
        self.weather_enabled.setChecked(config.weather_enabled)
        self.auto_start_enabled.setChecked(config.auto_start)

        pause_until = serialize_datetime(config.reminder_pause_until)
        if pause_until:
            self.pause_status.setText(f"ℹ️ 提醒状态：暂停至 {pause_until}")
        else:
            self.pause_status.setText("ℹ️ 提醒状态：运行中")
        del blockers

    def _schedule_emit(self, *args) -> None:
        self._save_timer.start()

    def _emit_config(self) -> None:
        self._current_config.drink_remind_interval_minutes = self.drink_interval.value()
        self._current_config.sedentary_remind_interval_minutes = self.sedentary_interval.value()
        self._current_config.dialog_cooldown_seconds = self.cooldown_seconds.value()
        self._current_config.weather_update_interval_minutes = self.weather_interval.value()
        self._current_config.random_dialog_enabled = self.random_dialog_enabled.isChecked()
        self._current_config.hourly_report_enabled = self.hourly_report_enabled.isChecked()
        self._current_config.weather_enabled = self.weather_enabled.isChecked()
        self._current_config.auto_start = self.auto_start_enabled.isChecked()
        self.config_changed.emit(AppConfig.from_dict(self._current_config.to_dict()))
