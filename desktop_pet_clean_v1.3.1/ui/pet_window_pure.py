from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal, Slot
from PySide6.QtGui import QAction, QCloseEvent, QContextMenuEvent, QMouseEvent, QMovie
from PySide6.QtWidgets import QLabel, QMenu, QVBoxLayout, QWidget

from data.models import WindowPosition
from ui.dialog_bubble import DialogBubble
from ui.icons import make_icon
from ui.theme import base_font_stack


class PetWindow(QWidget):
    weather_requested = Signal()
    answerbook_requested = Signal()
    settings_requested = Signal()
    status_requested = Signal()
    manual_action_requested = Signal(str)
    window_moved = Signal(int, int)
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
        self._drag_offset = QPoint()
        self._allow_close = False
        self._pet_name = "Pet"
        self._emotion_text = ""

        self.setWindowTitle("Desktop Pet")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setStyleSheet("QWidget { background: transparent; border: none; outline: none; }")

        self._build_ui()
        self._build_menu()
        self._normalize_menu_labels()
        self.bubble = DialogBubble(font_size=bubble_font_size)
        self.set_menu_font_size(menu_font_size)
        if not self._load_movie(self.gif_path):
            raise RuntimeError(f"Invalid GIF file: {self.gif_path}")

    def restore_position(self, position: WindowPosition) -> None:
        self.move(int(position.x), int(position.y))

    def current_position(self) -> WindowPosition:
        point = self.pos()
        return WindowPosition(x=int(point.x()), y=int(point.y()))

    def update_identity(self, *, pet_name: str, emotion_text: str) -> None:
        self._pet_name = pet_name
        self._emotion_text = emotion_text
        self.setToolTip(f"{pet_name}  {emotion_text}".strip())

    def apply_animation(self, gif_path: Path | None) -> bool:
        if gif_path is None:
            return False
        return self._load_movie(Path(gif_path))

    def show_bubble(self, text: str, ttl_ms: int = 4000) -> None:
        self.bubble.show_message(self.frameGeometry(), text, ttl_ms)

    def move_attached_overlays(self, delta_x: int, delta_y: int) -> None:
        self.bubble.offset_by(delta_x, delta_y)

    def set_menu_font_size(self, size_px: int) -> None:
        self.menu.setStyleSheet(_menu_stylesheet(size_px))
        self.bubble.update_font_size(size_px)

    def set_window_states(self, *, weather_open: bool, answerbook_open: bool, settings_open: bool) -> None:
        self.weather_action.setChecked(weather_open)
        self.answerbook_action.setChecked(answerbook_open)
        self.settings_action.setChecked(settings_open)

    def prepare_for_exit(self) -> None:
        self._allow_close = True

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802
        if not self._is_opaque_hit(event.pos()):
            event.ignore()
            return
        self.interacted.emit()
        self.menu.exec(self._menu_anchor_pos())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self._is_opaque_hit(event.position().toPoint()):
            self._drag_active = True
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.grabMouse()
            self.interacted.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_active and event.buttons() & Qt.LeftButton:
            old_position = self.pos()
            new_position = event.globalPosition().toPoint() - self._drag_offset
            delta = new_position - old_position
            if delta.x() or delta.y():
                self.move(new_position)
                self.window_moved.emit(delta.x(), delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self._drag_active:
            self._drag_active = False
            self.releaseMouse()
            self.drag_finished.emit(self.current_position())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._drag_active:
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.movie_label = QLabel(self)
        self.movie_label.setAlignment(Qt.AlignCenter)
        self.movie_label.setStyleSheet("background-color: transparent; border: none; outline: none;")
        self.movie_label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.movie_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.movie_label)

    def _build_menu(self) -> None:
        self.menu = QMenu(self)

        interaction_menu = self.menu.addMenu(make_icon("pet"), "互动")
        interaction_menu.menuAction().setCheckable(True)
        interaction_menu.aboutToShow.connect(lambda: interaction_menu.menuAction().setChecked(True))
        interaction_menu.aboutToHide.connect(lambda: interaction_menu.menuAction().setChecked(False))
        action_labels = {
            "feed": "喂食",
            "play": "陪玩",
            "clean": "清洁",
            "rest": "休息",
        }
        action_icons = {"feed": "feed", "play": "play", "clean": "clean", "rest": "rest"}
        for action_id in ("feed", "play", "clean", "rest"):
            action = QAction(make_icon(action_icons[action_id]), action_labels[action_id], interaction_menu)
            action.triggered.connect(
                lambda checked=False, current=action_id: self.manual_action_requested.emit(current)
            )
            interaction_menu.addAction(action)

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

    def _normalize_menu_labels(self) -> None:
        root_actions = self.menu.actions()
        if root_actions and root_actions[0].menu() is not None:
            self.interaction_menu = root_actions[0].menu()
            self.interaction_menu.menuAction().setText("互动")
            self.interaction_menu.menuAction().setIcon(make_icon("pet"))

            action_specs = [
                ("喂食", "feed"),
                ("陪玩", "play"),
                ("清洁", "clean"),
                ("休息", "rest"),
            ]
            for action, (text, icon_name) in zip(self.interaction_menu.actions(), action_specs):
                action.setText(text)
                action.setIcon(make_icon(icon_name))

        self.weather_action.setText("天气")
        self.weather_action.setIcon(make_icon("weather"))
        self.answerbook_action.setText("答案之书")
        self.answerbook_action.setIcon(make_icon("answerbook"))
        self.settings_action.setText("设置")
        self.settings_action.setIcon(make_icon("settings"))

    def _load_movie(self, gif_path: Path) -> bool:
        if not gif_path.exists():
            return False

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
        self.movie_label.setMovie(movie)
        movie.start()
        self._sync_to_movie_frame()
        return True

    def _is_opaque_hit(self, widget_pos: QPoint) -> bool:
        if self.movie is None:
            return False

        label_pos = self.movie_label.mapFrom(self, widget_pos)
        if not self.movie_label.rect().contains(label_pos):
            return False

        pixmap = self.movie.currentPixmap()
        if pixmap.isNull():
            return False

        image = pixmap.toImage()
        if image.isNull():
            return False

        x = int(label_pos.x())
        y = int(label_pos.y())
        if x < 0 or y < 0 or x >= image.width() or y >= image.height():
            return False

        return image.pixelColor(x, y).alpha() > 0

    def _menu_anchor_pos(self) -> QPoint:
        self.menu.ensurePolished()
        menu_size = self.menu.sizeHint()
        screen = self.screen()
        available = screen.availableGeometry() if screen is not None else self.frameGeometry().adjusted(-9999, -9999, 9999, 9999)
        margin = 18

        anchor = self.mapToGlobal(self.rect().topRight()) + QPoint(14, 10)
        if anchor.x() + menu_size.width() > available.right() - margin:
            anchor = self.mapToGlobal(self.rect().topLeft()) - QPoint(menu_size.width() + 14, -10)

        anchor.setX(
            max(
                available.left() + margin,
                min(anchor.x(), available.right() - menu_size.width() - margin),
            )
        )
        anchor.setY(
            max(
                available.top() + margin,
                min(anchor.y(), available.bottom() - menu_size.height() - margin),
            )
        )
        return anchor

    @Slot()
    @Slot(int)
    def _sync_to_movie_frame(self, _frame_index: int = 0) -> None:
        if self.movie is None:
            return

        pixmap = self.movie.currentPixmap()
        if pixmap.isNull():
            size = self.movie.frameRect().size()
            if size.isValid():
                self.movie_label.setFixedSize(size)
                self.setFixedSize(size)
            return

        self.movie_label.setFixedSize(pixmap.size())
        self.setFixedSize(pixmap.size())
        mask = pixmap.mask()
        if not mask.isNull():
            self.setMask(mask)
        else:
            self.clearMask()


