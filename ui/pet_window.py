from __future__ import annotations

import random

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QMovie, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from data.asset_manifest import AssetManifest
from data.manual_actions import MANUAL_ACTION_SPECS
from data.models import AnimationManifestEntry, DialogMessage, EmotionState, PetState
from data.pet_models import PetStatus
from ui.dialog_bubble import DialogBubble
from utils.font_loader import ui_font_stack


class PetWindow(QWidget):
    TARGET_MOVIE_SIZE = QSize(220, 220)

    pet_clicked = Signal()
    pet_double_clicked = Signal()
    drag_started = Signal()
    drag_finished = Signal(object)
    quick_action_requested = Signal(str)

    def __init__(self, asset_manifest: AssetManifest, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.asset_manifest = asset_manifest
        self._allow_close = False
        self._movie: QMovie | None = None
        self._press_global_pos: QPoint | None = None
        self._press_window_pos: QPoint | None = None
        self._dragging = False
        self._current_state = PetState.IDLE
        self._current_payload: dict = {}
        self._current_emotion = EmotionState.NORMAL

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setCursor(Qt.OpenHandCursor)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(6)

        self.animation_shell = QWidget(self)
        self.animation_shell.setAttribute(Qt.WA_TranslucentBackground, True)
        self.animation_shell.setFixedSize(self.TARGET_MOVIE_SIZE.width(), self.TARGET_MOVIE_SIZE.height() + 8)
        self.main_layout.addWidget(self.animation_shell, alignment=Qt.AlignCenter)

        self.animation_backdrop = QWidget(self.animation_shell)
        self.animation_backdrop.setGeometry(8, 10, 204, 204)
        self.animation_backdrop.setStyleSheet(
            """
            QWidget {
                background: rgba(255, 250, 252, 228);
                border: 2px solid rgba(255, 207, 223, 190);
                border-radius: 28px;
            }
            """
        )

        self.animation_label = QLabel(self.animation_shell)
        self.animation_label.setAlignment(Qt.AlignCenter)
        self.animation_label.resize(self.TARGET_MOVIE_SIZE)
        self.animation_label.move(0, 0)
        self.animation_label.setPixmap(self._build_placeholder_pixmap())

        self._idle_anim = QPropertyAnimation(self.animation_label, b"pos", self)
        self._idle_anim.setDuration(2500)
        self._idle_anim.setStartValue(QPoint(0, 0))
        self._idle_anim.setEndValue(QPoint(0, 6))
        self._idle_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._idle_anim.setLoopCount(-1)
        self._idle_anim.start()

        self.status_card = QWidget(self)
        self.status_card.setAttribute(Qt.WA_TranslucentBackground, True)
        self.status_card.setStyleSheet(
            f"""
            QWidget {{
                background: rgba(255, 249, 251, 248);
                border: 1px solid rgba(255, 207, 223, 210);
                border-radius: 14px;
                font-family: {ui_font_stack()};
            }}
            """
        )
        self.status_layout = QVBoxLayout(self.status_card)
        self.status_layout.setContentsMargins(10, 8, 10, 10)
        self.status_layout.setSpacing(6)

        self.stage_label = QLabel("成长阶段：幼年期  亲密度：20/100", self.status_card)
        self.stage_label.setStyleSheet(
            'color: #5A5A5A; font-size: 11px; font-weight: 700; '
            f'font-family: {ui_font_stack()};'
        )
        self.status_layout.addWidget(self.stage_label)

        self.hunger_bar = self._build_status_row("饱腹", "#FFC857")
        self.mood_bar = self._build_status_row("心情", "#FF9A9E")
        self.energy_bar = self._build_status_row("精力", "#A1C4FD")
        self.cleanliness_bar = self._build_status_row("清洁", "#A8E6CF")
        self.main_layout.addWidget(self.status_card)

        self.dialog_bubble = DialogBubble()
        self._build_context_menu()
        self._refresh_animation()

    def apply_state(self, state: PetState, payload: dict | None = None) -> None:
        self._current_state = state
        self._current_payload = payload or {}
        self._refresh_animation()

    def set_emotion_state(self, emotion_state: EmotionState) -> None:
        self._current_emotion = emotion_state
        if self._current_state == PetState.IDLE:
            self._refresh_animation()

    def update_pet_status(self, status: PetStatus) -> None:
        self.stage_label.setText(
            f"成长阶段：{status.growth_stage.label}  亲密度：{status.favorability}/100"
        )
        self.hunger_bar.setValue(status.hunger)
        self.mood_bar.setValue(status.mood)
        self.energy_bar.setValue(status.energy)
        self.cleanliness_bar.setValue(status.cleanliness)
        self.adjustSize()

    def update_vitals(self, vitals) -> None:
        if hasattr(vitals, "happiness"):
            self.mood_bar.setValue(int(vitals.happiness))
        if hasattr(vitals, "energy"):
            self.energy_bar.setValue(int(vitals.energy))

    def show_dialog(self, message: DialogMessage) -> None:
        duration_ms = max(3, message.expires_in_seconds) * 1000
        self.dialog_bubble.show_message(self.frameGeometry(), message.text, duration_ms)

    def hide_dialog(self) -> None:
        self.dialog_bubble.hide_bubble()

    def close_for_exit(self) -> None:
        self._allow_close = True
        self.dialog_bubble.hide_bubble()
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._allow_close:
            super().closeEvent(event)
            return
        event.ignore()
        self.hide()
        self.dialog_bubble.hide_bubble()

    def moveEvent(self, event) -> None:  # noqa: N802
        if self.dialog_bubble.isVisible():
            self.dialog_bubble.show_message(
                self.frameGeometry(),
                self.dialog_bubble.label.text(),
                self.dialog_bubble._hide_timer.remainingTime() or 3000,
            )
        super().moveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()
            return
        if event.button() != Qt.LeftButton:
            return
        self._press_global_pos = event.globalPosition().toPoint()
        self._press_window_pos = self.pos()
        self._dragging = False
        self.setCursor(Qt.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._press_global_pos is None or self._press_window_pos is None:
            return
        delta = event.globalPosition().toPoint() - self._press_global_pos
        if delta.manhattanLength() < QApplication.startDragDistance():
            return
        if not self._dragging:
            self._dragging = True
            self.drag_started.emit()
        self.move(self._press_window_pos + delta)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton:
            return
        if self._dragging:
            self.drag_finished.emit(self.pos())
        else:
            self.pet_clicked.emit()
        self._press_global_pos = None
        self._press_window_pos = None
        self._dragging = False
        self.setCursor(Qt.PointingHandCursor)
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.pet_double_clicked.emit()
            event.accept()

    def enterEvent(self, event) -> None:  # noqa: N802
        self.setCursor(Qt.PointingHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if not self._dragging:
            self.setCursor(Qt.OpenHandCursor)
        super().leaveEvent(event)

    def _refresh_animation(self) -> None:
        entry = self._select_entry(self._current_state, self._current_payload)
        if entry is None:
            self._show_placeholder()
            return
        self._load_animation(entry)

    def _select_entry(self, state: PetState, payload: dict) -> AnimationManifestEntry | None:
        if state != PetState.IDLE:
            variant = payload.get("variant")
            state_candidates = self.asset_manifest.entries_for_state(state, variant=variant)
            if not state_candidates:
                fallbacks = {
                    PetState.DRAGGING: self.asset_manifest.entries_for_emotion(self._current_emotion),
                    PetState.INTERACTING: self.asset_manifest.entries_for_state(PetState.RANDOM_ANIMATING),
                    PetState.MANUAL_ACTION: self.asset_manifest.entries_for_state(PetState.INTERACTING),
                    PetState.GROWING: self.asset_manifest.entries_for_state(PetState.INTERACTING),
                    PetState.TIME_REPORTING: self.asset_manifest.entries_for_state(PetState.RANDOM_ANIMATING),
                    PetState.WEATHER_SHOWING: self.asset_manifest.entries_for_state(PetState.IDLE),
                    PetState.REMINDING_DRINK: self.asset_manifest.entries_for_state(PetState.IDLE),
                    PetState.REMINDING_SEDENTARY: self.asset_manifest.entries_for_state(PetState.IDLE),
                }
                state_candidates = fallbacks.get(state, []) or self.asset_manifest.entries_for_state(
                    PetState.IDLE
                )
        else:
            state_candidates = self.asset_manifest.entries_for_emotion(self._current_emotion)
            if not state_candidates:
                state_candidates = self.asset_manifest.entries_for_emotion(EmotionState.NORMAL)
            if not state_candidates:
                state_candidates = self.asset_manifest.entries_for_state(PetState.IDLE)

        if not state_candidates:
            return None
        return random.choices(
            state_candidates,
            weights=[max(1, item.weight) for item in state_candidates],
            k=1,
        )[0]

    def _load_animation(self, entry: AnimationManifestEntry) -> None:
        asset_path = self.asset_manifest.resolve(entry)
        if not asset_path.exists():
            self._show_placeholder()
            return

        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()

        self._movie = QMovie(str(asset_path))
        self._movie.setCacheMode(QMovie.CacheAll)
        self._movie.setScaledSize(self.TARGET_MOVIE_SIZE)
        self.animation_label.setMovie(self._movie)
        self._movie.start()
        self.animation_label.resize(self.TARGET_MOVIE_SIZE)
        self.adjustSize()

    def _show_placeholder(self) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None
        self.animation_label.setPixmap(self._build_placeholder_pixmap())
        self.animation_label.resize(self.TARGET_MOVIE_SIZE)
        self.adjustSize()

    def _build_placeholder_pixmap(self) -> QPixmap:
        pixmap = QPixmap(self.TARGET_MOVIE_SIZE)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#FFCFDF"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRect(20, 20, 180, 180))
        painter.setPen(QColor("#5A5A5A"))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "PET")
        painter.end()
        return pixmap

    def _build_status_row(self, label: str, color: str) -> QProgressBar:
        row = QWidget(self.status_card)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        caption = QLabel(label, row)
        caption.setStyleSheet(
            f'color: #666666; font-size: 11px; font-family: {ui_font_stack()};'
        )
        caption.setFixedWidth(64)
        bar = QProgressBar(row)
        bar.setRange(0, 100)
        bar.setValue(80)
        bar.setTextVisible(False)
        bar.setFixedHeight(10)
        bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: rgba(255, 240, 245, 220);
                border: 1px solid rgba(255, 228, 225, 220);
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
            """
        )
        layout.addWidget(caption)
        layout.addWidget(bar, 1)
        self.status_layout.addWidget(row)
        return bar

    def _build_context_menu(self) -> None:
        self.context_menu = QMenu(self)
        self.context_menu.setWindowFlags(self.context_menu.windowFlags() | Qt.NoDropShadowWindowHint)
        self.context_menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: rgba(255, 255, 255, 245);
                border: 1px solid #FFCFDF;
                border-radius: 12px;
                padding: 8px;
                font-family: {ui_font_stack(include_emoji=True)};
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 8px;
                color: #5A5A5A;
                font-size: 13px;
                margin: 2px 0px;
            }}
            QMenu::item:selected {{
                background-color: #FFF0F5;
                color: #FF6B9D;
            }}
            QMenu::separator {{
                height: 1px;
                background: #FFE4E1;
                margin: 4px 8px;
            }}
            """
        )

        grouped_actions = (
            (("feed", "🍖"), ("play", "🧶"), ("clean", "🛁"), ("rest", "💤")),
            (
                ("petting", "🐾"),
                ("pat", "🤏"),
                ("exercise", "🏃"),
                ("charge", "🔋"),
                ("baji", "💗"),
                ("feather_ball", "🪀"),
                ("appear", "🎲"),
                ("walkdog", "🦮"),
            ),
        )
        for group_index, action_group in enumerate(grouped_actions):
            if group_index:
                self.context_menu.addSeparator()
            for action_id, prefix in action_group:
                spec = MANUAL_ACTION_SPECS[action_id]
                self.context_menu.addAction(f"{prefix} {spec.label}").triggered.connect(
                    lambda checked=False, current_action_id=action_id: self.quick_action_requested.emit(
                        current_action_id
                    )
                )

        self.context_menu.addSeparator()
        self.context_menu.addAction("🐾 宠物状态").triggered.connect(
            lambda: self.quick_action_requested.emit("status")
        )
        self.context_menu.addAction("📖 答案之书").triggered.connect(
            lambda: self.quick_action_requested.emit("answerbook")
        )
        self.context_menu.addAction("⛅ 立即查看天气").triggered.connect(
            lambda: self.quick_action_requested.emit("weather")
        )
        self.context_menu.addAction("⚙️ 系统设置").triggered.connect(
            lambda: self.quick_action_requested.emit("settings")
        )
        self.context_menu.addAction("⏸️ 暂停提醒 1 小时").triggered.connect(
            lambda: self.quick_action_requested.emit("pause")
        )
        self.context_menu.addAction("🔄 重置位置").triggered.connect(
            lambda: self.quick_action_requested.emit("reset")
        )
        self.context_menu.addSeparator()
        self.context_menu.addAction("❌ 退出程序").triggered.connect(
            lambda: self.quick_action_requested.emit("exit")
        )

    def _show_context_menu(self, global_pos: QPoint) -> None:
        self.context_menu.exec(global_pos)
