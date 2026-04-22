from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from data.manual_actions import MANUAL_ACTION_SPECS
from data.pet_models import GrowthStage, PetStatus
from ui.dialog_shell import DialogShell
from ui.icons import make_icon, make_pixmap
from ui.theme import (
    ACCENT,
    Colors,
    Metrics,
    TEXT_MUTED,
    TEXT_PRIMARY,
    Typography,
    base_font_stack,
    pill_stylesheet,
    progress_bar_stylesheet,
    soft_button_stylesheet,
    soft_card_stylesheet,
)


class _ArcValueWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = 0
        self.setFixedSize(40, 40)

    def set_value(self, value: int) -> None:
        self._value = max(0, min(100, int(value)))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(5, 5, 30, 30)
        base_pen = QPen(QColor(Colors.BORDER_DEFAULT.red(), Colors.BORDER_DEFAULT.green(), Colors.BORDER_DEFAULT.blue(), 52), 5)
        base_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(base_pen)
        painter.drawArc(rect, 210 * 16, -240 * 16)

        if self._value >= 70:
            color = Colors.SUCCESS
        elif self._value >= 35:
            color = Colors.WARNING
        else:
            color = Colors.DANGER
        value_pen = QPen(color, 5)
        value_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(value_pen)
        painter.drawArc(rect, 210 * 16, int(-240 * self._value / 100) * 16)

        painter.setPen(QColor(TEXT_PRIMARY))
        painter.setFont(Typography.font(10, Typography.WEIGHT_MEDIUM))
        painter.drawText(self.rect(), Qt.AlignCenter, str(self._value))
        super().paintEvent(event)


