from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QThreadPool, QTimer
from PySide6.QtWidgets import QApplication

from core.daypart_weather_reporter import DaypartWeatherReporter
from core.growth_manager import GrowthManager
from core.interaction_manager import InteractionManager
from core.notification_center import NotificationCenter
from core.pet_behavior_coordinator import PetBehaviorCoordinator
from core.reminder_manager import ReminderManager
from core.scheduler import Scheduler
from core.state_manager import StateManager
from core.time_reporter import TimeReporter
from core.ui_coordinator import UiCoordinator
from core.weather_coordinator import WeatherCoordinator
from data.asset_manifest import AssetManifest
from data.config_manager import ConfigManager
from data.models import PetState, UiMessage, WindowPosition
from data.pet_repository import PetRepository
from data.runtime_state_manager import RuntimeStateManager
from services.answerbook_service import AnswerBookService
from services.cache_service import CacheService
from services.dialog_service import DialogService
from services.local_dialog_provider import LocalDialogProvider
from services.uapi_dialog_provider import UapiDialogProvider
from services.weather_care_advisor import WeatherCareAdvisor
from services.weather_service import DeveloperConfiguredWeatherService, IpCityResolver
from ui.pet_status_panel import PetStatusPanel
from ui.pet_window import PetWindow
from ui.settings_panel import SettingsWindow
from ui.tray_controls import TrayMenu
from utils.autostart import (
    disable_autostart,
    is_autostart_enabled,
    resolve_autostart_command,
    set_autostart,
)
from utils.paths import project_root
from utils.time_utils import now_local, plus_hours


