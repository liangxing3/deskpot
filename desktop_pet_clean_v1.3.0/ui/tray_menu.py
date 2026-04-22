from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app.app_metadata import tray_tooltip
from ui.icons import make_icon
from ui.theme import menu_stylesheet
from utils.app_icon import load_app_icon


class TrayMenu(QObject):
    toggle_visibility_requested = Signal()
    activate_requested = Signal()
    show_status_requested = Signal()
    show_weather_requested = Signal()
    show_answerbook_requested = Signal()
    open_settings_requested = Signal()
    check_update_requested = Signal()
    show_about_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        tray_icon = load_app_icon()
        if tray_icon is None:
            tray_icon = make_icon("pet", size=24)
        self.tray_icon = QSystemTrayIcon(tray_icon, parent)

        self.menu = QMenu()
        self.menu.setStyleSheet(menu_stylesheet(13))

        self.toggle_action = self.menu.addAction(make_icon("pet"), "显示 / 隐藏宠物")
        self.menu.addSeparator()
        self.weather_action = self.menu.addAction(make_icon("weather"), "天气")
        self.answerbook_action = self.menu.addAction(make_icon("answerbook"), "答案之书")
        self.status_action = self.menu.addAction(make_icon("status"), "状态面板")
        self.settings_action = self.menu.addAction(make_icon("settings"), "设置")
        self.menu.addSeparator()
        self.check_update_action = self.menu.addAction(make_icon("status"), "检查更新")
        self.about_action = self.menu.addAction(make_icon("pet"), "关于")
        self.menu.addSeparator()
        self.exit_action = self.menu.addAction("退出")

        for action in (self.weather_action, self.answerbook_action, self.status_action, self.settings_action):
            action.setCheckable(True)

        self.toggle_action.triggered.connect(self.toggle_visibility_requested.emit)
        self.status_action.triggered.connect(self.show_status_requested.emit)
        self.weather_action.triggered.connect(self.show_weather_requested.emit)
        self.answerbook_action.triggered.connect(self.show_answerbook_requested.emit)
        self.settings_action.triggered.connect(self.open_settings_requested.emit)
        self.check_update_action.triggered.connect(self.check_update_requested.emit)
        self.about_action.triggered.connect(self.show_about_requested.emit)
        self.exit_action.triggered.connect(self.exit_requested.emit)
        self.tray_icon.activated.connect(self._handle_activated)
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.setToolTip(tray_tooltip())

    def show(self) -> None:
        self.tray_icon.show()

    def hide(self) -> None:
        self.tray_icon.hide()

    def show_message(self, title: str, message: str) -> None:
        self.tray_icon.showMessage(title, message, self.tray_icon.icon(), 3000)

    def set_menu_font_size(self, size_px: int) -> None:
        self.menu.setStyleSheet(menu_stylesheet(size_px))

    def set_window_states(
        self,
        *,
        weather_open: bool,
        answerbook_open: bool,
        status_open: bool,
        settings_open: bool,
    ) -> None:
        self.weather_action.setChecked(weather_open)
        self.answerbook_action.setChecked(answerbook_open)
        self.status_action.setChecked(status_open)
        self.settings_action.setChecked(settings_open)

    def _handle_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.activate_requested.emit()
