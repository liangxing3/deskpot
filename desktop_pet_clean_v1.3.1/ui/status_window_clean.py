from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QVBoxLayout, QWidget

from data.manual_actions import MANUAL_ACTION_SPECS
from data.pet_models import PetStatus
from ui.dialog_shell import DialogShell
from ui.theme import ACCENT, TEXT_MUTED, TEXT_PRIMARY, base_font_stack, soft_button_stylesheet, soft_card_stylesheet


class StatusWindow(DialogShell):
    action_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(title="状态面板", icon_name="status", parent=parent)
        self.resize(420, 460)
        self._build_ui()

    def update_status(self, status: PetStatus) -> None:
        self.pet_name_value.setText(status.pet_name)
        self.stage_value.setText(status.growth_stage.label)
        self.exp_value.setText(str(status.growth_exp))
        self.favorability_value.setText(f"{status.favorability}/100")
        self.hunger_bar.setValue(status.hunger)
        self.mood_bar.setValue(status.mood)
        self.energy_bar.setValue(status.energy)
        self.cleanliness_bar.setValue(status.cleanliness)

    def _build_ui(self) -> None:
        summary_card = self._card()
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        summary_layout.setSpacing(8)
        summary_layout.addWidget(self._section_title("成长档案"))
        self.pet_name_value = self._summary_row(summary_layout, "宠物名称")
        self.stage_value = self._summary_row(summary_layout, "成长阶段")
        self.exp_value = self._summary_row(summary_layout, "成长经验")
        self.favorability_value = self._summary_row(summary_layout, "亲密度")

        vitals_card = self._card()
        vitals_layout = QVBoxLayout(vitals_card)
        vitals_layout.setContentsMargins(12, 12, 12, 12)
        vitals_layout.setSpacing(9)
        vitals_layout.addWidget(self._section_title("当前状态"))
        self.hunger_bar = self._progress_row(vitals_layout, "饱腹")
        self.mood_bar = self._progress_row(vitals_layout, "心情")
        self.energy_bar = self._progress_row(vitals_layout, "精力")
        self.cleanliness_bar = self._progress_row(vitals_layout, "清洁")

        action_card = self._card()
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(12, 12, 12, 12)
        action_layout.setSpacing(10)
        action_layout.addWidget(self._section_title("互动动作"))

        primary_grid = QGridLayout()
        primary_grid.setSpacing(8)
        for index, action_id in enumerate(("feed", "play", "clean", "rest")):
            button = self._action_button(action_id, primary=True)
            primary_grid.addWidget(button, index // 2, index % 2)
        action_layout.addLayout(primary_grid)

        extra_grid = QGridLayout()
        extra_grid.setSpacing(8)
        extras = [action_id for action_id in MANUAL_ACTION_SPECS if action_id not in {"feed", "play", "clean", "rest"}]
        for index, action_id in enumerate(extras):
            button = self._action_button(action_id, primary=False)
            extra_grid.addWidget(button, index // 3, index % 3)
        action_layout.addLayout(extra_grid)

        self.body_layout.addWidget(summary_card)
        self.body_layout.addWidget(vitals_card)
        self.body_layout.addWidget(action_card)

    @staticmethod
    def _card() -> QWidget:
        card = QWidget()
        card.setStyleSheet(f"QWidget {{{soft_card_stylesheet()}}}")
        return card

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {ACCENT}; font-size: 11px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
        )
        return label

    @staticmethod
    def _summary_row(layout: QVBoxLayout, label_text: str) -> QLabel:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        label = QLabel(label_text, row)
        label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-family: {base_font_stack(include_emoji=True)};"
        )
        value = QLabel("-", row)
        value.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 12px; font-weight: 500; font-family: {base_font_stack(include_emoji=True)};"
        )
        row_layout.addWidget(label)
        row_layout.addStretch(1)
        row_layout.addWidget(value)
        layout.addWidget(row)
        return value

    @staticmethod
    def _progress_row(layout: QVBoxLayout, label_text: str) -> QProgressBar:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        label = QLabel(label_text, row)
        label.setFixedWidth(50)
        label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 11px; font-family: {base_font_stack(include_emoji=True)};"
        )
        bar = QProgressBar(row)
        bar.setRange(0, 100)
        bar.setTextVisible(True)
        bar.setFixedHeight(16)
        bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid rgba(205, 162, 180, 0.30);
                border-radius: 8px;
                background: rgba(255, 244, 248, 0.96);
                text-align: center;
                color: {TEXT_PRIMARY};
                font-size: 10px;
            }}
            QProgressBar::chunk {{
                border-radius: 7px;
                background: rgba(192, 88, 120, 0.78);
            }}
            """
        )
        row_layout.addWidget(label)
        row_layout.addWidget(bar, 1)
        layout.addWidget(row)
        return bar

    def _action_button(self, action_id: str, *, primary: bool) -> QPushButton:
        spec = MANUAL_ACTION_SPECS[action_id]
        button = QPushButton(spec.label)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(soft_button_stylesheet(primary=primary))
        button.clicked.connect(lambda checked=False, current=action_id: self.action_requested.emit(current))
        return button


from ui.status_window import StatusWindow as _CanonicalStatusWindow

StatusWindow = _CanonicalStatusWindow
