from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon


class TrayMenu(QObject):
    toggle_visibility_requested = Signal()
    show_pet_status_requested = Signal()
    answerbook_requested = Signal()
    show_weather_requested = Signal()
    pause_reminders_requested = Signal()
    open_settings_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        icon = QApplication.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon = QSystemTrayIcon(icon, parent)

        self.menu = QMenu()
        self.menu.setStyleSheet(
            """
            QMenu {
                background-color: rgba(255, 255, 255, 250);
                border: 1px solid #FFCFDF;
                padding: 6px;
                border-radius: 8px;
                font-family: "Segoe UI Emoji", "Microsoft YaHei UI";
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 6px;
                color: #5A5A5A;
                font-size: 13px;
                margin: 2px 0px;
            }
            QMenu::item:selected {
                background-color: #FFF0F5;
                color: #FF6B9D;
            }
            QMenu::separator {
                height: 1px;
                background: #FFE4E1;
                margin: 4px 8px;
            }
            """
        )

        self.toggle_action = self.menu.addAction("👁️ 显示 / 隐藏桌宠")
        self.status_action = self.menu.addAction("🐾 宠物状态")
        self.answerbook_action = self.menu.addAction("📖 答案之书")
        self.menu.addSeparator()
        self.weather_action = self.menu.addAction("⛅ 立即查看天气")
        self.pause_action = self.menu.addAction("⏸️ 暂停提醒 1 小时")
        self.settings_action = self.menu.addAction("⚙️ 系统设置")
        self.menu.addSeparator()
        self.exit_action = self.menu.addAction("❌ 退出程序")

        self.toggle_action.triggered.connect(self.toggle_visibility_requested.emit)
        self.status_action.triggered.connect(self.show_pet_status_requested.emit)
        self.answerbook_action.triggered.connect(self.answerbook_requested.emit)
        self.weather_action.triggered.connect(self.show_weather_requested.emit)
        self.pause_action.triggered.connect(self.pause_reminders_requested.emit)
        self.settings_action.triggered.connect(self.open_settings_requested.emit)
        self.exit_action.triggered.connect(self.exit_requested.emit)

        self.tray_icon.activated.connect(self._handle_activated)
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.setToolTip("Desktop Pet Assistant")

    def show(self) -> None:
        self.tray_icon.show()

    def hide(self) -> None:
        self.tray_icon.hide()

    def show_message(self, title: str, message: str) -> None:
        self.tray_icon.showMessage(title, message, self.tray_icon.icon(), 3000)

    def _handle_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_visibility_requested.emit()
