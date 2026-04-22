from __future__ import annotations

import logging

from PySide6.QtCore import QEasingCurve, QPoint, QEvent, Property, QPropertyAnimation, Qt, Signal, Slot
from PySide6.QtGui import QFontMetrics, QMouseEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from data.models import WindowPosition
from ui.icons import make_pixmap
from ui.theme import Colors, Metrics, Typography, dialog_shell_stylesheet


logger = logging.getLogger("desktop_pet.dialog")


class DialogShell(QDialog):
    """Shared frameless dialog shell used by all floating panels."""

    visibility_changed = Signal(bool)
    request_offset = Signal(int, int)
    drag_finished = Signal(object)

    def __init__(self, *, title: str, icon_name: str, parent=None) -> None:
        super().__init__(parent)
        self._title_text = title
        self._drag_active = False
        self._drag_offset = QPoint()
        self._allow_close = False
        self._closing_with_animation = False
        self._shell_opacity = 1.0

        self.setWindowTitle(title)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(False)
        self.setStyleSheet("QDialog { background: transparent; border: none; outline: none; }")
        self.request_offset.connect(self._offset_by_impl, Qt.QueuedConnection)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.surface = QWidget(self)
        self.surface.setObjectName("DialogSurface")
        self.surface.setStyleSheet(dialog_shell_stylesheet())
        root_layout.addWidget(self.surface)

        surface_layout = QVBoxLayout(self.surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)

        self.header = QWidget(self.surface)
        self.header.setObjectName("DialogHeader")
        self.header.setFixedHeight(40)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(14, 6, 8, 6)
        header_layout.setSpacing(8)

        self.icon_label = QLabel(self.header)
        self.icon_label.setPixmap(make_pixmap(icon_name, size=16))
        self.icon_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.title_label = QLabel(title, self.header)
        self.title_label.setObjectName("DialogTitle")
        self.title_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.close_button = QPushButton("×", self.header)
        self.close_button.setObjectName("DialogClose")
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.clicked.connect(self._log_close_button_clicked)
        self.close_button.clicked.connect(self.close)

        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.close_button)
        surface_layout.addWidget(self.header)

        self.body = QWidget(self.surface)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(Metrics.PADDING_LG, Metrics.PADDING_LG, Metrics.PADDING_LG, Metrics.PADDING_LG)
        self.body_layout.setSpacing(12)
        surface_layout.addWidget(self.body)

        self.header.setCursor(Qt.OpenHandCursor)
        self.header.installEventFilter(self)

        self._fade_anim = QPropertyAnimation(self, b"shellOpacity", self)
        self._fade_anim.finished.connect(self._on_fade_finished)

        self._update_title_label()

    def getShellOpacity(self) -> float:  # noqa: N802
        return self._shell_opacity

    def setShellOpacity(self, value: float) -> None:  # noqa: N802
        self._shell_opacity = max(0.0, min(1.0, float(value)))
        self.setWindowOpacity(self._shell_opacity)

    shellOpacity = Property(float, getShellOpacity, setShellOpacity)

    def prepare_for_exit(self) -> None:
        self._allow_close = True

    def set_title(self, title: str) -> None:
        self._title_text = title
        self.setWindowTitle(title)
        self._update_title_label()

    def restore_position(self, position: WindowPosition) -> None:
        self.move(int(position.x), int(position.y))

    def current_position(self) -> WindowPosition:
        point = self.pos()
        return WindowPosition(x=int(point.x()), y=int(point.y()), first_shown=False)

    def offset_by(self, delta_x: int, delta_y: int) -> None:
        if delta_x == 0 and delta_y == 0:
            return
        self.request_offset.emit(int(delta_x), int(delta_y))

    @Slot(int, int)
    def _offset_by_impl(self, delta_x: int, delta_y: int) -> None:
        if not self.isVisible():
            return
        self.move(self.x() + int(delta_x), self.y() + int(delta_y))

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._ensure_initial_layout_size()
        self._debug_shell_state("showEvent before restore")
        self.raise_()
        self.activateWindow()
        self._play_show_animation()
        self._debug_shell_state("showEvent after restore")
        self.visibility_changed.emit(True)

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        self._drag_active = False
        self.header.setCursor(Qt.OpenHandCursor)
        self.visibility_changed.emit(False)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_title_label()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._allow_close:
            event.accept()
            return
        if self._closing_with_animation:
            event.ignore()
            return
        self._closing_with_animation = True
        self._fade_anim.stop()
        self._fade_anim.setDuration(80)
        self._fade_anim.setEasingCurve(QEasingCurve.InCubic)
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()
        event.ignore()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.header and isinstance(event, QMouseEvent):
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_active = True
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.header.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return True

            if event.type() == QEvent.MouseMove and self._drag_active and event.buttons() & Qt.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_offset)
                event.accept()
                return True

            if event.type() == QEvent.MouseButtonRelease and self._drag_active and event.button() == Qt.LeftButton:
                self._drag_active = False
                self.header.setCursor(Qt.OpenHandCursor)
                self.drag_finished.emit(self.current_position())
                event.accept()
                return True

        return super().eventFilter(watched, event)

    def _play_show_animation(self) -> None:
        self._closing_with_animation = False
        self._fade_anim.stop()
        self._shell_opacity = 1.0
        self.setWindowOpacity(1.0)
        self.surface.show()
        self.header.show()
        self.body.show()
        self.surface.raise_()
        self.surface.update()
        self.body.update()
        self.update()

    def _update_title_label(self) -> None:
        metrics = QFontMetrics(self.title_label.font() or Typography.font(Typography.SIZE_H2, Typography.WEIGHT_MEDIUM))
        available_width = max(80, self.header.width() - 90)
        self.title_label.setText(metrics.elidedText(self._title_text, Qt.ElideRight, available_width))

    def _ensure_initial_layout_size(self) -> None:
        """Ensure sizeHint/layout applied before first paint.

        Some Qt frameless/translucent dialogs may appear undersized until the
        first user interaction triggers a layout pass. We force a layout
        activation here so the dialog opens at its intended size.
        """

        # Ensure the layout has real geometry to compute from.
        self.surface.ensurePolished()
        self.body.ensurePolished()
        if self.surface.layout() is not None:
            self.surface.layout().activate()
        if self.body.layout() is not None:
            self.body.layout().activate()

        hint = self.sizeHint()
        if not hint.isValid():
            return

        target_w = max(self.width(), hint.width(), int(Metrics.DIALOG_MIN_W))
        target_h = max(self.height(), hint.height(), int(Metrics.DIALOG_MIN_H))
        if target_w == self.width() and target_h == self.height():
            return
        self.resize(int(target_w), int(target_h))

    def _on_fade_finished(self) -> None:
        if self._closing_with_animation and self.windowOpacity() <= 0.0:
            self._closing_with_animation = False
            self.hide()

    def _debug_shell_state(self, prefix: str) -> None:
        logger.info(
            "[dialog-shell] %s title=%s opacity=%s hidden=%s minimized=%s active=%s flags=%s "
            "surface_visible=%s surface_size=%s body_visible=%s body_size=%s header_visible=%s header_size=%s "
            "fade_state=%s closing=%s",
            prefix,
            self.windowTitle(),
            self.windowOpacity(),
            self.isHidden(),
            self.isMinimized(),
            self.isActiveWindow(),
            int(self.windowFlags()),
            self.surface.isVisible(),
            self.surface.size(),
            self.body.isVisible(),
            self.body.size(),
            self.header.isVisible(),
            self.header.size(),
            self._fade_anim.state(),
            self._closing_with_animation,
        )

    @Slot()
    def _log_close_button_clicked(self) -> None:
        logger.info(
            "[dialog-shell] close button clicked title=%s parent=%s isWindow=%s flags=%s",
            self.windowTitle(),
            self.parentWidget(),
            self.isWindow(),
            int(self.windowFlags()),
        )
