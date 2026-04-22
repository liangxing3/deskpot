from __future__ import annotations

import copy
import logging
import threading

import developer_config
from PySide6.QtCore import QObject, QPoint, QRect, QThread, QThreadPool, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import QApplication

from app.app_metadata import APP_DISPLAY_NAME, APP_VERSION, display_version
from app.logic.animation_selector import AnimationManager, AnimationSelector, AnimationTransition, PetAnimationKey
from app.logic.pet_actions import apply_manual_action, derive_emotion, update_pet_name
from app.logic.reminders import ReminderEngine
from app.logic.scheduler import AppScheduler
from app.logic.startup_greetings import (
    STARTUP_GREETING_DELAY_MS,
    STARTUP_GREETING_TTL_MS,
    get_startup_greeting,
)
from app.logic.weather_monitor import (
    compare_weather_snapshots,
    prune_weather_alert_cooldowns,
    record_weather_change,
    should_emit_weather_change,
    update_weather_alert_state_snapshot,
    weather_context_key,
)
from app.signal_bus import get_bus
from data.config_manager import ConfigManager
from data.models import AppConfig, EmotionState, PetVitals, WeatherSnapshot, WindowPosition
from data.pet_models import PetStatus
from data.pet_repository import PetRepository
from data.runtime_state_manager import RuntimeStateManager
from services.answerbook_service import AnswerBookService
from services.cache_service import CacheService
from services.update_service import UpdateCheckResult, UpdateService
from services.weather_service import DeveloperConfiguredWeatherService, IpCityResolver, format_weather_summary
from ui.about_dialog import AboutDialog
from ui.answer_book_dialog_v2 import AnswerBookDialogV2
from ui.pet_window import PetWindow
from ui.settings_window import SettingsWindow
from ui.status_window import StatusWindow
from ui.theme import menu_font_size_for_bubble
from ui.tray_menu import TrayMenu
from ui.weather_dialog import WeatherDialog
from ui.weather_settings_dialog import WeatherSettingsDialog
from utils.async_runner import submit_task
from utils.autostart import disable_autostart, resolve_autostart_command, set_autostart
from utils.font_loader import configure_application_font
from utils.paths import default_gif_path, project_root
from utils.time_utils import now_local


def _emotion_label_clean(emotion: EmotionState) -> str:
    mapping = {
        EmotionState.NORMAL: "待机中",
        EmotionState.WORKING: "工作中",
        EmotionState.HUNGRY: "有点饿了",
        EmotionState.TIRED: "有点累了",
        EmotionState.DIRTY: "想清洁一下",
        EmotionState.LOW_ENERGY: "精力偏低",
        EmotionState.LOW_HAPPINESS: "心情一般",
        EmotionState.DRAINED: "状态透支",
        EmotionState.BORED: "有点无聊",
    }
    return mapping.get(emotion, "待机中")


def _status_label_clean(status: PetStatus, emotion: EmotionState) -> str:
    if getattr(status, "is_resting", False):
        return "休息中"
    return _emotion_label_clean(emotion)


