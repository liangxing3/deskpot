from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from data.pet_models import PetStatus
from utils.font_loader import ui_font_stack


class PetStatusPanel(QDialog):
    action_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("宠物状态")
        self.setModal(False)
        self.resize(420, 450)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setStyleSheet(
            f"""
            QDialog {{
                background: transparent;
                font-family: {ui_font_stack(include_emoji=True)};
            }}
            QGroupBox {{
                border: none;
                margin-top: 20px;
                background: transparent;
                font-weight: bold;
                color: #FF6B9D;
                font-size: 18px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 0px;
                padding: 0 8px;
                background: transparent;
            }}
            QLabel {{
                color: #666666;
                font-size: 17px;
                font-weight: 500;
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FF6B9D,
                    stop:1 #FF8EAF);
                color: white;
                border-radius: 12px;
                padding: 18px 20px;
                font-size: 17px;
                font-weight: bold;
                border: none;
                min-height: 55px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FF8EAF,
                    stop:1 #FF9A9E);
            }}
            QPushButton:pressed {{
                background: #FF9A9E;
                padding-top: 20px;
                padding-bottom: 14px;
            }}
            QProgressBar {{
                border: 1px solid #FFE4E1;
                border-radius: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFF0F5,
                    stop:1 #FFE8EC);
                text-align: center;
                color: #5A5A5A;
                font-size: 13px;
                height: 22px;
                font-weight: 600;
            }}
            QProgressBar::chunk {{
                border-radius: 7px;
            }}
            """
        )

        self.pet_name_label = QLabel()
        self.stage_label = QLabel()
        self.exp_label = QLabel()
        self.favorability_label = QLabel()

        summary_box = QGroupBox("📊 成长档案")
        summary_form = QFormLayout(summary_box)
        summary_form.addRow("📌 称呼:", self.pet_name_label)
        summary_form.addRow("🌱 阶段:", self.stage_label)
        summary_form.addRow("✨ 经验:", self.exp_label)
        summary_form.addRow("💖 羁绊:", self.favorability_label)

        status_box = QGroupBox("🧬 生理指标")
        status_layout = QVBoxLayout(status_box)
        status_layout.setSpacing(12)
        self.hunger_bar = self._build_bar(status_layout, "🍖 饱腹", "#FFC857")
        self.mood_bar = self._build_bar(status_layout, "🎵 心情", "#FF9A9E")
        self.energy_bar = self._build_bar(status_layout, "⚡ 精力", "#A1C4FD")
        self.cleanliness_bar = self._build_bar(status_layout, "✨ 清洁", "#A8E6CF")

        action_box = QGroupBox("🎮 互动动作")
        action_grid = QGridLayout(action_box)
        action_grid.setSpacing(12)
        action_grid.setContentsMargins(10, 20, 10, 10)
        actions = (
            ("feed", "🍖 喂食"),
            ("play", "🧶 陪玩"),
            ("clean", "🛁 洗澡"),
            ("rest", "💤 休息"),
            ("petting", "🐾 抚摸"),
            ("pat", "🤏 拍拍"),
        )
        for index, (action_id, label) in enumerate(actions):
            button = QPushButton(label)
            button.clicked.connect(
                lambda checked=False, current_action=action_id: self.action_requested.emit(
                    current_action
                )
            )
            action_grid.addWidget(button, index // 3, index % 3)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.hide)
        close_row.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(summary_box)
        layout.addWidget(status_box)
        layout.addWidget(action_box)
        layout.addLayout(close_row)

    def update_status(self, status: PetStatus) -> None:
        self.pet_name_label.setText(status.pet_name)
        self.stage_label.setText(status.growth_stage.label)
        current_exp, stage_goal = self._stage_progress(status)
        self.exp_label.setText(f"{current_exp} / {stage_goal}")
        self.favorability_label.setText(f"{status.favorability} / 100")
        self.hunger_bar.setValue(status.hunger)
        self.mood_bar.setValue(status.mood)
        self.energy_bar.setValue(status.energy)
        self.cleanliness_bar.setValue(status.cleanliness)

    def _build_bar(self, container: QVBoxLayout, label: str, color_hex: str) -> QProgressBar:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        caption = QLabel(label)
        caption.setStyleSheet(
            f'color: #FF6B9D; font-size: 12px; font-weight: 600; font-family: {ui_font_stack()};'
        )
        caption.setFixedWidth(70)
        
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setTextVisible(True)
        bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid #FFE4E1;
                border-radius: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFF0F5,
                    stop:1 #FFE8EC);
                text-align: center;
                color: #5A5A5A;
                font-size: 11px;
                height: 20px;
                font-weight: 600;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color_hex},
                    stop:1 {color_hex}DD);
                border-radius: 7px;
            }}
            """
        )
        
        layout.addWidget(caption)
        layout.addWidget(bar, 1)
        container.addWidget(row)
        return bar

    @staticmethod
    def _stage_progress(status: PetStatus) -> tuple[int, int]:
        if status.growth_exp < 100:
            return status.growth_exp, 100
        if status.growth_exp < 300:
            return status.growth_exp - 100, 200
        if status.growth_exp < 600:
            return status.growth_exp - 300, 300
        return 600, 600