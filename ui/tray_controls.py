from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from utils.font_loader import ui_font_stack


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
            f"""
            QMenu {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 255),
                    stop:1 rgba(255, 253, 255, 255));
                border: 1px solid #FFCFDF;
                padding: 8px;
                border-radius: 12px;
                font-family: {ui_font_stack(include_emoji=True)};
            }}
            QMenu::item {{
                padding: 10px 28px;
                border-radius: 8px;
                color: #5A5A5A;
                font-size: 14px;
                margin: 3px 0px;
                font-weight: 500;
            }}
            QMenu::item:selected {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFF0F5,
                    stop:1 #FFE8EC);
                color: #FF6B9D;
                font-weight: 600;
            }}
            QMenu::separator {{
                height: 1px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent,
                    stop:0.5 #FFE4E1,
                    stop:1 transparent);
                margin: 6px 12px;
            }}
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