def _menu_stylesheet(size_px: int) -> str:
    return f"""
    QMenu {{
        background-color: #FAFAFA;
        border: 1px solid rgba(216, 175, 184, 0.5);
        border-radius: 8px;
        padding: 4px;
        outline: none;
        font-size: {int(size_px)}px;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    QMenu::item {{
        padding: 6px 24px 6px 12px;
        border-radius: 4px;
        background: transparent;
        color: #3E3137;
    }}
    QMenu::item:selected {{
        background-color: rgba(230, 190, 198, 0.30);
    }}
    QMenu::item:checked {{
        background-color: rgba(230, 190, 198, 0.26);
        color: #3E3137;
    }}
    QMenu::item:checked:selected {{
        background-color: rgba(230, 190, 198, 0.34);
        color: #3E3137;
    }}
    QMenu::separator {{
        height: 1px;
        margin: 4px 8px;
        background: rgba(216, 175, 184, 0.35);
    }}
    """


from ui.pet_window import PetWindow as _CanonicalPetWindow

PetWindow = _CanonicalPetWindow


def _clean_normalize_menu_labels(self: PetWindow) -> None:
    root_actions = self.menu.actions()
    if root_actions and root_actions[0].menu() is not None:
        self.interaction_menu = root_actions[0].menu()
        self.interaction_menu.menuAction().setText("互动")
        self.interaction_menu.menuAction().setIcon(make_icon("pet"))

        action_specs = [
            ("喂食", "feed"),
            ("陪玩", "play"),
            ("清洁", "clean"),
            ("休息", "rest"),
        ]
        for action, (text, icon_name) in zip(self.interaction_menu.actions(), action_specs):
            action.setText(text)
            action.setIcon(make_icon(icon_name))

    self.weather_action.setText("天气")
    self.weather_action.setIcon(make_icon("weather"))
    self.answerbook_action.setText("答案之书")
    self.answerbook_action.setIcon(make_icon("answerbook"))
    self.settings_action.setText("设置")
    self.settings_action.setIcon(make_icon("settings"))


PetWindow._normalize_menu_labels = _clean_normalize_menu_labels
