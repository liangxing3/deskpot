from __future__ import annotations

import random

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QMovie, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
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
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
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
                background: transparent;
                border: none;
                border-radius: 28px;
            }
            QWidget:hover {
                background: transparent;
                border: none;
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
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 253, 255, 250),
                    stop:1 rgba(255, 249, 251, 250));
                border: 1px solid rgba(255, 207, 223, 220);
                border-radius: 16px;
                font-family: {ui_font_stack()};
            }}
            QWidget:hover {{
                border: 1px solid rgba(255, 180, 200, 240);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 255),
                    stop:1 rgba(255, 251, 253, 255));
            }}
            """
        )
        self.status_layout = QVBoxLayout(self.status_card)
        self.status_layout.setContentsMargins(10, 8, 10, 10)
        self.status_layout.setSpacing(6)

        self.stage_label = QLabel("成长阶段：幼年期  亲密度：20/100", self.status_card)
        self.stage_label.setStyleSheet(
            'color: #FF6B9D; font-size: 13px; font-weight: 700; '
            f'font-family: {ui_font_stack()}; padding: 5px 10px; background: rgba(255, 240, 245, 180); border-radius: 8px;'
        )
        self.status_layout.addWidget(self.stage_label)

        self.hunger_bar = self._build_status_row("饱腹", "#FFC857")
        self.mood_bar = self._build_status_row("心情", "#FF9A9E")
        self.energy_bar = self._build_status_row("精力", "#A1C4FD")
        self.cleanliness_bar = self._build_status_row("清洁", "#A8E6CF")
        self.status_card.hide()
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
        layout.setSpacing(8)

        caption = QLabel(label, row)
        caption.setStyleSheet(
            f'color: #FF6B9D; font-size: 11px; font-weight: 600; font-family: {ui_font_stack()};'
        )
        caption.setFixedWidth(48)
        bar = QProgressBar(row)
        bar.setRange(0, 100)
        bar.setValue(80)
        bar.setTextVisible(False)
        bar.setFixedHeight(12)
        bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: rgba(255, 240, 245, 200);
                border: 1px solid rgba(255, 228, 225, 200);
                border-radius: 6px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color},
                    stop:1 {color}DD);
                border-radius: 5px;
            }}
            """
        )
        layout.addWidget(caption)
        layout.addWidget(bar, 1)
        self.status_layout.addWidget(row)
        return bar

    def _build_context_menu(self) -> None:
        self.context_menu = QDialog(self)
        self.context_menu.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.context_menu.setAttribute(Qt.WA_TranslucentBackground, True)
        self.context_menu.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.context_menu.setStyleSheet(
            f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 255),
                    stop:1 rgba(255, 253, 255, 255));
                border: 1px solid #FFCFDF;
                border-radius: 16px;
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 255),
                    stop:1 rgba(255, 253, 255, 255));
                border: 1px solid #FFCFDF;
                border-radius: 12px;
                color: #5A5A5A;
                font-size: 20px;
                font-weight: 500;
                padding: 16px 20px;
                min-width: 120px;
                min-height: 60px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFF0F5,
                    stop:1 #FFE8EC);
                color: #FF6B9D;
                font-weight: 600;
                border: 2px solid #FFCFDF;
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFE8EC,
                    stop:1 #FFD6E0);
                color: #FF6B9D;
                font-weight: 700;
                padding: 17px 19px;
            }}
            """
        )

        menu_layout = QVBoxLayout(self.context_menu)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(8)

        main_actions = (
            ("pet_interactions", "🐾 宠物互动"),
            ("answerbook", "📖 答案之书"),
            ("weather", "⛅ 天气"),
            ("settings", "⚙️ 系统设置"),
            ("pause", "⏸️ 暂停提醒"),
            ("reset", "🔄 重置位置"),
            ("exit", "❌ 退出程序"),
        )

        for i in range(0, len(main_actions), 2):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)
            row_layout.setContentsMargins(8, 8, 8, 8)
            
            for j in range(2):
                if i + j < len(main_actions):
                    action_id, label = main_actions[i + j]
                    button = QPushButton(label)
                    button.clicked.connect(
                        lambda checked=False, current_action_id=action_id, btn=button: self._on_main_menu_clicked(
                            current_action_id, btn
                        )
                    )
                    row_layout.addWidget(button, 1)
            
            menu_layout.addLayout(row_layout)

        self.context_menu.hide()
        
        self._build_pet_interaction_menu()

    def _build_pet_interaction_menu(self) -> None:
        self.pet_interaction_menu = QDialog(self)
        self.pet_interaction_menu.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.pet_interaction_menu.setAttribute(Qt.WA_TranslucentBackground, True)
        self.pet_interaction_menu.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.pet_interaction_menu.setStyleSheet(
            f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 255),
                    stop:1 rgba(255, 253, 255, 255));
                border: 1px solid #FFCFDF;
                border-radius: 16px;
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 255),
                    stop:1 rgba(255, 253, 255, 255));
                border: 1px solid #FFCFDF;
                border-radius: 12px;
                color: #5A5A5A;
                font-size: 18px;
                font-weight: 500;
                padding: 14px 18px;
                min-width: 100px;
                min-height: 55px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFF0F5,
                    stop:1 #FFE8EC);
                color: #FF6B9D;
                font-weight: 600;
                border: 2px solid #FFCFDF;
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFE8EC,
                    stop:1 #FFD6E0);
                color: #FF6B9D;
                font-weight: 700;
                padding: 15px 17px;
            }}
            """
        )

        menu_layout = QVBoxLayout(self.pet_interaction_menu)
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(0)

        grouped_actions = (
            (("feed", "🍖"), ("play", "🧶"), ("clean", "🛁")),
            (("rest", "💤"), ("petting", "🐾"), ("pat", "🤏")),
            (("exercise", "🏃"), ("charge", "🔋"), ("baji", "💗")),
            (("feather_ball", "🪀"), ("appear", "🎲"), ("walkdog", "🦮")),
        )

        for group_index, action_group in enumerate(grouped_actions):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(8)
            row_layout.setContentsMargins(8, 8, 8, 8)
            
            for action_id, prefix in action_group:
                spec = MANUAL_ACTION_SPECS[action_id]
                button = QPushButton(f"{prefix} {spec.label}")
                button.clicked.connect(
                    lambda checked=False, current_action_id=action_id: self._on_pet_interaction_clicked(
                        current_action_id, button
                    )
                )
                row_layout.addWidget(button, 1)
            
            menu_layout.addLayout(row_layout)

        self.pet_interaction_menu.hide()

    def _on_main_menu_clicked(self, action_id: str, button: QPushButton) -> None:
        self._play_click_animation(button)
        
        if action_id == "pet_interactions":
            self._show_pet_interaction_menu()
        else:
            self.quick_action_requested.emit(action_id)
            self._close_menu()

    def _on_pet_interaction_clicked(self, action_id: str, button: QPushButton) -> None:
        self._play_click_animation(button)
        self.quick_action_requested.emit(action_id)
        self._close_pet_interaction_menu()
        self._close_menu()

    def _show_pet_interaction_menu(self) -> None:
        if self.context_menu.isVisible():
            main_pos = self.context_menu.pos()
            menu_x = main_pos.x() + 420
            menu_y = main_pos.y()
            
            screen_width = QApplication.primaryScreen().geometry().width()
            if menu_x + 400 > screen_width:
                menu_x = main_pos.x() - 420
            
            self.pet_interaction_menu.move(menu_x, menu_y)
            self.pet_interaction_menu.resize(400, 400)
            self.pet_interaction_menu.show()
            self.pet_interaction_menu.raise_()

    def _close_pet_interaction_menu(self) -> None:
        self.pet_interaction_menu.hide()

    def _on_menu_action_clicked(self, action_id: str, button: QPushButton) -> None:
        self._play_click_animation(button)
        self.quick_action_requested.emit(action_id)
        self._close_menu()

    def _close_menu(self) -> None:
        if hasattr(self, '_menu_position_timer'):
            self._menu_position_timer.stop()
        self._close_pet_interaction_menu()
        self.context_menu.hide()

    def _play_click_animation(self, button: QPushButton) -> None:
        opacity_effect = QGraphicsOpacityEffect(button)
        button.setGraphicsEffect(opacity_effect)
        
        opacity_anim = QPropertyAnimation(opacity_effect, b"opacity")
        opacity_anim.setDuration(100)
        opacity_anim.setStartValue(1.0)
        opacity_anim.setEndValue(0.5)
        opacity_anim.setEasingCurve(QEasingCurve.InOutQuad)
        
        opacity_anim2 = QPropertyAnimation(opacity_effect, b"opacity")
        opacity_anim2.setDuration(100)
        opacity_anim2.setStartValue(0.5)
        opacity_anim2.setEndValue(1.0)
        opacity_anim2.setEasingCurve(QEasingCurve.InOutQuad)
        
        opacity_anim.finished.connect(lambda: opacity_anim2.start())
        opacity_anim.start()

    def _show_context_menu(self, global_pos: QPoint) -> None:
        self.context_menu.move(global_pos)
        self.context_menu.resize(420, 520)
        self.context_menu.show()
        self.context_menu.raise_()
        
        self._menu_position_timer = QTimer(self)
        self._menu_position_timer.setSingleShot(True)
        self._menu_position_timer.timeout.connect(self._update_menu_position)
        self._menu_position_timer.start(50)

    def _update_menu_position(self) -> None:
        if self.context_menu.isVisible():
            pet_center = self.mapToGlobal(self.rect().center())
            menu_x = pet_center.x() - 210
            menu_y = pet_center.y() - 260
            
            if menu_x < 0:
                menu_x = 10
            elif menu_x + 420 > QApplication.primaryScreen().geometry().width():
                menu_x = QApplication.primaryScreen().geometry().width() - 430
            
            if menu_y < 0:
                menu_y = 10
            elif menu_y + 520 > QApplication.primaryScreen().geometry().height():
                menu_y = QApplication.primaryScreen().geometry().height() - 530
            
            self.context_menu.move(menu_x, menu_y)
            self._menu_position_timer.start(50)