class StatusWindow(DialogShell):
    action_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(title="状态面板", icon_name="status", parent=parent)
        self.resize(430, 500)
        self._build_ui()

    def set_pet_preview(self, pixmap: QPixmap | None) -> None:
        preview = pixmap if isinstance(pixmap, QPixmap) and not pixmap.isNull() else make_pixmap("pet", size=48)
        scaled = preview.scaled(48, 48, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        circular = QPixmap(48, 48)
        circular.fill(Qt.transparent)
        painter = QPainter(circular)
        painter.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath()
        clip.addEllipse(0, 0, 48, 48)
        painter.setClipPath(clip)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        self.preview_label.setPixmap(circular)

    def update_status(self, status: PetStatus) -> None:
        self.pet_name_label.setText(status.pet_name)
        self.stage_pill.setText(status.growth_stage.label)
        current_exp, stage_limit = _stage_progress(status.growth_stage, status.growth_exp)
        self.exp_progress.setMaximum(stage_limit)
        self.exp_progress.setValue(current_exp)
        self.exp_value.setText(f"{current_exp} / {stage_limit}")
        self.favorability_value.setText(f"{status.favorability}/100")
        self.hunger_arc.set_value(status.hunger)
        self.mood_arc.set_value(status.mood)
        self.energy_arc.set_value(status.energy)
        self.clean_arc.set_value(status.cleanliness)

    def _build_ui(self) -> None:
        top_card = _card()
        top_layout = QVBoxLayout(top_card)
        top_layout.setContentsMargins(16, 16, 16, 16)
        top_layout.setSpacing(12)

        identity_row = QHBoxLayout()
        identity_row.setSpacing(12)

        self.preview_label = QLabel(top_card)
        self.preview_label.setFixedSize(48, 48)
        self.preview_label.setStyleSheet("background: transparent;")
        self.set_pet_preview(None)

        name_wrap = QVBoxLayout()
        name_wrap.setSpacing(3)
        self.pet_name_label = QLabel("Momo", top_card)
        self.pet_name_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 18px; font-weight: 700; font-family: {base_font_stack(include_emoji=True)};"
        )
        self.stage_pill = QLabel("幼年期", top_card)
        self.stage_pill.setStyleSheet(
            f"QLabel {{{pill_stylesheet()} font-size: 11px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};}}"
        )
        name_wrap.addWidget(self.pet_name_label)
        name_wrap.addWidget(self.stage_pill, 0, Qt.AlignLeft)

        identity_row.addWidget(self.preview_label)
        identity_row.addLayout(name_wrap, 1)
        top_layout.addLayout(identity_row)

        progress_title = QLabel("成长经验", top_card)
        progress_title.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-family: {base_font_stack(include_emoji=True)};"
        )
        top_layout.addWidget(progress_title)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        self.exp_progress = QProgressBar(top_card)
        self.exp_progress.setTextVisible(False)
        self.exp_progress.setStyleSheet(progress_bar_stylesheet())
        self.exp_value = QLabel("0 / 100", top_card)
        self.exp_value.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-family: {base_font_stack(include_emoji=True)};"
        )
        progress_row.addWidget(self.exp_progress, 1)
        progress_row.addWidget(self.exp_value)
        top_layout.addLayout(progress_row)

        favor_row = QHBoxLayout()
        favor_label = QLabel("亲密度", top_card)
        favor_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-family: {base_font_stack(include_emoji=True)};"
        )
        self.favorability_value = QLabel("20/100", top_card)
        self.favorability_value.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
        )
        favor_row.addWidget(favor_label)
        favor_row.addStretch(1)
        favor_row.addWidget(self.favorability_value)
        top_layout.addLayout(favor_row)

        stat_card = _card()
        stat_layout = QVBoxLayout(stat_card)
        stat_layout.setContentsMargins(16, 16, 16, 16)
        stat_layout.setSpacing(12)
        stat_layout.addWidget(_section_title("当前状态"))
        self.hunger_arc = self._stat_row(stat_layout, "feed", "饱食度")
        self.mood_arc = self._stat_row(stat_layout, "pet", "亲密度")
        self.clean_arc = self._stat_row(stat_layout, "clean", "清洁度")
        self.energy_arc = self._stat_row(stat_layout, "rest", "精力")

        action_card = _card()
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(16, 16, 16, 16)
        action_layout.setSpacing(12)
        action_layout.addWidget(_section_title("互动"))
        action_grid = QGridLayout()
        action_grid.setSpacing(10)
        for index, (action_id, label, icon_name) in enumerate(
            (("feed", "喂食", "feed"), ("play", "陪玩", "play"), ("clean", "清洁", "clean"), ("rest", "休息", "rest"))
        ):
            button = QPushButton(label, action_card)
            button.setCursor(Qt.PointingHandCursor)
            button.setIcon(make_icon(icon_name, size=16))
            button.setStyleSheet(soft_button_stylesheet(primary=index % 2 == 0))
            button.clicked.connect(lambda checked=False, current=action_id: self.action_requested.emit(current))
            action_grid.addWidget(button, 0, index)
        action_layout.addLayout(action_grid)

        self.body_layout.addWidget(top_card)
        self.body_layout.addWidget(stat_card)
        self.body_layout.addWidget(action_card)

    def _stat_row(self, layout: QVBoxLayout, icon_name: str, label_text: str) -> _ArcValueWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        icon_label = QLabel(row)
        icon_label.setPixmap(make_pixmap(icon_name, size=16))
        text_label = QLabel(label_text, row)
        text_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-family: {base_font_stack(include_emoji=True)};"
        )
        arc = _ArcValueWidget(row)
        row_layout.addWidget(icon_label)
        row_layout.addWidget(text_label)
        row_layout.addStretch(1)
        row_layout.addWidget(arc)
        layout.addWidget(row)
        return arc


def _card() -> QWidget:
    card = QWidget()
    card.setStyleSheet(f"QWidget {{{soft_card_stylesheet()}}}")
    return card


def _section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(
        f"color: {ACCENT}; font-size: 11px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
    )
    return label


def _stage_progress(stage: GrowthStage, total_exp: int) -> tuple[int, int]:
    bounds = {
        GrowthStage.BABY: (0, 100),
        GrowthStage.CHILD: (100, 300),
        GrowthStage.TEEN: (300, 600),
        GrowthStage.ADULT: (600, 1000),
    }
    start, end = bounds[stage]
    return max(0, total_exp - start), max(1, end - start)
