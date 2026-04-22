from __future__ import annotations

import logging
import time

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QLabel, QWidget

from ui.theme import TEXT_PRIMARY, base_font_stack
from utils.font_loader import build_ui_font


logger = logging.getLogger("desktop_pet.bubble")


class DialogBubble(QWidget):
    """Transient bubble widget that follows the pet window via events."""

    RAW_TEXT_HARD_LIMIT = 280
    SIMPLE_TEXT_LIMIT = 72
    MAX_TRUNCATE_ITERATIONS = 10
    MAX_TEXT_WIDTH = 220
    MAX_LINE_COUNT = 4
    ELLIPSIS = "..."

    request_show = Signal(QRect, str, int, int)
    request_hide = Signal()
    request_offset = Signal(int, int)
    request_anchor_top_left = Signal(QPoint)

    def __init__(self, parent: QWidget | None = None, font_size: int = 13) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )

        self._font_size = int(font_size)
        self._current_text = ""
        self._current_priority = -1
        self._anchor_rect = QRect()
        self._pointer_on_top = False
        self._reposition_scheduled = False
        self._hidden_for_offscreen = False
        self._expires_at = 0.0

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.fade_out)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(16)
        self._shadow.setOffset(0, 3)
        self._shadow.setColor(QColor(180, 80, 100, 35))
        self.setGraphicsEffect(self._shadow)

        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._opacity_anim.setDuration(150)
        self._opacity_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._opacity_anim.finished.connect(self._on_fade_finished)

        self._pos_anim = QPropertyAnimation(self, b"pos", self)
        self._pos_anim.setDuration(100)
        self._pos_anim.setEasingCurve(QEasingCurve.OutBack)

        self.request_show.connect(self._show_message_impl, Qt.QueuedConnection)
        self.request_hide.connect(self._hide_bubble_impl, Qt.QueuedConnection)
        self.request_offset.connect(self._offset_by_impl, Qt.QueuedConnection)
        self.request_anchor_top_left.connect(self._set_anchor_top_left_impl, Qt.QueuedConnection)
        self._apply_font()

    def showMessage(self, text: str, duration_ms: int = 4000, priority: int = 0) -> None:
        """Compatibility API that requires a prior anchor rect."""

        self.show_message(self._anchor_rect, text, duration_ms, priority=priority)

    def show_message(
        self,
        anchor_rect: QRect,
        text: str,
        duration_ms: int,
        priority: int = 0,
    ) -> None:
        """Show a bubble relative to the given pet geometry."""

        if QThread.currentThread() is not self.thread():
            self.request_show.emit(QRect(anchor_rect), text, int(duration_ms), int(priority))
            return
        self._show_message_impl(QRect(anchor_rect), text, int(duration_ms), int(priority))

    def update_font_size(self, size: int) -> None:
        self._font_size = int(size)
        self._apply_font()
        if self._current_text:
            self._resize_to_content()
            self._schedule_reposition()

    def hide_bubble(self) -> None:
        if QThread.currentThread() is not self.thread():
            self.request_hide.emit()
            return
        self._hide_bubble_impl()

    def offset_by(self, delta_x: int, delta_y: int) -> None:
        if delta_x == 0 and delta_y == 0:
            return
        if QThread.currentThread() is not self.thread():
            self.request_offset.emit(int(delta_x), int(delta_y))
            return
        self._offset_by_impl(int(delta_x), int(delta_y))

    def update_anchor_top_left(self, point: QPoint) -> None:
        if QThread.currentThread() is not self.thread():
            self.request_anchor_top_left.emit(QPoint(point))
            return
        self._set_anchor_top_left_impl(QPoint(point))

    @Slot(QRect, str, int, int)
    def _show_message_impl(self, anchor_rect: QRect, text: str, duration_ms: int, priority: int) -> None:
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return
        if self._hide_timer.isActive() and priority < self._current_priority:
            return

        self._anchor_rect = QRect(anchor_rect)
        self._current_text = normalized_text
        self._current_priority = int(priority)
        self._expires_at = time.monotonic() + max(1, int(duration_ms)) / 1000.0

        try:
            if len(normalized_text) > self.SIMPLE_TEXT_LIMIT * 2:
                display_text = self._simple_truncate_text(normalized_text, self.SIMPLE_TEXT_LIMIT)
                logger.debug(
                    "[bubble] simple truncate in _show_message_impl raw_len=%s final_len=%s",
                    len(normalized_text),
                    len(display_text),
                )
            else:
                display_text = self._truncate_text(normalized_text)
        except Exception:
            logger.exception("[bubble] _truncate_text failed; falling back to simple truncation")
            display_text = self._simple_truncate_text(normalized_text, self.SIMPLE_TEXT_LIMIT)

        if not display_text:
            return

        self.label.setText(display_text)
        self._resize_to_content()

        self._hide_timer.stop()
        self._opacity_anim.stop()
        self._pos_anim.stop()
        self._schedule_reposition(animated=True)
        self._hide_timer.start(max(1, int(duration_ms)))

    @Slot()
    def _hide_bubble_impl(self) -> None:
        self._hide_timer.stop()
        self._opacity_anim.stop()
        self._pos_anim.stop()
        self._current_text = ""
        self._current_priority = -1
        self._expires_at = 0.0
        self._hidden_for_offscreen = False
        self.hide()

    @Slot(int, int)
    def _offset_by_impl(self, delta_x: int, delta_y: int) -> None:
        if self._anchor_rect.isNull():
            return
        self._anchor_rect.translate(int(delta_x), int(delta_y))
        self._schedule_reposition()

    @Slot(QPoint)
    def _set_anchor_top_left_impl(self, point: QPoint) -> None:
        if self._anchor_rect.isNull():
            return
        self._anchor_rect.moveTopLeft(point)
        self._schedule_reposition()

    def fade_out(self) -> None:
        self._opacity_anim.stop()
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.start()

    def _apply_font(self) -> None:
        self.label.setFont(build_ui_font(self._font_size, include_emoji=True, prefer_custom=True))
        self.label.setStyleSheet(
            f"background: transparent; color: {TEXT_PRIMARY}; font-family: {base_font_stack(include_emoji=True)};"
        )

    def _truncate_text(self, text: str) -> str:
        current = self._normalize_text(text)
        if not current:
            return ""

        metrics = QFontMetrics(self.label.font())
        max_width = self.MAX_TEXT_WIDTH
        max_height = metrics.lineSpacing() * self.MAX_LINE_COUNT

        if len(current) > self.RAW_TEXT_HARD_LIMIT:
            current = current[: self.RAW_TEXT_HARD_LIMIT].rstrip()
            logger.debug("[bubble] hard-capped raw text to %s chars", len(current))

        if self._fits_height(metrics, current, max_width, max_height):
            logger.debug(
                "[bubble] _truncate_text raw_len=%s simple=False iterations=0 final_len=%s",
                len(current),
                len(current),
            )
            return current

        best = self._simple_truncate_text(current, min(32, len(current)))
        low = 1
        high = max(1, min(len(current), self.SIMPLE_TEXT_LIMIT))
        iterations = 0

        while low <= high and iterations < self.MAX_TRUNCATE_ITERATIONS:
            iterations += 1
            mid = (low + high) // 2
            candidate = self._simple_truncate_text(current, mid)
            if self._fits_height(metrics, candidate, max_width, max_height):
                best = candidate
                low = mid + 1
            else:
                high = mid - 1

        if not best:
            best = self.ELLIPSIS

        logger.debug(
            "[bubble] _truncate_text raw_len=%s simple=False iterations=%s final_len=%s",
            len(current),
            iterations,
            len(best),
        )
        return best

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
        normalized = " ".join(part for part in normalized.split() if part)
        if len(normalized) > self.RAW_TEXT_HARD_LIMIT:
            normalized = normalized[: self.RAW_TEXT_HARD_LIMIT].rstrip()
        return normalized

    def _simple_truncate_text(self, text: str, max_chars: int) -> str:
        current = (text or "").strip()
        if not current:
            return ""
        if len(current) <= max_chars:
            return current
        trimmed = current[: max(1, max_chars)].rstrip()
        return f"{trimmed}{self.ELLIPSIS}" if trimmed else self.ELLIPSIS

    def _fits_height(self, metrics: QFontMetrics, text: str, max_width: int, max_height: int) -> bool:
        rect = metrics.boundingRect(
            QRect(0, 0, max_width, 9999),
            Qt.TextWordWrap | Qt.AlignCenter,
            text,
        )
        return rect.height() <= max_height

    def _resize_to_content(self) -> None:
        metrics = QFontMetrics(self.label.font())
        rect = metrics.boundingRect(
            QRect(0, 0, self.MAX_TEXT_WIDTH, 9999),
            Qt.TextWordWrap | Qt.AlignCenter,
            self.label.text(),
        )
        horizontal_padding = 18
        vertical_padding = 14
        pointer_size = 10
        bubble_width = rect.width() + horizontal_padding * 2
        bubble_height = rect.height() + vertical_padding * 2 + pointer_size
        self.setFixedSize(bubble_width, bubble_height)
        if self._pointer_on_top:
            self.label.setGeometry(horizontal_padding, vertical_padding + pointer_size, rect.width(), rect.height())
        else:
            self.label.setGeometry(horizontal_padding, vertical_padding, rect.width(), rect.height())

    def _schedule_reposition(self, *, animated: bool = False) -> None:
        self._animated_reposition = animated
        if self._reposition_scheduled:
            return
        self._reposition_scheduled = True
        QTimer.singleShot(0, self._apply_reposition)

    def _apply_reposition(self) -> None:
        self._reposition_scheduled = False
        if not self._current_text or self._anchor_rect.isNull():
            return

        geometry = self._target_geometry()
        if geometry is None:
            if self.isVisible():
                self.hide()
            self._hidden_for_offscreen = True
            return

        start_pos = geometry.topLeft() + QPoint(0, 6 if not self._pointer_on_top else -6)
        was_hidden = not self.isVisible() or self._hidden_for_offscreen
        self._hidden_for_offscreen = False

        self._resize_to_content()
        self.raise_()
        if was_hidden:
            self.move(start_pos)
            self.setWindowOpacity(0.0)
            self.show()
            self._opacity_anim.stop()
            self._opacity_anim.setDuration(100)
            self._opacity_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._opacity_anim.setStartValue(0.0)
            self._opacity_anim.setEndValue(1.0)
            self._opacity_anim.start()
            self._pos_anim.stop()
            self._pos_anim.setStartValue(start_pos)
            self._pos_anim.setEndValue(geometry.topLeft())
            self._pos_anim.start()
        else:
            self._pos_anim.stop()
            if getattr(self, "_animated_reposition", False):
                self._pos_anim.setStartValue(self.pos())
                self._pos_anim.setEndValue(geometry.topLeft())
                self._pos_anim.start()
            else:
                self.move(geometry.topLeft())

    def _target_geometry(self) -> QRect | None:
        if self._anchor_rect.isNull():
            return None
        screen = QApplication.screenAt(self._anchor_rect.center()) or QApplication.primaryScreen()
        if screen is None:
            return None
        available = screen.availableGeometry()
        pet_rect = QRect(self._anchor_rect)
        if not available.intersects(pet_rect):
            return None

        bubble_width = self.width()
        bubble_height = self.height()
        pointer_gap = 8
        x = pet_rect.center().x() - bubble_width // 2
        x = max(available.left() + 8, min(x, available.right() - bubble_width - 8))

        preferred_y = pet_rect.top() - bubble_height - pointer_gap
        if preferred_y < available.top() + 8:
            self._pointer_on_top = True
            y = pet_rect.bottom() + pointer_gap
        else:
            self._pointer_on_top = False
            y = preferred_y

        y = max(available.top() + 8, min(y, available.bottom() - bubble_height - 8))
        return QRect(int(x), int(y), bubble_width, bubble_height)

    def _on_fade_finished(self) -> None:
        if self.windowOpacity() <= 0.0:
            self.hide()
            self._current_priority = -1
            self._current_text = ""
            self._expires_at = 0.0

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pointer_size = 10
        rect = self.rect().adjusted(2, 2, -2, -2)
        bubble_rect = rect.adjusted(
            0,
            pointer_size if self._pointer_on_top else 0,
            0,
            -pointer_size if not self._pointer_on_top else 0,
        )

        path = QPainterPath()
        path.addRoundedRect(bubble_rect, 18, 18)

        center_x = bubble_rect.center().x()
        if self._pointer_on_top:
            path.moveTo(center_x - 10, bubble_rect.top())
            path.lineTo(center_x, bubble_rect.top() - pointer_size)
            path.lineTo(center_x + 10, bubble_rect.top())
        else:
            path.moveTo(center_x - 10, bubble_rect.bottom())
            path.lineTo(center_x, bubble_rect.bottom() + pointer_size)
            path.lineTo(center_x + 10, bubble_rect.bottom())
        path.closeSubpath()

        painter.fillPath(path, QColor(255, 248, 252, 240))
        painter.setPen(QPen(QColor(244, 160, 181), 1.2))
        painter.drawPath(path)
        super().paintEvent(event)
