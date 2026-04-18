from __future__ import annotations

import random

from PySide6.QtWidgets import QApplication

from data.models import DialogMessage, EmotionState, WindowPosition


class UiCoordinator:
    """Owns window-level interactions and screen-aware positioning."""

    def __init__(
        self,
        *,
        app: QApplication,
        pet_window,
        settings_window,
        pet_status_panel,
        tray_menu,
    ) -> None:
        self.app = app
        self.pet_window = pet_window
        self.settings_window = settings_window
        self.pet_status_panel = pet_status_panel
        self.tray_menu = tray_menu

    def bind(
        self,
        *,
        on_pet_clicked,
        on_drag_started,
        on_drag_finished,
        on_quick_action,
        on_config_changed,
        on_pause_reminders,
        on_resume_reminders,
        on_reset_position,
        on_pet_status_action,
        on_toggle_visibility,
        on_show_pet_status,
        on_show_answerbook,
        on_show_weather,
        on_open_settings,
        on_exit,
    ) -> None:
        self.pet_window.pet_clicked.connect(on_pet_clicked)
        self.pet_window.drag_started.connect(on_drag_started)
        self.pet_window.drag_finished.connect(on_drag_finished)
        self.pet_window.quick_action_requested.connect(on_quick_action)

        self.settings_window.config_changed.connect(on_config_changed)
        self.settings_window.pause_reminders_requested.connect(on_pause_reminders)
        self.settings_window.resume_reminders_requested.connect(on_resume_reminders)
        self.settings_window.reset_position_requested.connect(on_reset_position)

        self.pet_status_panel.action_requested.connect(on_pet_status_action)

        self.tray_menu.toggle_visibility_requested.connect(on_toggle_visibility)
        self.tray_menu.show_pet_status_requested.connect(on_show_pet_status)
        self.tray_menu.answerbook_requested.connect(on_show_answerbook)
        self.tray_menu.show_weather_requested.connect(on_show_weather)
        self.tray_menu.pause_reminders_requested.connect(on_pause_reminders)
        self.tray_menu.open_settings_requested.connect(on_open_settings)
        self.tray_menu.exit_requested.connect(on_exit)

    def show_main_ui(self) -> None:
        self.pet_window.show()
        self.tray_menu.show()

    def show_message(self, message: DialogMessage) -> None:
        self.pet_window.show_dialog(message)

    def sync_config(self, config) -> None:
        self.settings_window.sync_from_config(config)

    def update_pet_status(self, pet_status) -> None:
        self.pet_window.update_pet_status(pet_status)
        self.pet_status_panel.update_status(pet_status)

    def update_emotion(self, emotion: EmotionState) -> None:
        self.pet_window.set_emotion_state(emotion)

    def show_settings(self) -> None:
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def show_pet_status_panel(self) -> None:
        self.pet_status_panel.show()
        self.pet_status_panel.raise_()
        self.pet_status_panel.activateWindow()

    def toggle_visibility(self) -> None:
        if self.pet_window.isVisible():
            self.pet_window.hide()
            self.pet_window.hide_dialog()
            return
        self.pet_window.show()
        self.pet_window.raise_()
        self.pet_window.activateWindow()

    def restore_window_position(self, position: WindowPosition) -> WindowPosition:
        screen = self.app.primaryScreen().availableGeometry()
        max_x = max(screen.left(), screen.right() - self.pet_window.width())
        max_y = max(screen.top(), screen.bottom() - self.pet_window.height())
        x = min(max(position.x, screen.left()), max_x)
        y = min(max(position.y, screen.top()), max_y)
        self.pet_window.move(x, y)
        return WindowPosition(x=x, y=y)

    def current_window_position(self) -> WindowPosition:
        pos = self.pet_window.pos()
        return WindowPosition(x=pos.x(), y=pos.y())

    def reset_position(self) -> WindowPosition:
        screen = self.app.primaryScreen().availableGeometry()
        x = max(screen.left(), screen.right() - self.pet_window.width() - 80)
        y = max(screen.top(), screen.bottom() - self.pet_window.height() - 80)
        self.pet_window.move(x, y)
        return WindowPosition(x=x, y=y)

    def move_to_random_position(self) -> WindowPosition:
        screen = self.app.primaryScreen().availableGeometry()
        max_x = max(screen.left(), screen.right() - self.pet_window.width())
        max_y = max(screen.top(), screen.bottom() - self.pet_window.height())
        x = random.randint(screen.left(), max_x)
        y = random.randint(screen.top(), max_y)
        self.pet_window.move(x, y)
        return WindowPosition(x=x, y=y)

    def shutdown(self) -> None:
        self.tray_menu.hide()
        self.settings_window.hide()
        self.pet_status_panel.hide()
        self.pet_window.hide_dialog()
        self.pet_window.close_for_exit()
