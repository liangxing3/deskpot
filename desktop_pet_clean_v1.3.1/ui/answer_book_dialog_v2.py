from __future__ import annotations

import random

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from data.models import AnswerBookResult
from ui.dialog_shell import DialogShell
from ui.theme import Colors, Metrics, Typography, base_font_stack, line_edit_stylesheet


def _rgba(color, alpha: int | None = None) -> str:
    resolved_alpha = color.alpha() if alpha is None else int(alpha)
    return f"rgba({color.red()},{color.green()},{color.blue()},{resolved_alpha})"


class AnswerBookDialogV2(DialogShell):
    submit_requested = Signal(str)

    QUICK_QUESTIONS = (
        "我今天适合开始新的计划吗？",
        "我现在该主动迈出下一步吗？",
        "这件事值得我继续投入吗？",
        "我今天更适合推进还是观望？",
        "我该先处理眼前这件事吗？",
        "这个决定现在做合适吗？",
    )
    QUICK_QUESTIONS_VISIBLE = 2

    def __init__(self, parent=None) -> None:
        super().__init__(title="答案之书", icon_name="answerbook", parent=parent)
        self._loading = False
        self._loading_step = 0
        self._loading_base = "正在翻开答案之书"
        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(220)
        self._loading_timer.timeout.connect(self._tick_loading_state)

        self.resize(440, 560)
        self.setMinimumSize(420, 520)

        self._build_ui()
        self._wire_signals()
        self._update_action_state()

    def focus_input(self) -> None:
        self.question_input.setFocus(Qt.OtherFocusReason)
        cursor = self.question_input.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.question_input.setTextCursor(cursor)

    def set_loading(self, question: str) -> None:
        self._loading = True
        self.question_input.setPlainText(question.strip())
        self.ask_button.setText("处理中…")
        self._set_result(answer_text=self._loading_base, hint_text="小狗正在认真翻书", source_text="处理中")
        self._loading_step = 0
        self._loading_timer.start()
        self._update_action_state()

    def set_result(self, result: AnswerBookResult) -> None:
        self._loading = False
        self._loading_timer.stop()
        self.ask_button.setText("翻开答案")
        self._set_result(
            answer_text=result.answer.strip() or "这次没有翻到明确答案。",
            hint_text="仅供参考，开心最重要",
            source_text=_source_text(result.source),
        )
        self._update_action_state()

    def set_error(self, message: str) -> None:
        self._loading = False
        self._loading_timer.stop()
        self.ask_button.setText("翻开答案")
        self._set_result(
            answer_text=message.strip() or "这次没有翻到明确答案。",
            hint_text="先别着急，换个问法再试试",
            source_text="暂时不可用",
        )
        self._update_action_state()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.question_input and isinstance(event, QKeyEvent):
            if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ControlModifier:
                    self._submit_question()
                    event.accept()
                    return True
        return super().eventFilter(watched, event)

    def _build_ui(self) -> None:
        self.body_layout.setContentsMargins(10, 10, 10, 10)
        self.body_layout.setSpacing(0)

        self.content_panel = self._card(
            background=_rgba(Colors.BG_CARD, 252),
            border_alpha=104,
            radius=Metrics.RADIUS_LG,
        )
        content_layout = QVBoxLayout(self.content_panel)
        content_layout.setContentsMargins(14, 14, 14, 14)
        content_layout.setSpacing(12)

        hero = self._card(background=_rgba(Colors.BLUSH_SOFT, 245), border_alpha=180, radius=Metrics.RADIUS_LG)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(14, 12, 14, 12)
        hero_layout.setSpacing(4)
        eyebrow = QLabel("每日一问", hero)
        eyebrow.setStyleSheet(
            f"color: {Colors.ROSE_DARK.name()};"
            "font-size: 10px;"
            "font-weight: 600;"
            "letter-spacing: 1px;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        title = QLabel("把问题交给小狗", hero)
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()};"
            f"font-size: {Typography.SIZE_H1}px;"
            "font-weight: 600;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        subtitle = QLabel("建议用一句话问清楚：是 / 否 / 下一步 / 要不要继续。", hero)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()};"
            "font-size: 12px;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        hero_layout.addWidget(eyebrow)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        content_layout.addWidget(hero)

        content_layout.addWidget(self._build_question_card())
        content_layout.addWidget(self._build_quick_card())
        content_layout.addLayout(self._build_actions_row())
        content_layout.addWidget(self._build_answer_card(), 1)
        self.body_layout.addWidget(self.content_panel, 1)

    def _build_question_card(self) -> QWidget:
        card = self._card(background=_rgba(Colors.BG_CARD, 252), border_alpha=78, radius=Metrics.RADIUS_MD)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        label_row = QHBoxLayout()
        label_row.setContentsMargins(0, 0, 0, 0)
        label_row.setSpacing(8)
        label = QLabel("输入问题", card)
        label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()};"
            "font-size: 12px;"
            "font-weight: 600;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        hint = QLabel("Ctrl + Enter 提交", card)
        hint.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hint.setStyleSheet(
            f"color: {_rgba(Colors.TEXT_SECONDARY, 180)};"
            "font-size: 11px;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        label_row.addWidget(label, 1)
        label_row.addWidget(hint, 0)
        layout.addLayout(label_row)

        self.question_input = QTextEdit(card)
        self.question_input.setPlaceholderText("比如：我现在要不要主动去沟通？")
        self.question_input.setMinimumHeight(78)
        self.question_input.setMaximumHeight(136)
        self.question_input.setStyleSheet(_question_input_stylesheet())
        self.question_input.installEventFilter(self)
        layout.addWidget(self.question_input)
        return card

    def _build_quick_card(self) -> QWidget:
        card = self._card(background=_rgba(Colors.BG_CARD, 252), border_alpha=78, radius=Metrics.RADIUS_MD)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        label = QLabel("快速提问", card)
        label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()};"
            "font-size: 12px;"
            "font-weight: 600;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        layout.addWidget(label)

        chips = QWidget(card)
        grid = QGridLayout(chips)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        self.quick_question_buttons: list[QPushButton] = []
        for index, text in enumerate(self.QUICK_QUESTIONS[: self.QUICK_QUESTIONS_VISIBLE]):
            btn = QPushButton(text, chips)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_chip_stylesheet())
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _checked=False, question=text: self._fill_quick_question(question))
            self.quick_question_buttons.append(btn)
            grid.addWidget(btn, index // 2, index % 2)

        layout.addWidget(chips)
        return card

    def _build_actions_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.random_button = QPushButton("随机", self.content_panel)
        self.random_button.setCursor(Qt.PointingHandCursor)
        self.random_button.setStyleSheet(_secondary_button_stylesheet())

        self.clear_button = QPushButton("清空", self.content_panel)
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setStyleSheet(_secondary_button_stylesheet())

        self.ask_button = QPushButton("翻开答案", self.content_panel)
        self.ask_button.setCursor(Qt.PointingHandCursor)
        self.ask_button.setStyleSheet(_primary_button_stylesheet())

        row.addWidget(self.random_button, 0)
        row.addWidget(self.clear_button, 0)
        row.addStretch(1)
        row.addWidget(self.ask_button, 1)
        return row

    def _build_answer_card(self) -> QWidget:
        card = self._card(background=_rgba(Colors.BG_INPUT, 252), border_alpha=78, radius=Metrics.RADIUS_LG)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel("这次的答案", card)
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()};"
            "font-size: 12px;"
            "font-weight: 600;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )

        self.source_label = QLabel("等待提问", card)
        self.source_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.source_label.setStyleSheet(
            f"color: {_rgba(Colors.TEXT_SECONDARY, 200)};"
            "font-size: 11px;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )

        header.addWidget(title, 1)
        header.addWidget(self.source_label, 0)
        layout.addLayout(header)

        self.result_label = QLabel("写下问题，翻开就会出现答案。", card)
        self.result_label.setWordWrap(True)
        self.result_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.result_label.setMinimumHeight(156)
        self.result_label.setStyleSheet(_answer_surface_stylesheet())

        self.hint_label = QLabel("仅供参考，开心最重要", card)
        self.hint_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.hint_label.setStyleSheet(
            f"color: {_rgba(Colors.TEXT_SECONDARY, 190)};"
            "font-size: 11px;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )

        layout.addWidget(self.result_label, 1)
        layout.addWidget(self.hint_label)
        return card

    def _wire_signals(self) -> None:
        self.question_input.textChanged.connect(self._update_action_state)
        self.ask_button.clicked.connect(self._submit_question)
        self.clear_button.clicked.connect(self._clear_question)
        self.random_button.clicked.connect(self._fill_random_question)

    def _submit_question(self) -> None:
        question = self.question_input.toPlainText().strip()
        if self._loading or not question:
            return
        self.submit_requested.emit(question)

    def _set_result(self, *, answer_text: str, hint_text: str, source_text: str) -> None:
        self.result_label.setText(answer_text.strip() or "这次没有翻到明确答案。")
        self.hint_label.setText(hint_text)
        self.source_label.setText(source_text)

    def _update_action_state(self) -> None:
        has_text = bool(self.question_input.toPlainText().strip())
        self.ask_button.setEnabled(has_text and not self._loading)
        self.clear_button.setEnabled(has_text and not self._loading)
        self.random_button.setEnabled(not self._loading)
        self.question_input.setReadOnly(self._loading)
        for button in self.quick_question_buttons:
            button.setEnabled(not self._loading)

    def _fill_quick_question(self, question: str) -> None:
        if self._loading:
            return
        self.question_input.setPlainText(question)
        self.focus_input()

    def _fill_random_question(self) -> None:
        self._fill_quick_question(random.choice(self.QUICK_QUESTIONS))

    def _clear_question(self) -> None:
        if self._loading:
            return
        self.question_input.clear()
        self.focus_input()

    def _tick_loading_state(self) -> None:
        if not self._loading:
            self._loading_timer.stop()
            return
        self._loading_step = (self._loading_step + 1) % 3
        dots = "·" * (self._loading_step + 1)
        self.result_label.setText(f"{self._loading_base}{dots}")

    @staticmethod
    def _card(*, background: str, border_alpha: int = 90, radius: int = Metrics.RADIUS_MD) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            "QWidget {"
            f"background: {background};"
            "border: none;"
            f"border-radius: {int(radius)}px;"
            "outline: none;"
            "}"
        )
        return card


def _question_input_stylesheet() -> str:
    return (
        line_edit_stylesheet()
        + f"""
        QTextEdit {{
            border-radius: {Metrics.RADIUS_MD}px;
            padding: 11px 12px;
            selection-background-color: {_rgba(Colors.PRIMARY, 85)};
        }}
        QTextEdit:focus {{
            border: none;
            background: {_rgba(Colors.BLUSH_SOFT, 205)};
        }}
        """
    )


def _chip_stylesheet() -> str:
    return f"""
    QPushButton {{
        background: {_rgba(Colors.PRIMARY, 14)};
        border: none;
        border-radius: 15px;
        outline: none;
        color: {Colors.TEXT_PRIMARY.name()};
        padding: 6px 10px;
        text-align: left;
        font-size: 12px;
        font-weight: 500;
        min-height: 30px;
        max-height: 30px;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    QPushButton:hover {{
        background: {_rgba(Colors.PRIMARY, 22)};
    }}
    QPushButton:pressed {{
        background: {_rgba(Colors.PRIMARY, 32)};
    }}
    QPushButton:disabled {{
        color: {_rgba(Colors.TEXT_SECONDARY, 150)};
        background: {_rgba(Colors.BORDER_DEFAULT, 30)};
        border: none;
    }}
    """


def _primary_button_stylesheet() -> str:
    return f"""
    QPushButton {{
        background: {Colors.PRIMARY.name()};
        border: none;
        border-radius: 10px;
        outline: none;
        color: {Colors.TEXT_ON_PRIMARY.name()};
        padding: 10px 14px;
        min-height: 40px;
        max-height: 40px;
        font-size: 14px;
        font-weight: 600;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    QPushButton:hover {{
        background: {Colors.PRIMARY_HOVER.name()};
    }}
    QPushButton:pressed {{
        background: {Colors.PRIMARY_PRESSED.name()};
    }}
    QPushButton:disabled {{
        background: {_rgba(Colors.PRIMARY, 140)};
        border: none;
        color: {_rgba(Colors.TEXT_ON_PRIMARY, 210)};
    }}
    """


def _secondary_button_stylesheet() -> str:
    return f"""
    QPushButton {{
        background: {_rgba(Colors.BG_CARD, 250)};
        border: none;
        border-radius: 10px;
        outline: none;
        color: {Colors.TEXT_PRIMARY.name()};
        padding: 10px 14px;
        min-height: 40px;
        max-height: 40px;
        font-size: 13px;
        font-weight: 600;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    QPushButton:hover {{
        background: {_rgba(Colors.PRIMARY, 24)};
    }}
    QPushButton:pressed {{
        background: {_rgba(Colors.PRIMARY, 45)};
    }}
    QPushButton:disabled {{
        color: {_rgba(Colors.TEXT_SECONDARY, 150)};
        background: {_rgba(Colors.BORDER_DEFAULT, 35)};
        border: none;
    }}
    """


def _answer_surface_stylesheet() -> str:
    return f"""
    QLabel {{
        background: {_rgba(Colors.BLUSH_SOFT, 235)};
        border: none;
        border-radius: {Metrics.RADIUS_MD}px;
        padding: 18px 16px;
        color: {Colors.TEXT_PRIMARY.name()};
        font-size: 18px;
        font-weight: 700;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    """


def _source_text(source: str) -> str:
    mapping = {
        "remote": "在线答案",
        "cache": "缓存答案",
        "fallback": "本地兜底",
    }
    return mapping.get(str(source).strip().lower(), "答案")