class AppController(QObject):
    """Composition root for the desktop pet runtime."""

    def __init__(self, app: QApplication, logger: logging.Logger) -> None:
        super().__init__(app)
        self.app = app
        self.logger = logger
        self.thread_pool = QThreadPool.globalInstance()
        self._is_exiting = False

        self.config_manager = ConfigManager(logger)
        self.runtime_state_manager = RuntimeStateManager(logger)
        self.pet_repository = PetRepository(logger)
        self.cache_service = CacheService(logger)

        self.config = self.config_manager.load()
        self.runtime_state = self.runtime_state_manager.load()
        self.pet_status = self.pet_repository.load()

        self._apply_autostart()
        self.config.auto_start = is_autostart_enabled()

        self.asset_manifest = AssetManifest()
        self.state_manager = StateManager()
        self.scheduler = Scheduler()
        self.interaction_manager = InteractionManager()
        self.reminder_manager = ReminderManager()
        self.time_reporter = TimeReporter()
        self.time_reporter.last_hourly_report_hour = self.runtime_state.last_hourly_report_hour
        self.daypart_weather_reporter = DaypartWeatherReporter(self.runtime_state)
        self.weather_care_advisor = WeatherCareAdvisor()
        self.growth_manager = GrowthManager(self.pet_status)

        self.city_resolver = IpCityResolver(cache_service=self.cache_service, logger=logger)
        self.weather_service = DeveloperConfiguredWeatherService(
            cache_service=self.cache_service,
            city_resolver=self.city_resolver,
            logger=logger,
        )
        self.dialog_service = DialogService(
            logger=logger,
            cache_service=self.cache_service,
            remote_provider=UapiDialogProvider(logger),
            local_provider=LocalDialogProvider(),
        )
        self.answerbook_service = AnswerBookService(
            logger=logger,
            cache_service=self.cache_service,
        )

        self.pet_window = PetWindow(self.asset_manifest)
        self.settings_window = SettingsWindow()
        self.pet_status_panel = PetStatusPanel()
        self.tray_menu = TrayMenu()

        self.ui = UiCoordinator(
            app=app,
            pet_window=self.pet_window,
            settings_window=self.settings_window,
            pet_status_panel=self.pet_status_panel,
            tray_menu=self.tray_menu,
        )
        self.notification_center = NotificationCenter(
            logger=logger,
            state_manager=self.state_manager,
        )
        self.behavior = PetBehaviorCoordinator(
            logger=logger,
            thread_pool=self.thread_pool,
            state_manager=self.state_manager,
            scheduler=self.scheduler,
            interaction_manager=self.interaction_manager,
            reminder_manager=self.reminder_manager,
            time_reporter=self.time_reporter,
            growth_manager=self.growth_manager,
            dialog_service=self.dialog_service,
            answerbook_service=self.answerbook_service,
            notification_center=self.notification_center,
            get_config=lambda: self.config,
            runtime_state=self.runtime_state,
            ui_parent_getter=lambda: self.pet_window,
            has_weather_cache=self.weather_service.has_cached_weather,
            on_weather_requested=self.show_weather_summary,
            on_open_settings=self.open_settings,
            on_open_pet_status=self.open_pet_status_panel,
            on_pause_reminders=self.pause_reminders_for_one_hour,
            on_reset_position=self.reset_position,
            on_exit=self.exit_application,
            on_move_randomly=self.move_to_random_position,
            save_runtime_state=self.save_runtime_state,
            save_pet_status=self.save_pet_status,
        )
        self.weather = WeatherCoordinator(
            logger=logger,
            thread_pool=self.thread_pool,
            state_manager=self.state_manager,
            scheduler=self.scheduler,
            interaction_manager=self.interaction_manager,
            daypart_weather_reporter=self.daypart_weather_reporter,
            weather_care_advisor=self.weather_care_advisor,
            weather_service=self.weather_service,
            dialog_service=self.dialog_service,
            notification_center=self.notification_center,
            get_config=lambda: self.config,
            runtime_state=self.runtime_state,
            save_runtime_state=self.save_runtime_state,
        )

        self._connect_signals()
        corrected_position = self.ui.restore_window_position(self.config.window_position)
        if corrected_position != self.config.window_position:
            self.config.window_position = corrected_position
            self.save_config()
        self.ui.sync_config(self.config)
        self.behavior.bootstrap()
        self.ui.show_main_ui()

        self.scheduler.start()
        self.weather.schedule_next_refresh(from_time=now_local())
        QTimer.singleShot(1500, self.weather.startup_auto_weather)

    def _connect_signals(self) -> None:
        self.ui.bind(
            on_pet_clicked=self.behavior.on_pet_clicked,
            on_drag_started=self.on_drag_started,
            on_drag_finished=self.on_drag_finished,
            on_quick_action=self.behavior.handle_quick_action,
            on_config_changed=self.apply_config,
            on_pause_reminders=self.pause_reminders_for_one_hour,
            on_resume_reminders=self.resume_reminders,
            on_reset_position=self.reset_position,
            on_pet_status_action=self.behavior.perform_manual_action,
            on_toggle_visibility=self.toggle_visibility,
            on_show_pet_status=self.open_pet_status_panel,
            on_show_answerbook=self.behavior.open_answerbook_prompt,
            on_show_weather=lambda: self.show_weather_summary("tray_manual"),
            on_open_settings=self.open_settings,
            on_exit=self.exit_application,
        )

        self.notification_center.message_ready.connect(self.ui.show_message)
        self.behavior.pet_status_updated.connect(self.ui.update_pet_status)
        self.behavior.emotion_changed.connect(self.ui.update_emotion)

        self.state_manager.state_changed.connect(self._on_state_changed)
        self.scheduler.activity_tick.connect(self._on_activity_tick)
        self.scheduler.clock_tick.connect(self._on_clock_tick)
        self.scheduler.growth_tick.connect(self.behavior.on_growth_tick)
        self.scheduler.random_animation_due.connect(self.behavior.on_random_animation_due)
        self.scheduler.random_dialog_due.connect(self.behavior.on_random_dialog_due)
        self.scheduler.delayed_hourly_due.connect(self.behavior.on_delayed_hourly_due)
        self.scheduler.startup_weather_due.connect(self.weather.on_startup_weather_due)
        self.scheduler.weather_refresh_due.connect(self.weather.on_weather_refresh_due)

    def _on_state_changed(self, state: PetState, payload: dict) -> None:
        self.pet_window.apply_state(state, payload)

    def _on_activity_tick(self) -> None:
        self.behavior.on_activity_tick()

    def _on_clock_tick(self) -> None:
        self.behavior.on_clock_tick()
        self.weather.on_clock_tick()

    def on_drag_started(self) -> None:
        self.state_manager.request_state(PetState.DRAGGING)

    def on_drag_finished(self, point) -> None:
        self.config.window_position = WindowPosition(x=point.x(), y=point.y())
        self.save_config()
        self.state_manager.clear_state(PetState.DRAGGING)

    def show_weather_summary(self, source: str = "tray_manual") -> None:
        self.weather.request_announcement(source, manual=True)

    def open_settings(self) -> None:
        self.ui.show_settings()

    def open_pet_status_panel(self) -> None:
        self.ui.show_pet_status_panel()
        self.behavior.emit_pet_status_summary()

    def toggle_visibility(self) -> None:
        self.ui.toggle_visibility()

    def pause_reminders_for_one_hour(self) -> None:
        self.config.reminder_pause_until = plus_hours(1)
        self.save_config()
        self.notification_center.publish(
            UiMessage(
                text="提醒已暂停 1 小时。",
                category="system",
                priority=75,
                ttl_ms=2500,
                cooldown_key="system:pause",
                cooldown_ms=2000,
            )
        )

    def resume_reminders(self) -> None:
        self.config.reminder_pause_until = None
        self.save_config()
        self.notification_center.publish(
            UiMessage(
                text="提醒已恢复。",
                category="system",
                priority=75,
                ttl_ms=2500,
                cooldown_key="system:resume",
                cooldown_ms=2000,
            )
        )

    def reset_position(self) -> None:
        self.config.window_position = self.ui.reset_position()
        self.save_config()

    def move_to_random_position(self) -> None:
        self.config.window_position = self.ui.move_to_random_position()
        self.save_config()

    def apply_config(self, config) -> None:
        config.window_position = self.ui.current_window_position()
        config.reminder_pause_until = self.config.reminder_pause_until
        self.config = config
        self._apply_autostart()
        self.save_config()
        self.weather.schedule_next_refresh(from_time=now_local())

    def save_config(self, *, immediate: bool = False) -> None:
        self.config_manager.save(self.config, immediate=immediate)
        self.ui.sync_config(self.config)

    def save_runtime_state(self, *, immediate: bool = False) -> None:
        self.runtime_state_manager.save(self.runtime_state, immediate=immediate)

    def save_pet_status(self, *, immediate: bool = False) -> None:
        self.pet_repository.save(self.growth_manager.snapshot(), immediate=immediate)

    def exit_application(self) -> None:
        if self._is_exiting:
            return
        self._is_exiting = True
        self.scheduler.stop()
        self.notification_center.clear()
        self.config.window_position = self.ui.current_window_position()
        self._flush_runtime_state()
        self.ui.shutdown()
        self.app.quit()

    def _apply_autostart(self) -> None:
        command = resolve_autostart_command(project_root() / "main.py")
        try:
            if self.config.auto_start:
                set_autostart(command)
            else:
                disable_autostart()
        except Exception as exc:
            self.logger.warning("Failed to update auto-start setting: %s", exc)

    def _flush_runtime_state(self) -> None:
        operations = (
            ("config save", lambda: self.save_config(immediate=True)),
            ("runtime save", lambda: self.save_runtime_state(immediate=True)),
            ("pet status save", lambda: self.save_pet_status(immediate=True)),
            ("cache flush", self.cache_service.flush),
            ("config flush", self.config_manager.flush),
            ("runtime flush", self.runtime_state_manager.flush),
            ("pet status flush", self.pet_repository.flush),
        )
        for label, operation in operations:
            try:
                operation()
            except Exception as exc:  # pragma: no cover - defensive shutdown path.
                self.logger.warning("Failed during %s: %s", label, exc)
