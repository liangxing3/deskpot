from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QWidget

from utils.font_loader import build_ui_font, ui_font_stack


class DialogBubble(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet(
            f"color: #5A5A5A; line-height: 150%; font-family: {ui_font_stack(include_emoji=True)};"
        )
        self.label.setFont(build_ui_font(18, include_emoji=True))

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.fade_out)

        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._opacity_anim.setDuration(250)
        self._opacity_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._opacity_anim.finished.connect(self._on_fade_finished)

        self._scale_anim = QPropertyAnimation(self, b"geometry", self)
        self._scale_anim.setDuration(350)
        self._scale_anim.setEasingCurve(QEasingCurve.OutBack)

    def show_message(self, anchor_rect: QRect, text: str, duration_ms: int) -> None:
        if not text:
            return
        self.label.setText(text)
        self.label.adjustSize()

        width = max(200, min(400, self.label.sizeHint().width() + 48))
        height = max(80, self.label.sizeHint().height() + 36)
        self.resize(width, height)
        self.label.setGeometry(20, 16, width - 40, height - 32)

        x = anchor_rect.center().x() - width // 2
        y = anchor_rect.top() - height - 14
        if y < 0:
            y = anchor_rect.bottom() + 12

        target_geo = QRect(x, y, width, height)
        start_geo = QRect(x + width // 2, y + height, 0, 0)

        self._opacity_anim.stop()
        self._scale_anim.stop()
        self._hide_timer.stop()

        self.setGeometry(start_geo)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._scale_anim.setStartValue(start_geo)
        self._scale_anim.setEndValue(target_geo)

        self._opacity_anim.start()
        self._scale_anim.start()
        self._hide_timer.start(duration_ms)

    def hide_bubble(self) -> None:
        self._hide_timer.stop()
        self._opacity_anim.stop()
        self._scale_anim.stop()
        self.hide()

    def fade_out(self) -> None:
        self._opacity_anim.stop()
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.start()

    def _on_fade_finished(self) -> None:
        if self.windowOpacity() <= 0.0:
            self.hide()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        rect = self.rect().adjusted(2, 2, -2, -10)
        path.addRoundedRect(rect, 18, 18)
        path.moveTo(rect.center().x() - 10, rect.bottom())
        path.lineTo(rect.center().x(), rect.bottom() + 10)
        path.lineTo(rect.center().x() + 10, rect.bottom())
        path.closeSubpath()

        gradient = QColor(255, 253, 254, 250)
        painter.fillPath(path, gradient)
        painter.setPen(QPen(QColor(255, 207, 223, 220), 2))
        painter.drawPath(path)
        super().paintEvent(event)