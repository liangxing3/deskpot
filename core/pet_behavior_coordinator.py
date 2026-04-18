from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

from PySide6.QtCore import QObject, QThreadPool, Signal
from PySide6.QtWidgets import QInputDialog

from core.state_manager import STATE_PRIORITIES
from data.manual_actions import MANUAL_ACTION_SPECS
from data.models import AnswerBookResult, DialogMessage, PetState, UiMessage
from utils.async_runner import submit_task
from utils.time_utils import hour_key, now_local


class PetBehaviorCoordinator(QObject):
    pet_status_updated = Signal(object)
    emotion_changed = Signal(object)

    PET_HINT_COOLDOWN_SECONDS = 60 * 60

    def __init__(
        self,
        *,
        logger: logging.Logger,
        thread_pool: QThreadPool,
        state_manager,
        scheduler,
        interaction_manager,
        reminder_manager,
        time_reporter,
        growth_manager,
        dialog_service,
        answerbook_service,
        notification_center,
        get_config: Callable[[], object],
        runtime_state,
        ui_parent_getter: Callable[[], object],
        has_weather_cache: Callable[[], bool],
        on_weather_requested: Callable[[str], None],
        on_open_settings: Callable[[], None],
        on_open_pet_status: Callable[[], None],
        on_pause_reminders: Callable[[], None],
        on_reset_position: Callable[[], None],
        on_exit: Callable[[], None],
        on_move_randomly: Callable[[], None],
        save_runtime_state: Callable[[], None],
        save_pet_status: Callable[[], None],
    ) -> None:
        super().__init__()
        self.logger = logger
        self.thread_pool = thread_pool
        self.state_manager = state_manager
        self.scheduler = scheduler
        self.interaction_manager = interaction_manager
        self.reminder_manager = reminder_manager
        self.time_reporter = time_reporter
        self.growth_manager = growth_manager
        self.dialog_service = dialog_service
        self.answerbook_service = answerbook_service
        self.notification_center = notification_center
        self.get_config = get_config
        self.runtime_state = runtime_state
        self.ui_parent_getter = ui_parent_getter
        self.has_weather_cache = has_weather_cache
        self.on_weather_requested = on_weather_requested
        self.on_open_settings = on_open_settings
        self.on_open_pet_status = on_open_pet_status
        self.on_pause_reminders = on_pause_reminders
        self.on_reset_position = on_reset_position
        self.on_exit = on_exit
        self.on_move_randomly = on_move_randomly
        self.save_runtime_state = save_runtime_state
        self.save_pet_status = save_pet_status

        self._last_emotion_state = None
        self._last_pet_hint_at: datetime | None = None
        self._dialog_in_flight = False
        self._answerbook_in_flight = False

    def bootstrap(self) -> None:
        self.growth_manager.bootstrap(now_local())
        self._emit_pet_status_and_emotion(force=True)

    def on_pet_clicked(self) -> None:
        current = now_local()
        config = self.get_config()
        if not self.interaction_manager.can_click(config, current):
            return

        self.interaction_manager.register_click(current)
        self.scheduler.schedule_next_random_dialog()
        growth_result = self.growth_manager.apply_click_interaction(now=current)
        self.state_manager.request_state(PetState.INTERACTING, ttl_ms=3_500)
        self._handle_growth_feedback(growth_result, current=current)

        if growth_result.leveled_up:
            self.state_manager.request_state(
                PetState.GROWING,
                ttl_ms=5_000,
                payload={"variant": "growing"},
            )
            message = self.dialog_service.fetch_message("pet_growth", prefer_remote=False)
            self._publish_dialog_message(message, priority=70, dedupe_key="pet:growth")
            return

        action = self.interaction_manager.next_click_action(self.has_weather_cache())
        if action.value == "time":
            self._publish_ui_message(
                UiMessage(
                    text=f"现在是 {current.strftime('%H:%M')}。",
                    category="time_report",
                    priority=35,
                    ttl_ms=3000,
                    cooldown_key="click:time",
                    cooldown_ms=2000,
                )
            )
            return
        if action.value == "weather":
            self.on_weather_requested("manual_click")
            return
        self.request_dialog_message("click", prefer_remote=True, priority=30)

    def handle_quick_action(self, action: str) -> None:
        if action in MANUAL_ACTION_SPECS:
            self.perform_manual_action(action)
            return

        handlers = {
            "status": self.on_open_pet_status,
            "answerbook": self.open_answerbook_prompt,
            "weather": lambda: self.on_weather_requested("tray_manual"),
            "settings": self.on_open_settings,
            "pause": self.on_pause_reminders,
            "reset": self.on_reset_position,
            "exit": self.on_exit,
        }
        handler = handlers.get(action)
        if handler:
            handler()

    def perform_manual_action(self, action_id: str) -> None:
        if self.state_manager.current_state == PetState.DRAGGING:
            return

        spec = MANUAL_ACTION_SPECS[action_id]
        current = now_local()
        growth_result = self.growth_manager.apply_manual_action(action_id, now=current)
        self.runtime_state.last_manual_action = action_id
        self.interaction_manager.register_interaction(current)
        self.scheduler.schedule_next_random_dialog()

        if growth_result.leveled_up:
            self.state_manager.request_state(
                PetState.GROWING,
                ttl_ms=5_000,
                payload={"variant": "growing"},
            )
        else:
            self.state_manager.request_state(
                PetState.MANUAL_ACTION,
                ttl_ms=spec.duration_ms,
                payload={"variant": spec.variant},
            )

        if action_id == "appear":
            self.on_move_randomly()

        self._handle_growth_feedback(growth_result, current=current)
        if growth_result.leveled_up:
            message = self.dialog_service.fetch_message("pet_growth", prefer_remote=False)
            self._publish_dialog_message(message, priority=70, dedupe_key="pet:growth")
            return

        self._publish_ui_message(
            UiMessage(
                text=spec.bubble_text,
                category="click",
                priority=40,
                ttl_ms=max(4_000, spec.duration_ms),
                cooldown_key=f"manual:{action_id}",
                cooldown_ms=2_000,
                dedupe_key=f"manual:{action_id}",
                dedupe_ms=4_000,
            )
        )

    def on_activity_tick(self) -> bool:
        current = now_local()
        reminder_state = self.reminder_manager.due_reminder(
            self.get_config(),
            last_interaction_time=self.interaction_manager.last_interaction_time,
            now=current,
        )
        if reminder_state and self.state_manager.can_enter(reminder_state):
            self.trigger_reminder(reminder_state)
            return True

        self._maybe_emit_pet_status_hint(current)
        return False

    def on_clock_tick(self) -> None:
        current = now_local()
        if not self.get_config().hourly_report_enabled:
            return
        if self.time_reporter.should_report(current):
            if self.state_manager.current_priority() >= STATE_PRIORITIES[PetState.REMINDING_DRINK]:
                self.time_reporter.schedule_pending(current)
                self.scheduler.delay_hourly_report()
            else:
                self.emit_hourly_report(current)

    def on_delayed_hourly_due(self) -> None:
        if not self.time_reporter.can_emit_pending():
            return
        if self.state_manager.current_priority() >= STATE_PRIORITIES[PetState.REMINDING_DRINK]:
            return
        self.emit_hourly_report(now_local())

    def on_growth_tick(self) -> None:
        current = now_local()
        growth_result = self.growth_manager.tick(now=current)
        if growth_result.changed:
            self._handle_growth_feedback(growth_result, current=current)

    def on_random_animation_due(self) -> None:
        if self.state_manager.current_state == PetState.IDLE:
            self.state_manager.request_state(PetState.RANDOM_ANIMATING, ttl_ms=4_000)

    def on_random_dialog_due(self) -> None:
        current = now_local()
        config = self.get_config()
        if not self.interaction_manager.can_emit_random_dialog(
            config,
            state_priority=self.state_manager.current_priority(),
            reminder_recent=self.reminder_manager.reminder_recent(current),
        ):
            return
        self.interaction_manager.mark_random_dialog_shown(current)
        self.state_manager.request_state(PetState.RANDOM_ANIMATING, ttl_ms=4_000)
        self.request_dialog_message("random_chat", prefer_remote=True, priority=20)

    def request_dialog_message(self, category: str, *, prefer_remote: bool, priority: int) -> None:
        if self._dialog_in_flight:
            return
        self._dialog_in_flight = True
        submit_task(
            self.thread_pool,
            self.dialog_service.fetch_message,
            args=(category,),
            kwargs={"prefer_remote": prefer_remote},
            on_success=lambda message: self._on_dialog_message_ready(message, priority),
            on_error=self._on_dialog_message_failed,
        )

    def open_answerbook_prompt(self) -> None:
        if self._answerbook_in_flight:
            self._publish_ui_message(
                UiMessage(
                    text="答案之书正在翻页，稍等一下。",
                    category="answerbook",
                    priority=60,
                    ttl_ms=2500,
                    cooldown_key="answerbook:loading",
                    cooldown_ms=2500,
                )
            )
            return

        question, ok = QInputDialog.getText(
            self.ui_parent_getter(),
            "答案之书",
            "你想问什么？",
        )
        if not ok:
            return

        normalized_question = question.strip()
        if not normalized_question:
            self._publish_ui_message(
                UiMessage(
                    text="问题不能为空。",
                    category="answerbook",
                    priority=60,
                    ttl_ms=2500,
                )
            )
            return

        current = now_local()
        self.interaction_manager.register_interaction(current)
        self.scheduler.schedule_next_random_dialog()
        self.state_manager.request_state(PetState.INTERACTING, ttl_ms=6_000)
        self._answerbook_in_flight = True
        self._publish_ui_message(
            UiMessage(
                text="让我翻翻答案之书……",
                category="answerbook",
                priority=60,
                ttl_ms=2500,
                cooldown_key="answerbook:request",
                cooldown_ms=2000,
            )
        )
        submit_task(
            self.thread_pool,
            self.answerbook_service.ask,
            args=(normalized_question,),
            on_success=self._on_answerbook_ready,
            on_error=self._on_answerbook_failed,
        )

    def emit_pet_status_summary(self) -> None:
        category = self.growth_manager.summary_category(
            now=now_local(),
            last_interaction_time=self.interaction_manager.last_interaction_time,
        )
        message = self.dialog_service.fetch_message(category, prefer_remote=False)
        self._publish_dialog_message(message, priority=30, dedupe_key=f"pet:summary:{category}")

    def trigger_reminder(self, reminder_state: PetState) -> None:
        self.reminder_manager.mark_reminded(reminder_state)
        self.state_manager.request_state(reminder_state, ttl_ms=5_000)
        category = (
            "reminder_drink"
            if reminder_state == PetState.REMINDING_DRINK
            else "reminder_sedentary"
        )
        message = self.dialog_service.fetch_message(category, prefer_remote=False)
        self._publish_dialog_message(
            message,
            priority=90,
            dedupe_key=f"reminder:{category}",
            cooldown_key="reminder:any",
            cooldown_ms=5 * 60 * 1000,
        )

    def emit_hourly_report(self, current: datetime) -> None:
        self.time_reporter.mark_reported(current)
        self.runtime_state.last_hourly_report_hour = hour_key(current)
        self.save_runtime_state()
        self.state_manager.request_state(PetState.TIME_REPORTING, ttl_ms=4_500)
        self._publish_ui_message(
            UiMessage(
                text=f"现在是 {current.strftime('%H:00')}。",
                category="time_report",
                priority=70,
                ttl_ms=5000,
                cooldown_key="hourly:report",
                cooldown_ms=60_000,
                dedupe_key=f"hourly:{hour_key(current)}",
                dedupe_ms=60_000,
            )
        )

    def _on_dialog_message_ready(self, message: DialogMessage, priority: int) -> None:
        self._dialog_in_flight = False
        self._publish_dialog_message(
            message,
            priority=priority,
            dedupe_key=f"dialog:{message.category}:{message.message_id or message.text}",
            cooldown_key=f"dialog:{message.category}",
            cooldown_ms=2_000,
        )

    def _on_dialog_message_failed(self, exc: Exception) -> None:
        self._dialog_in_flight = False
        self.logger.warning("Dialog worker failed: %s", exc)

    def _on_answerbook_ready(self, result: AnswerBookResult) -> None:
        self._answerbook_in_flight = False
        self.state_manager.request_state(PetState.INTERACTING, ttl_ms=5_000)
        self._publish_ui_message(
            UiMessage(
                text=f"问题：{result.question}\n答案：{result.answer}",
                category="answerbook",
                source=result.source,
                priority=65,
                ttl_ms=6000,
                cooldown_key="answerbook:result",
                cooldown_ms=2000,
            )
        )

    def _on_answerbook_failed(self, exc: Exception) -> None:
        self._answerbook_in_flight = False
        self.logger.warning("Answerbook worker failed: %s", exc)
        self._publish_ui_message(
            UiMessage(
                text="答案之书暂时不可用。",
                category="answerbook",
                priority=60,
                ttl_ms=2500,
            )
        )

    def _emit_pet_status_and_emotion(self, *, force: bool = False) -> None:
        self.save_pet_status()
        self.pet_status_updated.emit(self.growth_manager.snapshot())
        emotion = self.growth_manager.current_emotion(
            now=now_local(),
            last_interaction_time=self.interaction_manager.last_interaction_time,
        )
        if force or emotion != self._last_emotion_state:
            self._last_emotion_state = emotion
            self.emotion_changed.emit(emotion)

    def _handle_growth_feedback(self, growth_result, *, current: datetime) -> None:
        if not growth_result.changed:
            return
        self.runtime_state.last_updated_at = current
        self.save_runtime_state()
        self._emit_pet_status_and_emotion(force=growth_result.leveled_up)
        if growth_result.favorability_increased and not growth_result.leveled_up:
            message = self.dialog_service.fetch_message("pet_favorability_up", prefer_remote=False)
            self._publish_dialog_message(
                message,
                priority=35,
                dedupe_key="pet:favorability",
                cooldown_key="pet:favorability",
                cooldown_ms=30_000,
            )

    def _maybe_emit_pet_status_hint(self, current: datetime) -> None:
        if self.state_manager.current_state != PetState.IDLE:
            return
        if self._last_pet_hint_at and (
            current - self._last_pet_hint_at
        ).total_seconds() < self.PET_HINT_COOLDOWN_SECONDS:
            return
        category = self.growth_manager.summary_category(
            now=current,
            last_interaction_time=self.interaction_manager.last_interaction_time,
        )
        if category == "pet_status_good":
            return
        self._last_pet_hint_at = current
        message = self.dialog_service.fetch_message(category, prefer_remote=False)
        self._publish_dialog_message(
            message,
            priority=25,
            dedupe_key=f"pet:hint:{category}",
            cooldown_key="pet:hint",
            cooldown_ms=self.PET_HINT_COOLDOWN_SECONDS * 1000,
        )

    def _publish_dialog_message(
        self,
        message: DialogMessage,
        *,
        priority: int,
        dedupe_key: str,
        cooldown_key: str | None = None,
        cooldown_ms: int = 0,
    ) -> None:
        self._publish_ui_message(
            UiMessage(
                text=message.text,
                category=message.category,
                source=message.source,
                priority=priority,
                ttl_ms=max(1000, message.expires_in_seconds * 1000),
                cooldown_key=cooldown_key,
                cooldown_ms=cooldown_ms,
                dedupe_key=dedupe_key,
                dedupe_ms=max(3000, message.expires_in_seconds * 1000),
                drop_if_state_at_least=STATE_PRIORITIES[PetState.REMINDING_DRINK]
                if priority < 90
                else None,
            )
        )

    def _publish_ui_message(self, message: UiMessage) -> None:
        self.notification_center.publish(message)