class AppController(QObject):
    bubble_requested = Signal(str, int, int)
    surface_message_requested = Signal(str, int)
    tray_message_requested = Signal(str, str)

    def __init__(self, *, app: QApplication, logger: logging.Logger) -> None:
        super().__init__(app)
        self.app = app
        self.logger = logger
        self.config_manager = ConfigManager(logger)
        self.pet_repository = PetRepository(logger)
        self.runtime_state_manager = RuntimeStateManager(logger)
        self.cache_service = CacheService(logger)
        self.answerbook_service = AnswerBookService(logger=logger, cache_service=self.cache_service)
        self.update_service = UpdateService(logger=logger)
        self.ip_city_resolver = IpCityResolver(cache_service=self.cache_service, logger=logger)
        self.weather_service = DeveloperConfiguredWeatherService(
            cache_service=self.cache_service,
            city_resolver=_ConfiguredCityResolver(self, self.ip_city_resolver),
            logger=logger,
        )
        self.bus = get_bus()
        self.animation_selector = AnimationSelector()
        self.animation_manager = AnimationManager(self.animation_selector)

        self.config = AppConfig.default()
        self.status = PetStatus.default()
        self.vitals = PetVitals.default()
        self.weather_snapshot: WeatherSnapshot | None = None
        self.window: PetWindow | None = None
        self.status_window: StatusWindow | None = None
        self.settings_window: SettingsWindow | None = None
        self.weather_settings_dialog: WeatherSettingsDialog | None = None
        self.weather_dialog: WeatherDialog | None = None
        self.answer_book_dialog: AnswerBookDialogV2 | None = None
        self.about_dialog: AboutDialog | None = None
        self.tray_menu: TrayMenu | None = None

        self._weather_request_in_flight = False
        self._update_check_in_flight = False
        self.thread_pool = QThreadPool.globalInstance()
        self._animation_state_timer = QTimer(self.app)
        self._animation_state_timer.setSingleShot(True)
        self._animation_state_timer.timeout.connect(self._handle_animation_timeout)
        self._startup_greeting_timer = QTimer(self.app)
        self._startup_greeting_timer.setSingleShot(True)
        self._startup_greeting_timer.timeout.connect(self._show_startup_greeting)
        self._startup_heartbeat_timer = QTimer(self.app)
        self._startup_heartbeat_timer.setInterval(1000)
        self._startup_heartbeat_timer.timeout.connect(self._log_ui_heartbeat)
        self._scheduler: AppScheduler | None = None
        self._last_active_dialog = None
        self._startup_greeting_waiting_for_appear = False
        self._startup_greeting_shown = False
        self.bubble_requested.connect(self._show_bubble_on_main, Qt.QueuedConnection)
        self.surface_message_requested.connect(self._surface_message_on_main, Qt.QueuedConnection)
        self.tray_message_requested.connect(self._show_tray_message_on_main, Qt.QueuedConnection)

    def start(self) -> None:
        self._startup_log("start() entered")
        configure_application_font(self.app, self.logger)
        self._startup_log("application font configured")
        self.app.setQuitOnLastWindowClosed(False)
        self.app.aboutToQuit.connect(self._flush_all)
        self._startup_log("quit behavior configured")

        self.config = self.config_manager.load()
        self._startup_log("config loaded")
        self.config_manager.watch_user_config()
        self._startup_log("config watcher attached")
        self.status = self.pet_repository.load()
        self._startup_log("pet status loaded")
        self.vitals = self.runtime_state_manager.load()
        self._startup_log("runtime state loaded")

        self._startup_log("animation bootstrap starting")
        startup_transition = self.animation_manager.bootstrap(self.status, current_time=now_local())
        self._startup_log("animation bootstrap finished")
        gif_path = startup_transition.path or default_gif_path()
        if gif_path is None:
            raise FileNotFoundError("No startup GIF found under assets/GIF.")

        self.logger.info("Starting clean project with GIF: %s", gif_path)
        self.window = PetWindow(
            gif_path=gif_path,
            menu_font_size=menu_font_size_for_bubble(self.config.ui_font_size_px),
            bubble_font_size=self.config.ui_font_size_px,
        )
        self._startup_log("pet window created")
        self.tray_menu = TrayMenu(self.window)
        self._startup_log("tray created")
        self._startup_log("dialogs remain lazy-created at startup")

        self._startup_log("_connect_signals starting")
        self._connect_signals()
        self._startup_log("_connect_signals finished")
        self._sync_all_views(refresh_animation=False)
        self._startup_log("_sync_all_views finished")
        self.window.restore_position(self.config.window_position)
        self._startup_log("window position restored")
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        self._startup_log("main window shown and activated")
        self._apply_transition(startup_transition, apply_path=False)
        self._startup_log("startup animation transition applied")
        self._arm_startup_greeting(startup_transition)
        self._startup_log("startup greeting scheduling armed")
        self.tray_menu.show()
        self._startup_log("tray icon shown")

        self._scheduler = AppScheduler(
            engine=ReminderEngine(),
            config_getter=lambda: self.config,
            status_getter=lambda: self.status,
            vitals_getter=lambda: self.vitals,
            weather_getter=lambda: self.weather_snapshot,
            parent=self.app,
        )
        self._startup_log("scheduler created")
        self._startup_log("initial weather refresh dispatch starting")
        if self.config.weather_enabled and self.config.weather_background_monitor_enabled:
            self._mark_weather_monitor_checked(now_local())
            self._refresh_weather(force_refresh=True, surface_on_complete=False, monitor_mode="seed")
        elif self.config.weather_enabled:
            self._refresh_weather(force_refresh=False, surface_on_complete=False)
        else:
            self._startup_log("initial weather refresh skipped (weather disabled)")
        self._startup_log("initial weather refresh dispatch returned")
        self._scheduler.events_ready.connect(self._handle_scheduler_events)
        self._startup_log("scheduler signals connected")
        self._scheduler.start()
        self._startup_log("scheduler started")
        self._startup_heartbeat_timer.start()
        self._startup_log("UI heartbeat timer started")
        QTimer.singleShot(500, self._preload_common_gifs)
        self._startup_log("GIF preload scheduled")
        self._startup_log("start() returning")

    def toggle_main_window(self) -> None:
        if self.window is None:
            return
        if self.window.isVisible():
            self.window.hide()
            return
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def activate_main_window(self) -> None:
        if self.window is None:
            return
        if not self.window.isVisible():
            self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def show_status_window(self) -> None:
        self._show_dialog(self._ensure_status_window(), key="status_window")
        self._sync_window_states()

    def show_settings_window(self) -> None:
        self._show_dialog(self._ensure_settings_window(), key="settings_window")
        self._sync_window_states()

    def show_weather_settings_dialog(self) -> None:
        self._show_dialog(self._ensure_weather_settings_dialog(), key="weather_settings_dialog")
        self._sync_window_states()

    def show_weather_dialog(self) -> None:
        dialog = self._ensure_weather_dialog()
        self._show_dialog(dialog, key="weather_dialog")
        self._sync_window_states()
        self._refresh_weather(force_refresh=False, surface_on_complete=False)

    def show_about_dialog(self) -> None:
        dialog = self._ensure_about_dialog()
        self._show_dialog(dialog, key="about_dialog")
        self._sync_window_states()

    def show_answer_book_dialog(self) -> None:
        self.logger.info("[answerbook] show request received")
        dialog = self._ensure_answer_book_dialog()
        self.logger.info(
            "[answerbook] dialog instance ready visible=%s pos=%s frame=%s",
            dialog.isVisible(),
            dialog.pos(),
            dialog.frameGeometry(),
        )
        self._show_dialog(dialog, key="answer_book_dialog")
        dialog.focus_input()
        self.logger.info(
            "[answerbook] final visible=%s pos=%s frame=%s",
            dialog.isVisible(),
            dialog.pos(),
            dialog.frameGeometry(),
        )
        self._sync_window_states()

    def quit(self) -> None:
        if self._scheduler is not None:
            self._scheduler.stop()
        self._flush_all()
        if self.tray_menu is not None:
            self.tray_menu.hide()
        for dialog in (
            self.answer_book_dialog,
            self.weather_dialog,
            self.weather_settings_dialog,
            self.settings_window,
            self.status_window,
            self.about_dialog,
        ):
            if dialog is not None:
                dialog.prepare_for_exit()
                dialog.close()
        if self.window is not None:
            self.window.prepare_for_exit()
            self.window.close()
        self.app.quit()

    def _connect_signals(self) -> None:
        assert self.window is not None
        assert self.tray_menu is not None

        self.window.weather_requested.connect(lambda: self._handle_function_menu_action("weather"))
        self.window.answerbook_requested.connect(lambda: self._handle_function_menu_action("answerbook"))
        self.window.settings_requested.connect(lambda: self._handle_function_menu_action("settings"))
        self.window.status_requested.connect(lambda: self._handle_function_menu_action("status"))
        self.window.pet_clicked.connect(self._handle_pet_clicked)
        self.window.window_moved.connect(self._handle_window_delta)
        self.window.manual_action_requested.connect(self._handle_interaction_action)
        self.window.drag_finished.connect(self._save_window_position)
        self.window.hidden_to_tray.connect(self._on_window_hidden_to_tray)
        self.window.interacted.connect(self._note_activity)
        self.tray_menu.toggle_visibility_requested.connect(self.toggle_main_window)
        self.tray_menu.activate_requested.connect(self.activate_main_window)
        self.tray_menu.show_status_requested.connect(lambda: self._handle_function_menu_action("status"))
        self.tray_menu.show_weather_requested.connect(lambda: self._handle_function_menu_action("weather"))
        self.tray_menu.show_answerbook_requested.connect(lambda: self._handle_function_menu_action("answerbook"))
        self.tray_menu.open_settings_requested.connect(lambda: self._handle_function_menu_action("settings"))
        self.tray_menu.check_update_requested.connect(self.check_for_updates)
        self.tray_menu.show_about_requested.connect(self.show_about_dialog)
        self.tray_menu.exit_requested.connect(self.quit)

        self.bus.bubble_show.connect(self._handle_bus_bubble_show, Qt.QueuedConnection)
        self.bus.weather_updated.connect(self._handle_bus_weather_updated, Qt.QueuedConnection)
        self.bus.weather_error.connect(self._handle_bus_weather_error, Qt.QueuedConnection)
        self.bus.pet_state_changed.connect(self._handle_bus_pet_state_changed, Qt.QueuedConnection)
        self.bus.theme_changed.connect(self._sync_all_views, Qt.QueuedConnection)
        self.bus.app_quit_request.connect(self.quit, Qt.QueuedConnection)

    def _thread_debug_label(self) -> str:
        current_qt = QThread.currentThread()
        app_qt = self.app.thread()
        return (
            f"py_thread={threading.get_ident()} "
            f"qt_current=0x{id(current_qt):x} "
            f"qt_main=0x{id(app_qt):x} "
            f"is_main={current_qt is app_qt}"
        )

    def _is_main_thread(self) -> bool:
        return QThread.currentThread() is self.app.thread()

    def _startup_log(self, message: str) -> None:
        self.logger.info("[startup] %s | %s", message, self._thread_debug_label())

    @Slot()
    def _log_ui_heartbeat(self) -> None:
        self.logger.info("[heartbeat] event loop alive | %s", self._thread_debug_label())

    def _wire_dialog(self, dialog, *, key: str) -> None:
        dialog.visibility_changed.connect(
            lambda visible, current_dialog=dialog: self._handle_dialog_visibility(current_dialog, visible)
        )
        dialog.drag_finished.connect(
            lambda position, current_key=key: self._save_dialog_position(current_key, position)
        )

    def _ensure_status_window(self) -> StatusWindow:
        assert self.window is not None
        if self.status_window is None:
            self.status_window = StatusWindow(None)
            self.status_window.action_requested.connect(self._handle_manual_action)
            self._wire_dialog(self.status_window, key="status_window")
        self.status_window.update_status(self.status)
        self.status_window.set_pet_preview(self.window.current_frame_pixmap())
        return self.status_window

    def _ensure_settings_window(self) -> SettingsWindow:
        assert self.window is not None
        if self.settings_window is None:
            self.settings_window = SettingsWindow(None)
            self.settings_window.config_changed.connect(self._apply_general_settings)
            self.settings_window.pet_name_changed.connect(self._update_pet_name)
            self.settings_window.open_weather_settings_requested.connect(self.show_weather_settings_dialog)
            self.settings_window.check_update_requested.connect(self.check_for_updates)
            self.settings_window.about_requested.connect(self.show_about_dialog)
            self._wire_dialog(self.settings_window, key="settings_window")
        self.settings_window.sync_from_config(self.config, self.status.pet_name)
        return self.settings_window

    def _ensure_weather_settings_dialog(self) -> WeatherSettingsDialog:
        assert self.window is not None
        if self.weather_settings_dialog is None:
            self.weather_settings_dialog = WeatherSettingsDialog(None)
            self.weather_settings_dialog.config_changed.connect(self._apply_weather_settings)
            self._wire_dialog(self.weather_settings_dialog, key="weather_settings_dialog")
        self.weather_settings_dialog.sync_from_config(self.config)
        return self.weather_settings_dialog

    def _ensure_weather_dialog(self) -> WeatherDialog:
        assert self.window is not None
        if self.weather_dialog is None:
            self.weather_dialog = WeatherDialog(None)
            self.weather_dialog.refresh_requested.connect(
                lambda: self._refresh_weather(force_refresh=True, surface_on_complete=False)
            )
            self.weather_dialog.open_settings_requested.connect(self.show_weather_settings_dialog)
            self._wire_dialog(self.weather_dialog, key="weather_dialog")
        self.weather_dialog.set_temperature_unit(self.config.weather_temperature_unit)
        if self.weather_snapshot is not None:
            self.weather_dialog.update_snapshot(self.weather_snapshot)
        return self.weather_dialog

    def _ensure_answer_book_dialog(self) -> AnswerBookDialogV2:
        assert self.window is not None
        if self.answer_book_dialog is None:
            self.answer_book_dialog = AnswerBookDialogV2(None)
            self.answer_book_dialog.submit_requested.connect(self._submit_answerbook)
            self._wire_dialog(self.answer_book_dialog, key="answer_book_dialog")
        return self.answer_book_dialog

    def _ensure_about_dialog(self) -> AboutDialog:
        assert self.window is not None
        if self.about_dialog is None:
            self.about_dialog = AboutDialog(None)
            self.about_dialog.check_update_requested.connect(self.check_for_updates)
            self._wire_dialog(self.about_dialog, key="about_dialog")
        self.about_dialog.refresh_static_content()
        return self.about_dialog

    def _sync_all_views(self, refresh_animation: bool = True) -> None:
        assert self.window is not None
        assert self.tray_menu is not None

        self._sync_pet_identity()
        self.window.set_menu_font_size(menu_font_size_for_bubble(self.config.ui_font_size_px))
        if self.status_window is not None:
            self.status_window.update_status(self.status)
            self.status_window.set_pet_preview(self.window.current_frame_pixmap())
        if self.settings_window is not None:
            self.settings_window.sync_from_config(self.config, self.status.pet_name)
        if self.weather_settings_dialog is not None:
            self.weather_settings_dialog.sync_from_config(self.config)
        if self.weather_dialog is not None:
            self.weather_dialog.set_temperature_unit(self.config.weather_temperature_unit)
            if self.weather_snapshot is not None:
                self.weather_dialog.update_snapshot(self.weather_snapshot)
        if self.about_dialog is not None:
            self.about_dialog.refresh_static_content()
        self.tray_menu.set_menu_font_size(menu_font_size_for_bubble(self.config.ui_font_size_px))
        if refresh_animation:
            self._refresh_base_animation(current_time=now_local())
        self._sync_window_states()

    def _sync_pet_identity(self) -> None:
        if self.window is None:
            return
        emotion = derive_emotion(self.status)
        self.window.update_identity(
            pet_name=self.status.pet_name,
            emotion_text=_status_label_clean(self.status, emotion),
        )

    def _sync_window_states(self) -> None:
        if self.window is None or self.tray_menu is None:
            return
        weather_open = bool(self.weather_dialog and self.weather_dialog.isVisible())
        answerbook_open = bool(self.answer_book_dialog and self.answer_book_dialog.isVisible())
        settings_open = bool(self.settings_window and self.settings_window.isVisible())
        status_open = bool(self.status_window and self.status_window.isVisible())
        self.window.set_window_states(
            weather_open=weather_open,
            answerbook_open=answerbook_open,
            settings_open=settings_open,
        )
        self.tray_menu.set_window_states(
            weather_open=weather_open,
            answerbook_open=answerbook_open,
            status_open=status_open,
            settings_open=settings_open,
        )

    def _show_dialog(self, dialog, *, key: str) -> None:
        if key == "answer_book_dialog":
            self.logger.info(
                "[answerbook] pre-show visible=%s pos=%s frame=%s",
                dialog.isVisible(),
                dialog.pos(),
                dialog.frameGeometry(),
            )
        if not dialog.isVisible():
            self._place_dialog(dialog, key=key)
        if hasattr(dialog, "showNormal"):
            dialog.showNormal()
        dialog.show()
        if key == "answer_book_dialog":
            dialog.setWindowOpacity(1.0)
        self._ensure_dialog_visible_on_screen(dialog, key=key)
        self._raise_dialog(dialog)
        self._ensure_dialog_visible_on_screen(dialog, key=key)
        if key == "answer_book_dialog":
            screen_name = self._screen_name_for_rect(dialog.frameGeometry())
            self.logger.info(
                "[answerbook] post-show visible=%s pos=%s frame=%s screen=%s opacity=%s hidden=%s minimized=%s "
                "active=%s isWindow=%s flags=%s parent=%s size=%s rect=%s childrenRect=%s",
                dialog.isVisible(),
                dialog.pos(),
                dialog.frameGeometry(),
                screen_name,
                dialog.windowOpacity(),
                dialog.isHidden(),
                dialog.isMinimized(),
                dialog.isActiveWindow(),
                dialog.isWindow(),
                int(dialog.windowFlags()),
                dialog.parentWidget(),
                dialog.size(),
                dialog.rect(),
                dialog.childrenRect(),
            )

    def _ensure_dialog_visible_on_screen(self, dialog, *, key: str) -> None:
        frame = dialog.frameGeometry()
        if self._is_rect_visible_on_any_screen(frame):
            return
        fallback_position = self._position_dialog_near_pet(dialog, key=key)
        if key == "answer_book_dialog":
            self.logger.info(
                "[answerbook] frame outside visible screens, fallback to %s",
                fallback_position,
            )
        dialog.restore_position(fallback_position)
        self._save_dialog_position(key, fallback_position)

    def _place_dialog(self, dialog, *, key: str) -> None:
        saved_position = self.config.dialog_positions.get(key)
        if saved_position is None or saved_position.first_shown:
            position = self._position_dialog_near_pet(dialog, key=key)
            position.first_shown = False
            dialog.restore_position(position)
            self.config.dialog_positions[key] = copy.deepcopy(position)
            QTimer.singleShot(0, lambda: self.config_manager.save(self.config))
            if key == "answer_book_dialog":
                self.logger.info("[answerbook] using default visible position %s", position)
            return
        saved_rect = self._dialog_rect_for_position(dialog, saved_position)
        if not self._is_rect_visible_on_any_screen(saved_rect):
            fallback = self._position_dialog_near_pet(dialog, key=key)
            dialog.restore_position(fallback)
            self._save_dialog_position(key, fallback)
            if key == "answer_book_dialog":
                self.logger.info(
                    "[answerbook] saved position %s is off-screen, fallback to %s",
                    saved_position,
                    fallback,
                )
            return
        clamped = self._clamp_dialog_position(dialog, saved_position)
        dialog.restore_position(clamped)
        if key == "answer_book_dialog":
            self.logger.info("[answerbook] restored saved visible position %s", clamped)

    def _default_dialog_position(self, dialog, *, key: str) -> WindowPosition:
        assert self.window is not None
        anchor = self.window.frameGeometry()
        screen = self.window.screen()
        available = screen.availableGeometry() if screen is not None else anchor.adjusted(-9999, -9999, 9999, 9999)
        pet_w = anchor.width()
        dialog_w = max(dialog.width(), dialog.sizeHint().width())
        dialog_h = max(dialog.height(), dialog.sizeHint().height())
        margin = 12
        raw_positions = {
            "status_window": QPoint(anchor.left() + pet_w + 12, anchor.top()),
            "settings_window": QPoint(anchor.left() + pet_w + 12, anchor.top() + 80),
            "weather_dialog": QPoint(anchor.left(), anchor.top() - dialog_h - 12),
            "weather_settings_dialog": QPoint(anchor.left() + pet_w + 12, anchor.top() + 160),
            "about_dialog": QPoint(anchor.left() + pet_w + 12, anchor.top() + 240),
            "answer_book_dialog": QPoint(anchor.left() - dialog_w - 12, anchor.top()),
        }
        pos = raw_positions.get(key, QPoint(anchor.left() + pet_w + 12, anchor.top() + 24))
        if key in {"status_window", "settings_window", "weather_settings_dialog", "about_dialog"} and pos.x() + dialog_w > available.right() - margin:
            pos.setX(anchor.left() - dialog_w - 12)
        if key == "answer_book_dialog" and pos.x() < available.left() + margin:
            pos.setX(anchor.left() + pet_w + 12)
        if key == "weather_dialog" and pos.y() < available.top() + margin:
            pos.setY(anchor.bottom() + 12)
        position = WindowPosition(x=int(pos.x()), y=int(pos.y()), first_shown=False)
        return self._clamp_dialog_position(dialog, position)

    def _position_dialog_near_pet(self, dialog, *, key: str) -> WindowPosition:
        return self._default_dialog_position(dialog, key=key)

    def _dialog_rect_for_position(self, dialog, position: WindowPosition) -> QRect:
        dialog_w = max(dialog.width(), dialog.sizeHint().width())
        dialog_h = max(dialog.height(), dialog.sizeHint().height())
        return QRect(int(position.x), int(position.y), int(dialog_w), int(dialog_h))

    def _available_screen_geometries(self) -> list[QRect]:
        geometries = [screen.availableGeometry() for screen in QApplication.screens()]
        if geometries:
            return geometries
        primary = self.app.primaryScreen()
        return [primary.availableGeometry()] if primary is not None else []

    def _is_rect_visible_on_any_screen(self, rect: QRect) -> bool:
        min_visible_width = min(rect.width(), 160)
        min_visible_height = min(rect.height(), 120)
        for available in self._available_screen_geometries():
            intersection = rect.intersected(available)
            if intersection.width() >= min_visible_width and intersection.height() >= min_visible_height:
                return True
        return False

    def _best_visible_geometry_for_rect(self, rect: QRect) -> QRect | None:
        best_geometry: QRect | None = None
        best_area = -1
        for available in self._available_screen_geometries():
            if available.contains(rect.center()):
                return available
            intersection = rect.intersected(available)
            area = max(0, intersection.width()) * max(0, intersection.height())
            if area > best_area:
                best_area = area
                best_geometry = available
        return best_geometry

    def _screen_name_for_rect(self, rect: QRect) -> str:
        for screen in QApplication.screens():
            available = screen.availableGeometry()
            if available.contains(rect.center()) or rect.intersects(available):
                return screen.name() or "unknown"
        primary = self.app.primaryScreen()
        return (primary.name() if primary is not None else "none") or "unknown"

    def _clamp_dialog_position(self, dialog, position: WindowPosition) -> WindowPosition:
        target_rect = self._dialog_rect_for_position(dialog, position)
        available = self._best_visible_geometry_for_rect(target_rect)
        if available is None:
            return copy.deepcopy(position)
        dialog_w = max(dialog.width(), dialog.sizeHint().width())
        dialog_h = max(dialog.height(), dialog.sizeHint().height())
        margin = 12
        x = max(available.left() + margin, min(int(position.x), available.right() - dialog_w - margin))
        y = max(available.top() + margin, min(int(position.y), available.bottom() - dialog_h - margin))
        return WindowPosition(x=x, y=y, first_shown=bool(position.first_shown))

    def _save_dialog_position(self, key: str, position: WindowPosition) -> None:
        saved = copy.deepcopy(position)
        saved.first_shown = False
        self.config.dialog_positions[key] = saved
        QTimer.singleShot(0, lambda: self.config_manager.save(self.config))

    def _handle_window_delta(self, delta_x: int, delta_y: int) -> None:
        _ = (delta_x, delta_y)

    def _handle_dialog_visibility(self, dialog, visible: bool) -> None:
        if visible:
            self._last_active_dialog = dialog
            self._raise_dialog(dialog)
        elif self._last_active_dialog is dialog:
            self._last_active_dialog = None
        if not visible:
            for dialog_key, candidate in (
                ("status_window", self.status_window),
                ("settings_window", self.settings_window),
                ("weather_settings_dialog", self.weather_settings_dialog),
                ("weather_dialog", self.weather_dialog),
                ("answer_book_dialog", self.answer_book_dialog),
                ("about_dialog", self.about_dialog),
            ):
                if candidate is dialog:
                    self._save_dialog_position(dialog_key, dialog.current_position())
                    break
        self._sync_window_states()

    def _attached_dialogs(self):
        for dialog in (
            self.status_window,
            self.settings_window,
            self.weather_settings_dialog,
            self.weather_dialog,
            self.answer_book_dialog,
            self.about_dialog,
        ):
            if dialog is not None:
                yield dialog

    def _raise_dialog(self, dialog) -> None:
        self._last_active_dialog = dialog
        dialog.raise_()
        dialog.activateWindow()

    def _raise_active_dialogs(self) -> None:
        visible_dialogs = [dialog for dialog in self._attached_dialogs() if dialog.isVisible()]
        if not visible_dialogs:
            return
        preferred = self._last_active_dialog if self._last_active_dialog in visible_dialogs else visible_dialogs[-1]
        for dialog in visible_dialogs:
            if dialog is not preferred:
                dialog.raise_()
        preferred.raise_()
        preferred.activateWindow()

    @Slot(str, int)
    def _handle_bus_bubble_show(self, text: str, ttl_ms: int) -> None:
        self.logger.debug("[thread] _handle_bus_bubble_show %s", self._thread_debug_label())
        self._show_bubble(text, ttl_ms=ttl_ms, priority=0)

    @Slot(object)
    def _handle_bus_weather_updated(self, snapshot: WeatherSnapshot | None) -> None:
        self.logger.debug("[thread] _handle_bus_weather_updated %s", self._thread_debug_label())
        self.weather_snapshot = snapshot
        if self.weather_dialog is not None:
            self.weather_dialog.update_snapshot(snapshot)

    @Slot(str)
    def _handle_bus_weather_error(self, message: str) -> None:
        self.logger.debug("[thread] _handle_bus_weather_error %s", self._thread_debug_label())
        if self.weather_dialog is not None:
            self.weather_dialog.set_error(message)

    @Slot()
    def _handle_bus_pet_state_changed(self) -> None:
        self.logger.debug("[thread] _handle_bus_pet_state_changed %s", self._thread_debug_label())
        self._sync_pet_identity()
        if self.status_window is not None:
            self.status_window.update_status(self.status)
            if self.window is not None:
                self.status_window.set_pet_preview(self.window.current_frame_pixmap())

    def _apply_transition(self, transition, *, apply_path: bool = True) -> None:
        if self.window is None or transition is None:
            return
        if apply_path:
            target_path = transition.path or default_gif_path()
            if target_path is not None and not self.window.apply_animation(target_path):
                fallback = default_gif_path()
                if fallback is not None:
                    self.window.apply_animation(fallback)
        self._sync_pet_identity()
        if self.status_window is not None:
            self.status_window.set_pet_preview(self.window.current_frame_pixmap())
        if transition.duration_ms:
            self._animation_state_timer.start(int(transition.duration_ms))
        else:
            self._animation_state_timer.stop()

    def _arm_startup_greeting(self, startup_transition: AnimationTransition | None) -> None:
        self._startup_greeting_timer.stop()
        self._startup_greeting_shown = False
        if (
            startup_transition is not None
            and startup_transition.key == PetAnimationKey.APPEAR
            and startup_transition.duration_ms
        ):
            self._startup_greeting_waiting_for_appear = True
            self.logger.info(
                "Startup greeting armed after APPEAR animation delay=%sms",
                STARTUP_GREETING_DELAY_MS,
            )
            return
        self._schedule_startup_greeting(delay_ms=STARTUP_GREETING_DELAY_MS)

    def _schedule_startup_greeting(self, *, delay_ms: int) -> None:
        if self._startup_greeting_shown:
            return
        self._startup_greeting_waiting_for_appear = False
        self._startup_greeting_timer.stop()
        self._startup_greeting_timer.start(max(0, int(delay_ms)))
        self.logger.info("Startup greeting scheduled in %sms", max(0, int(delay_ms)))

    @Slot()
    def _show_startup_greeting(self) -> None:
        if self._startup_greeting_shown or self.window is None or not self.window.isVisible():
            return
        self._startup_greeting_shown = True
        greeting = get_startup_greeting()
        self.logger.info("Showing startup greeting bubble: %s", greeting)
        self._show_bubble(greeting, ttl_ms=STARTUP_GREETING_TTL_MS, priority=1)

    def _handle_animation_timeout(self) -> None:
        should_show_startup_greeting = (
            self._startup_greeting_waiting_for_appear
            and not self._startup_greeting_shown
            and self.animation_manager.current_animation == PetAnimationKey.APPEAR
        )
        transition = self.animation_manager.on_animation_finished()
        if transition is None:
            self._animation_state_timer.stop()
            if should_show_startup_greeting:
                self._schedule_startup_greeting(delay_ms=STARTUP_GREETING_DELAY_MS)
            return
        self._apply_transition(transition)
        if should_show_startup_greeting:
            self._schedule_startup_greeting(delay_ms=STARTUP_GREETING_DELAY_MS)

    def _refresh_base_animation(self, *, current_time=None) -> None:
        transition = self.animation_manager.refresh_base_animation(self.status, current_time=current_time or now_local())
        if transition is not None:
            self._apply_transition(transition)
            return
        self._sync_pet_identity()
        if self.status_window is not None and self.window is not None:
            self.status_window.set_pet_preview(self.window.current_frame_pixmap())

    def _handle_pet_clicked(self) -> None:
        self._note_activity()
        key = self.animation_selector.select_click_animation(self.status)
        transition = self.animation_manager.play_event_animation(key)
        if transition is not None:
            self._apply_transition(transition)

    def _handle_function_menu_action(self, action_name: str) -> None:
        """Function menu actions only open UI and never touch animation state."""
        if action_name == "weather":
            self.show_weather_dialog()
            return
        if action_name == "answerbook":
            self.logger.info("[answerbook] function menu action dispatched")
            self.show_answer_book_dialog()
            return
        if action_name == "settings":
            self.show_settings_window()
            return
        if action_name == "status":
            self.show_status_window()
            return

    def _preload_common_gifs(self) -> None:
        keys = [
            PetAnimationKey.IDLE,
            PetAnimationKey.HAPPY,
            PetAnimationKey.APPEAR,
            PetAnimationKey.FEED,
            PetAnimationKey.EXERCISE,
        ]
        paths = []
        for key in keys:
            path = self.animation_selector.resolve_animation_path(key)
            if path is not None:
                paths.append(path)
        if not paths:
            return

        def _warm_files():
            warmed: list[str] = []
            for path in paths:
                try:
                    path.read_bytes()
                    warmed.append(str(path))
                except OSError:
                    continue
            return warmed

        submit_task(
            self.thread_pool,
            _warm_files,
            on_success=lambda _: None,
            on_error=lambda exc: self.logger.debug("GIF preload failed: %s", exc),
        )

    def _handle_interaction_action(self, action_id: str) -> None:
        now = now_local()
        self.status, feedback = apply_manual_action(self.status, action_id, current_time=now)
        self.vitals.last_manual_action = action_id
        self.vitals.last_updated_at = now
        self.pet_repository.save(self.status)
        self.runtime_state_manager.save(self.vitals)
        self._note_activity(now)
        self.bus.pet_state_changed.emit()
        self._show_bubble(feedback.bubble_text, ttl_ms=feedback.duration_ms, priority=1)

        base_transition = self.animation_manager.refresh_base_animation(self.status, current_time=now)
        event_key = {
            "feed": PetAnimationKey.FEED,
            "clean": PetAnimationKey.CLEAN,
            "play": PetAnimationKey.EXERCISE,
        }.get(action_id)

        if event_key is not None:
            transition = self.animation_manager.play_event_animation(event_key)
            if transition is not None:
                self._apply_transition(transition)
            elif base_transition is not None:
                self._apply_transition(base_transition)
            return

        if base_transition is not None:
            self._apply_transition(base_transition)

    def _handle_manual_action(self, action_id: str) -> None:
        # Compatibility shim for existing dialog/window signal connections.
        self._handle_interaction_action(action_id)

    def _save_window_position(self, position: WindowPosition) -> None:
        self.config.window_position = copy.deepcopy(position)
        self.config.window_position.first_shown = False
        self.config_manager.save(self.config)

    def _apply_general_settings(self, partial: AppConfig) -> None:
        self.config.auto_start = partial.auto_start
        self.config.drink_remind_interval_minutes = partial.drink_remind_interval_minutes
        self.config.sedentary_remind_interval_minutes = partial.sedentary_remind_interval_minutes
        self.config.hourly_report_enabled = partial.hourly_report_enabled
        self.config.random_dialog_enabled = partial.random_dialog_enabled
        self.config.ui_font_size_px = partial.ui_font_size_px
        self._persist_autostart()
        self.config_manager.save(self.config, immediate=True)
        self._sync_all_views(refresh_animation=False)

    def _apply_weather_settings(self, partial: AppConfig) -> None:
        monitor_context_changed = (
            self.config.weather_city_override != partial.weather_city_override
            or self.config.weather_auto_location != partial.weather_auto_location
            or self.config.weather_background_monitor_enabled != partial.weather_background_monitor_enabled
        )
        self.config.weather_city_override = partial.weather_city_override
        self.config.weather_auto_location = partial.weather_auto_location
        self.config.weather_temperature_unit = partial.weather_temperature_unit
        self.config.weather_bubble_enabled = partial.weather_bubble_enabled
        self.config.weather_broadcast_time = partial.weather_broadcast_time
        self.config.weather_severe_alert_enabled = partial.weather_severe_alert_enabled
        self.config.weather_background_monitor_enabled = partial.weather_background_monitor_enabled
        self.config.weather_change_alert_enabled = partial.weather_change_alert_enabled
        self.config.weather_change_alert_sensitivity = partial.weather_change_alert_sensitivity
        self.config_manager.save(self.config, immediate=True)
        self._sync_all_views(refresh_animation=False)
        if monitor_context_changed and self.config.weather_enabled and self.config.weather_background_monitor_enabled:
            self._mark_weather_monitor_checked(now_local())
            self._refresh_weather(force_refresh=True, surface_on_complete=False, monitor_mode="seed")
            return
        self._refresh_weather(force_refresh=True, surface_on_complete=False)

    def _update_pet_name(self, pet_name: str) -> None:
        cleaned = pet_name.strip()
        if not cleaned:
            return
        self.status = update_pet_name(self.status, cleaned)
        self.pet_repository.save(self.status, immediate=True)
        self.bus.pet_state_changed.emit()
        self._sync_all_views(refresh_animation=False)

    def _submit_answerbook(self, question: str) -> None:
        dialog = self._ensure_answer_book_dialog()
        dialog.set_loading(question)
        submit_task(
            self.thread_pool,
            self.answerbook_service.ask,
            args=(question,),
            on_success=dialog.set_result,
            on_error=lambda exc: dialog.set_error(str(exc)),
        )

    def check_for_updates(self) -> None:
        dialog = self._ensure_about_dialog()
        self._show_dialog(dialog, key="about_dialog")
        if self._update_check_in_flight:
            self._raise_dialog(dialog)
            return
        self._update_check_in_flight = True
        dialog.set_checking_update()
        submit_task(
            self.thread_pool,
            self.update_service.check_for_updates,
            on_success=self._handle_update_check_success,
            on_error=self._handle_update_check_error,
        )

    def _handle_update_check_success(self, result: UpdateCheckResult) -> None:
        self._update_check_in_flight = False
        dialog = self._ensure_about_dialog()
        dialog.set_update_result(result)
        if result.source == "unpublished":
            self._show_tray_message_on_main(
                "暂未发布更新",
                "当前仓库还没有正式发布版本，暂时无法比较远端更新。",
            )
            return
        if result.update_available:
            self._show_tray_message_on_main(
                "发现新版本",
                f"{APP_DISPLAY_NAME} {display_version(result.latest_version)} 可用，当前为 {display_version(APP_VERSION)}。",
            )
            return
        self._show_tray_message_on_main(
            "已是最新版本",
            f"{APP_DISPLAY_NAME} 当前版本 {display_version(APP_VERSION)} 已是最新版本。",
        )

    def _handle_update_check_error(self, exc: Exception) -> None:
        self._update_check_in_flight = False
        dialog = self._ensure_about_dialog()
        dialog.set_update_error("暂时无法连接远端发布页，请稍后重试。")
        self.logger.warning("Update check failed: %s", exc)
        self._show_tray_message_on_main("检查更新失败", "暂时无法连接远端发布页，请稍后重试。")

    def _mark_weather_monitor_checked(self, when=None) -> None:
        self.vitals.weather_alert_state.last_checked_at = when or now_local()
        self.runtime_state_manager.save(self.vitals)

    def _handle_weather_monitor_snapshot(self, snapshot: WeatherSnapshot, *, compare_changes: bool) -> None:
        if snapshot.source != "remote":
            self.logger.info(
                "Weather monitor skipped snapshot persistence because source=%s",
                snapshot.source,
            )
            return
        state = self.vitals.weather_alert_state
        current_time = snapshot.captured_at or snapshot.retrieved_at or now_local()
        previous_snapshot = state.last_snapshot
        context_changed = (
            previous_snapshot is not None
            and weather_context_key(previous_snapshot) != weather_context_key(snapshot)
        )

        prune_weather_alert_cooldowns(state, current_time=current_time)
        if compare_changes and previous_snapshot is not None and not context_changed:
            result = compare_weather_snapshots(
                previous_snapshot,
                snapshot,
                sensitivity=self.config.weather_change_alert_sensitivity,
            )
            if (
                self.config.weather_background_monitor_enabled
                and self.config.weather_change_alert_enabled
                and should_emit_weather_change(result, state, current_time=current_time)
            ):
                self.logger.info(
                    "Weather monitor alert emitted signature=%s types=%s",
                    result.signature,
                    ",".join(result.change_types),
                )
                record_weather_change(state, result, current_time=current_time)
                self._show_bubble(result.message or "天气有变化了，出门前记得留意一下。", ttl_ms=result.ttl_ms, priority=1)
            elif result.significant:
                self.logger.info(
                    "Weather monitor alert suppressed by cooldown signature=%s types=%s",
                    result.signature,
                    ",".join(result.change_types),
                )

        if context_changed:
            self.logger.info(
                "Weather monitor context changed from %s to %s; reset previous snapshot comparison",
                weather_context_key(previous_snapshot),
                weather_context_key(snapshot),
            )
        update_weather_alert_state_snapshot(state, snapshot, reset_context=context_changed)
        self.runtime_state_manager.save(self.vitals)

    def _refresh_weather(
        self,
        *,
        force_refresh: bool,
        surface_on_complete: bool,
        monitor_mode: str = "none",
    ) -> None:
        if self._weather_request_in_flight:
            return
        if self.weather_dialog is not None:
            self.weather_dialog.set_loading()
        self._weather_request_in_flight = True

        def _on_success(snapshot: WeatherSnapshot | None) -> None:
            self.logger.debug("[thread] _refresh_weather.on_success %s", self._thread_debug_label())
            self._weather_request_in_flight = False
            self.bus.weather_updated.emit(snapshot)
            if snapshot is not None and monitor_mode != "none":
                self._handle_weather_monitor_snapshot(
                    snapshot,
                    compare_changes=monitor_mode == "compare",
                )
            if surface_on_complete:
                self._surface_message(format_weather_summary(snapshot), ttl_ms=5600)
            self.cache_service.flush()

        def _on_error(exc: Exception) -> None:
            self.logger.debug("[thread] _refresh_weather.on_error %s", self._thread_debug_label())
            self._weather_request_in_flight = False
            self.logger.warning("Weather refresh failed: %s", exc)
            message = "天气暂时不可用，已回退到缓存或本地兜底。"
            self.bus.weather_error.emit(message)
            if self.weather_dialog is not None:
                self.weather_dialog.set_error(message)
            if surface_on_complete:
                self._surface_message("天气获取失败。", ttl_ms=5200)

        submit_task(
            self.thread_pool,
            self.weather_service.get_weather,
            kwargs={"force_refresh": force_refresh},
            on_success=_on_success,
            on_error=_on_error,
        )

    def _handle_scheduler_events(self, events) -> None:
        should_monitor_weather = any(event.kind == "weather_monitor_tick" for event in events)
        should_surface_weather = any(event.kind == "weather_broadcast" for event in events)
        for event in events:
            if event.kind in {"weather_monitor_tick", "weather_broadcast"}:
                continue
            else:
                self._surface_message(event.text, ttl_ms=event.ttl_ms)
        if should_monitor_weather:
            self._refresh_weather(
                force_refresh=True,
                surface_on_complete=should_surface_weather,
                monitor_mode="compare",
            )
        elif should_surface_weather:
            self._refresh_weather(force_refresh=False, surface_on_complete=True)
        self.runtime_state_manager.save(self.vitals)

    def _surface_message(self, text: str, *, ttl_ms: int = 4000) -> None:
        if not self._is_main_thread():
            self.logger.warning(
                "[thread] _surface_message called off main thread; rerouting: %s",
                self._thread_debug_label(),
            )
            self.surface_message_requested.emit(text, int(ttl_ms))
            return
        self._surface_message_on_main(text, int(ttl_ms))

    def _show_bubble(self, text: str, *, ttl_ms: int, priority: int = 0) -> None:
        if not self._is_main_thread():
            self.logger.error(
                "[thread] _show_bubble called off main thread; rerouting before timer start: %s",
                self._thread_debug_label(),
            )
            self.bubble_requested.emit(text, int(ttl_ms), int(priority))
            return
        self._show_bubble_on_main(text, int(ttl_ms), int(priority))

    def _note_activity(self, when=None) -> None:
        current = when or now_local()
        self.vitals.last_updated_at = current
        if self._scheduler is not None:
            self._scheduler.note_activity(current)
        self.runtime_state_manager.save(self.vitals)

    def _on_window_hidden_to_tray(self) -> None:
        if self.tray_menu is not None:
            self._show_tray_message_on_main("桌宠已隐藏", "桌宠仍在运行，可以从托盘菜单恢复。")

    @Slot(str, int)
    def _surface_message_on_main(self, text: str, ttl_ms: int) -> None:
        self.logger.debug("[thread] _surface_message_on_main %s", self._thread_debug_label())
        if self.window is not None and self.window.isVisible():
            self.bus.bubble_show.emit(text, int(ttl_ms))
        elif self.tray_menu is not None:
            self._show_tray_message_on_main("桌宠提醒", text)

    @Slot(str, int, int)
    def _show_bubble_on_main(self, text: str, ttl_ms: int, priority: int) -> None:
        self.logger.debug("[thread] _show_bubble_on_main %s", self._thread_debug_label())
        if self.window is None:
            return
        self.window.show_bubble(text, int(ttl_ms), priority=int(priority))
        QTimer.singleShot(0, self._raise_active_dialogs)

    @Slot(str, str)
    def _show_tray_message_on_main(self, title: str, message: str) -> None:
        self.logger.debug("[thread] _show_tray_message_on_main %s", self._thread_debug_label())
        if self.tray_menu is not None:
            self.tray_menu.show_message(title, message)

    def _persist_autostart(self) -> None:
        try:
            if self.config.auto_start:
                command = resolve_autostart_command(project_root() / "main.py")
                set_autostart(command)
            else:
                disable_autostart()
        except Exception as exc:
            self.logger.warning("Failed to update auto-start setting: %s", exc)

    def _flush_all(self) -> None:
        try:
            self.config_manager.save(self.config, immediate=True)
        except Exception:
            self.logger.exception("Failed to save config before flush.")
        try:
            self.pet_repository.save(self.status, immediate=True)
        except Exception:
            self.logger.exception("Failed to save pet status before flush.")
        try:
            self.runtime_state_manager.save(self.vitals, immediate=True)
        except Exception:
            self.logger.exception("Failed to save runtime state before flush.")
        try:
            self.config_manager.flush()
        except Exception:
            self.logger.exception("Failed to flush config store.")
        try:
            self.pet_repository.flush()
        except Exception:
            self.logger.exception("Failed to flush pet repository.")
        try:
            self.runtime_state_manager.flush()
        except Exception:
            self.logger.exception("Failed to flush runtime state.")
        try:
            self.cache_service.flush()
        except Exception:
            self.logger.exception("Failed to flush cache service.")


class _ConfiguredCityResolver:
    def __init__(self, controller: AppController, auto_resolver: IpCityResolver) -> None:
        self.controller = controller
        self.auto_resolver = auto_resolver

    def resolve_city(self, force_refresh: bool = False) -> str | None:
        config = self.controller.config
        manual_city = config.weather_city_override.strip()

        if config.weather_auto_location:
            resolved_city = self.auto_resolver.resolve_city(force_refresh=force_refresh)
            if resolved_city:
                return resolved_city

        if manual_city:
            return manual_city
        if developer_config.WEATHER_DEFAULT_CITY:
            return developer_config.WEATHER_DEFAULT_CITY
        return None
