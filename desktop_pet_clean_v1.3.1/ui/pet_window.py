from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QBitmap,
    QCloseEvent,
    QContextMenuEvent,
    QImage,
    QImageReader,
    QMouseEvent,
    QMoveEvent,
    QMovie,
    QPixmap,
    QRegion,
)
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QWidget

from data.models import WindowPosition
from ui.dialog_bubble import DialogBubble
from ui.icons import make_icon
from ui.theme import menu_stylesheet


class PetWindow(QWidget):
    """Transparent top-level pet window that only renders the current GIF."""

    MINIMUM_SIZE = QSize(1, 1)
    DRAG_THRESHOLD_PX = 8

    # --- Signals ---
    weather_requested = Signal()
    answerbook_requested = Signal()
    settings_requested = Signal()
    status_requested = Signal()
    manual_action_requested = Signal(str)
    pet_clicked = Signal()
    drag_started = Signal()
    window_moved = Signal(int, int)
    petMoved = Signal(QPoint)
    drag_finished = Signal(object)
    hidden_to_tray = Signal()
    interacted = Signal()

    def __init__(
        self,
        *,
        gif_path: Path,
        parent: QWidget | None = None,
        menu_font_size: int = 13,
        bubble_font_size: int = 13,
    ) -> None:
        super().__init__(parent)
        self.gif_path = Path(gif_path)
        self.movie: QMovie | None = None
        self._drag_active = False
        self._drag_candidate = False
        self._drag_offset = QPoint()
        self._press_origin = QPoint()
        self._drag_moved = False
        self._allow_close = False
        self._hit_mask = QRegion()
        self._menu_font_size = int(menu_font_size)
        self._display_pixmap = QPixmap()
        self._display_size = QSize(self.MINIMUM_SIZE)
        self._frame_rects: list[QRect] = []
        self._cached_gif_path = ""

        self.setWindowTitle("Desktop Pet")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setStyleSheet("QWidget { background: transparent; border: none; outline: none; }")

        self._build_ui()
        self._build_menu()
        self.bubble = DialogBubble(font_size=bubble_font_size)
        self.petMoved.connect(self._handle_pet_moved)
        self.set_menu_font_size(menu_font_size)
        if not self._load_movie(self.gif_path):
            raise RuntimeError(f"Invalid GIF file: {self.gif_path}")

    def restore_position(self, position: WindowPosition) -> None:
        """Restore the window position from persisted config."""

        self.move(int(position.x), int(position.y))

    def current_position(self) -> WindowPosition:
        """Return the current top-left position."""

        point = self.pos()
        return WindowPosition(x=int(point.x()), y=int(point.y()), first_shown=False)

    def update_identity(self, *, pet_name: str, emotion_text: str) -> None:
        """Update tooltip information for the current pet state."""

        self.setToolTip(f"{pet_name}  {emotion_text}".strip())

    def apply_animation(self, gif_path: Path | None) -> bool:
        """Switch to another GIF file if it exists and is valid."""

        if gif_path is None:
            return False
        return self._load_movie(Path(gif_path))

    def current_frame_pixmap(self):
        """Return the current frame pixmap for preview use."""

        if self._display_pixmap.isNull():
            return None
        return self._display_pixmap

    def show_bubble(self, text: str, ttl_ms: int = 4000, priority: int = 0) -> None:
        """Show a bubble relative to the current pet geometry."""

        self.bubble.show_message(self.frameGeometry(), text, ttl_ms, priority=priority)

    def move_attached_overlays(self, delta_x: int, delta_y: int) -> None:
        """Compatibility hook for overlay movement during controller transition."""

        self.bubble.offset_by(delta_x, delta_y)

    def set_menu_font_size(self, size_px: int) -> None:
        """Apply menu and bubble font sizing."""

        self._menu_font_size = int(size_px)
        self.menu.setStyleSheet(menu_stylesheet(int(size_px)))
        self.bubble.update_font_size(int(size_px))

    def set_window_states(self, *, weather_open: bool, answerbook_open: bool, settings_open: bool) -> None:
        """Reflect dialog visibility in menu checked state."""

        self.weather_action.setChecked(weather_open)
        self.answerbook_action.setChecked(answerbook_open)
        self.settings_action.setChecked(settings_open)

    def prepare_for_exit(self) -> None:
        """Allow the next close event to terminate the top-level window."""

        self._allow_close = True

    def hitTest(self, pos: QPoint) -> bool:  # noqa: N802
        """Return whether the given widget-local point hits a non-transparent pixel."""

        if self._drag_active:
            return True
        label_pos = self.movie_label.mapFrom(self, pos)
        return self.movie_label.rect().contains(label_pos) and self._hit_mask.contains(label_pos)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802
        if not self.hitTest(event.pos()):
            event.ignore()
            return
        self.interacted.emit()
        self._prepare_menu_direction()
        self.menu.popup(self._menu_anchor_pos())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.hitTest(event.position().toPoint()):
            self._drag_candidate = True
            self._drag_active = False
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._press_origin = event.globalPosition().toPoint()
            self._drag_moved = False
            self.grabMouse()
            self.interacted.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_candidate and event.buttons() & Qt.LeftButton:
            if not self._drag_active:
                if (event.globalPosition().toPoint() - self._press_origin).manhattanLength() < self.DRAG_THRESHOLD_PX:
                    event.accept()
                    return
                self._drag_active = True
                self._drag_moved = True
                self.drag_started.emit()
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and (self._drag_candidate or self._drag_active):
            was_dragging = self._drag_active
            self._drag_candidate = False
            self._drag_active = False
            self._drag_moved = False
            self.releaseMouse()
            if was_dragging:
                self.drag_finished.emit(self.current_position())
            else:
                self.pet_clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def moveEvent(self, event: QMoveEvent) -> None:  # noqa: N802
        super().moveEvent(event)
        delta = event.pos() - event.oldPos()
        if delta.x() or delta.y():
            self.window_moved.emit(delta.x(), delta.y())
        self.petMoved.emit(self.frameGeometry().topLeft())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._drag_candidate or self._drag_active:
            self._drag_candidate = False
            self._drag_active = False
            self.releaseMouse()
        if self._allow_close:
            self.bubble.hide_bubble()
            self.bubble.close()
            event.accept()
            return
        self.bubble.hide_bubble()
        self.hide()
        self.hidden_to_tray.emit()
        event.ignore()

    def _build_ui(self) -> None:
        self.movie_label = QLabel(self)
        self.movie_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.movie_label.setStyleSheet("background-color: transparent; border: none; outline: none;")
        self.movie_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.movie_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.movie_label.setGeometry(0, 0, self.MINIMUM_SIZE.width(), self.MINIMUM_SIZE.height())
        self.resize(self.MINIMUM_SIZE)

    def _build_menu(self) -> None:
        self.menu = QMenu(self)
        self.interaction_menu = self.menu.addMenu(make_icon("pet"), "互动")
        self.interaction_menu.menuAction().setCheckable(True)
        self.interaction_menu.aboutToShow.connect(lambda: self.interaction_menu.menuAction().setChecked(True))
        self.interaction_menu.aboutToHide.connect(lambda: self.interaction_menu.menuAction().setChecked(False))

        action_specs = (
            ("feed", "喂食", "feed"),
            ("play", "陪玩", "play"),
            ("clean", "清洁", "clean"),
            ("rest", "休息", "rest"),
        )
        for action_id, label, icon_name in action_specs:
            action = QAction(make_icon(icon_name), label, self.interaction_menu)
            action.triggered.connect(
                lambda checked=False, current=action_id: self.manual_action_requested.emit(current)
            )
            self.interaction_menu.addAction(action)

        self.menu.addSeparator()

        self.weather_action = QAction(make_icon("weather"), "天气", self.menu)
        self.weather_action.setCheckable(True)
        self.weather_action.triggered.connect(self.weather_requested.emit)
        self.menu.addAction(self.weather_action)

        self.answerbook_action = QAction(make_icon("answerbook"), "答案之书", self.menu)
        self.answerbook_action.setCheckable(True)
        self.answerbook_action.triggered.connect(self.answerbook_requested.emit)
        self.menu.addAction(self.answerbook_action)

        self.menu.addSeparator()

        self.settings_action = QAction(make_icon("settings"), "设置", self.menu)
        self.settings_action.setCheckable(True)
        self.settings_action.triggered.connect(self.settings_requested.emit)
        self.menu.addAction(self.settings_action)

    def _load_movie(self, gif_path: Path) -> bool:
        if not gif_path.exists():
            return False

        self._ensure_frame_rects(gif_path)
        movie = QMovie(str(gif_path))
        movie.setCacheMode(QMovie.CacheAll)
        if not movie.isValid():
            return False

        if self.movie is not None:
            try:
                self.movie.frameChanged.disconnect(self._sync_to_movie_frame)
            except (RuntimeError, TypeError):
                pass
            self.movie.stop()

        self.gif_path = gif_path
        self.movie = movie
        self.movie.frameChanged.connect(self._sync_to_movie_frame)
        self.movie_label.clear()
        self._display_pixmap = QPixmap()
        self._display_size = QSize(self.MINIMUM_SIZE)
        movie.start()
        self._sync_to_movie_frame(movie.currentFrameNumber())
        return True

    @Slot()
    @Slot(int)
    def _sync_to_movie_frame(self, _frame_index: int = 0) -> None:
        if self.movie is None:
            return

        raw_pixmap = self.movie.currentPixmap()
        if raw_pixmap.isNull():
            return

        frame_index = int(_frame_index)
        if frame_index < 0:
            frame_index = int(self.movie.currentFrameNumber())

        frame_rect = self._frame_rect_for_index(frame_index, raw_pixmap)
        pixmap = raw_pixmap.copy(frame_rect)
        if pixmap.isNull():
            pixmap = raw_pixmap

        if pixmap.size().isValid():
            self._sync_window_geometry(pixmap.size())

        self._display_pixmap = pixmap
        self.movie_label.setPixmap(pixmap)
        self._update_hit_mask(pixmap)
        mask_bitmap = QBitmap.fromImage(pixmap.toImage().createAlphaMask())
        if not mask_bitmap.isNull():
            self.setMask(mask_bitmap)
        else:
            self.clearMask()

    def _ensure_frame_rects(self, gif_path: Path) -> None:
        cache_key = str(gif_path.resolve())
        if cache_key == self._cached_gif_path and self._frame_rects:
            return

        self._frame_rects = self._precompute_frame_rects(gif_path)
        self._cached_gif_path = cache_key

    def _precompute_frame_rects(self, gif_path: Path) -> list[QRect]:
        reader = QImageReader(str(gif_path))
        rects: list[QRect] = []
        while reader.canRead():
            image = reader.read()
            if image.isNull():
                break
            rect = _non_transparent_rect(image)
            rects.append(rect if rect.isValid() else image.rect())
        if rects:
            return rects
        return [QRect(0, 0, self.MINIMUM_SIZE.width(), self.MINIMUM_SIZE.height())]

    def _frame_rect_for_index(self, frame_index: int, pixmap: QPixmap) -> QRect:
        raw_rect = pixmap.rect()
        if not raw_rect.isValid():
            return QRect(0, 0, self.MINIMUM_SIZE.width(), self.MINIMUM_SIZE.height())

        if 0 <= frame_index < len(self._frame_rects):
            clipped = self._frame_rects[frame_index].intersected(raw_rect)
            if clipped.isValid():
                return clipped
        return raw_rect

    def _sync_window_geometry(self, size: QSize) -> None:
        width = max(self.MINIMUM_SIZE.width(), int(size.width()))
        height = max(self.MINIMUM_SIZE.height(), int(size.height()))
        resolved = QSize(width, height)
        if resolved == self._display_size and self.movie_label.geometry().size() == resolved and self.size() == resolved:
            return

        self._display_size = resolved
        self.movie_label.setGeometry(0, 0, width, height)
        self.resize(width, height)

    def _update_hit_mask(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            self._hit_mask = QRegion()
            return
        bitmap = QBitmap.fromImage(pixmap.toImage().createAlphaMask())
        self._hit_mask = QRegion(bitmap)

    def _menu_anchor_pos(self) -> QPoint:
        anchor = self.frameGeometry()
        raw_pos = QPoint(anchor.right() + 8, anchor.top())
        screen = QApplication.screenAt(raw_pos) or self.screen() or QApplication.primaryScreen()
        if screen is None:
            return raw_pos

        available = screen.availableGeometry()
        menu_size = self.menu.sizeHint()
        x = min(raw_pos.x(), available.right() - menu_size.width() - 4)
        y = min(raw_pos.y(), available.bottom() - menu_size.height() - 4)
        x = max(x, available.left() + 4)
        y = max(y, available.top() + 4)
        return QPoint(int(x), int(y))

    def _prepare_menu_direction(self) -> None:
        anchor = self.frameGeometry()
        screen = QApplication.screenAt(anchor.center()) or self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.interaction_menu.setLayoutDirection(Qt.LeftToRight)
            return
        available = screen.availableGeometry()
        near_right_edge = available.right() - anchor.right() < 200
        self.interaction_menu.setLayoutDirection(Qt.RightToLeft if near_right_edge else Qt.LeftToRight)

    @Slot(QPoint)
    def _handle_pet_moved(self, top_left: QPoint) -> None:
        self.bubble.update_anchor_top_left(top_left)


def _patched_build_menu(self: PetWindow) -> None:
    self.menu = QMenu(self)
    self.interaction_menu = self.menu.addMenu(make_icon("pet"), "互动")
    self.interaction_menu.menuAction().setCheckable(True)
    self.interaction_menu.aboutToShow.connect(lambda: self.interaction_menu.menuAction().setChecked(True))
    self.interaction_menu.aboutToHide.connect(lambda: self.interaction_menu.menuAction().setChecked(False))

    action_specs = (
        ("feed", "喂食", "feed"),
        ("play", "陪玩", "play"),
        ("clean", "清洁", "clean"),
        ("rest", "休息", "rest"),
    )
    for action_id, label, icon_name in action_specs:
        action = QAction(make_icon(icon_name), label, self.interaction_menu)
        action.triggered.connect(lambda checked=False, current=action_id: self.manual_action_requested.emit(current))
        self.interaction_menu.addAction(action)

    self.menu.addSeparator()

    self.weather_action = QAction(make_icon("weather"), "天气", self.menu)
    self.weather_action.setCheckable(True)
    self.weather_action.triggered.connect(lambda checked=False: self.weather_requested.emit())
    self.menu.addAction(self.weather_action)

    self.answerbook_action = QAction(make_icon("answerbook"), "答案之书", self.menu)
    self.answerbook_action.setCheckable(True)
    self.answerbook_action.triggered.connect(lambda checked=False: self.answerbook_requested.emit())
    self.menu.addAction(self.answerbook_action)

    self.menu.addSeparator()

    self.settings_action = QAction(make_icon("settings"), "设置", self.menu)
    self.settings_action.setCheckable(True)
    self.settings_action.triggered.connect(lambda checked=False: self.settings_requested.emit())
    self.menu.addAction(self.settings_action)


PetWindow._build_menu = _patched_build_menu


def _non_transparent_rect(image: QImage) -> QRect:
    converted = image.convertToFormat(QImage.Format.Format_ARGB32)
    mask = converted.createAlphaMask()
    return QRegion(QBitmap.fromImage(mask)).boundingRect()
