from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.app_metadata import (
    APP_DISPLAY_NAME,
    APP_RELEASES_URL,
    APP_REPOSITORY_URL,
    APP_VERSION,
    display_version,
    runtime_mode_label,
)
from services.update_service import UpdateCheckResult
from ui.dialog_shell import DialogShell
from ui.theme import Colors, Metrics, Typography, base_font_stack


def _rgba(color, alpha: int | None = None) -> str:
    resolved_alpha = color.alpha() if alpha is None else int(alpha)
    return f"rgba({color.red()},{color.green()},{color.blue()},{resolved_alpha})"


class AboutDialog(DialogShell):
    check_update_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(title="关于", icon_name="pet", parent=parent)
        self._download_url = APP_RELEASES_URL
        self.resize(430, 430)
        self.setMinimumSize(410, 400)
        self._build_ui()
        self.refresh_static_content()
        self.set_update_idle()

    def refresh_static_content(self) -> None:
        self.app_name_label.setText(APP_DISPLAY_NAME)
        self.version_value_label.setText(display_version(APP_VERSION))
        self.runtime_value_label.setText(runtime_mode_label())
        self.repo_value_label.setText(APP_REPOSITORY_URL)

    def set_update_idle(self) -> None:
        self.check_update_button.setEnabled(True)
        self.check_update_button.setText("检查更新")
        self.status_title_label.setText("尚未检查更新")
        self.status_body_label.setText("点击“检查更新”后，会去 GitHub 发布页比对远端版本。")
        self.open_update_button.setText("打开发布页")
        self.open_update_button.setVisible(True)
        self._download_url = APP_RELEASES_URL

    def set_checking_update(self) -> None:
        self.check_update_button.setEnabled(False)
        self.check_update_button.setText("检查中…")
        self.status_title_label.setText("正在检查更新")
        self.status_body_label.setText("正在连接远端发布页，请稍等一下。")

    def set_update_result(self, result: UpdateCheckResult) -> None:
        self.check_update_button.setEnabled(True)
        self.check_update_button.setText("重新检查")
        self._download_url = result.download_url or result.release_page_url or APP_RELEASES_URL
        if result.source == "unpublished":
            self.status_title_label.setText("暂未发布正式版本")
            self.status_body_label.setText(result.summary or "当前仓库还没有正式发布版本。")
            self.open_update_button.setText("打开发布页")
            self.open_update_button.setVisible(True)
            return
        if result.update_available:
            self.status_title_label.setText(f"发现新版本 {display_version(result.latest_version)}")
            body = result.summary or "远端发布页已有更新。"
            if result.published_at:
                body = f"{body}\n发布时间：{result.published_at}"
            self.status_body_label.setText(body)
            self.open_update_button.setText("打开下载页")
        else:
            self.status_title_label.setText(f"当前已是最新版本 {display_version(result.current_version)}")
            self.status_body_label.setText("本地版本已与远端最新版本一致。")
            self.open_update_button.setText("查看发布页")
        self.open_update_button.setVisible(True)

    def set_update_error(self, message: str) -> None:
        self.check_update_button.setEnabled(True)
        self.check_update_button.setText("重新检查")
        self.status_title_label.setText("检查更新失败")
        self.status_body_label.setText(message.strip() or "暂时无法连接远端发布页。")
        self.open_update_button.setText("打开发布页")
        self.open_update_button.setVisible(True)
        self._download_url = APP_RELEASES_URL

    def _build_ui(self) -> None:
        self.body_layout.setContentsMargins(Metrics.PADDING_LG, Metrics.PADDING_LG, Metrics.PADDING_LG, Metrics.PADDING_LG)
        self.body_layout.setSpacing(12)

        hero = self._card(background=_rgba(Colors.BLUSH_SOFT, 245), border_alpha=180, radius=Metrics.RADIUS_LG)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 14, 16, 14)
        hero_layout.setSpacing(6)

        eyebrow = QLabel("Version", hero)
        eyebrow.setStyleSheet(
            f"color: {Colors.ROSE_DARK.name()}; font-size: 10px; font-weight: 600; letter-spacing: 1px; font-family: {base_font_stack(include_emoji=True)};"
        )
        self.app_name_label = QLabel(APP_DISPLAY_NAME, hero)
        self.app_name_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: {Typography.SIZE_H1 + 1}px; font-weight: 700; font-family: {base_font_stack(include_emoji=True)};"
        )
        subtitle = QLabel("查看当前版本、更新状态和项目主页。", hero)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()}; font-size: 12px; font-family: {base_font_stack(include_emoji=True)};"
        )
        hero_layout.addWidget(eyebrow)
        hero_layout.addWidget(self.app_name_label)
        hero_layout.addWidget(subtitle)
        self.body_layout.addWidget(hero)

        detail_card = self._card(background=_rgba(Colors.BG_CARD, 252), border_alpha=78, radius=Metrics.RADIUS_MD)
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(16, 14, 16, 14)
        detail_layout.setSpacing(10)
        detail_layout.addWidget(self._section_title("版本信息"))
        detail_layout.addLayout(self._info_row("当前版本", value_attr="version_value_label"))
        detail_layout.addLayout(self._info_row("运行方式", value_attr="runtime_value_label"))
        detail_layout.addLayout(self._info_row("项目主页", value_attr="repo_value_label"))
        self.body_layout.addWidget(detail_card)

        update_card = self._card(background=_rgba(Colors.BG_INPUT, 252), border_alpha=92, radius=Metrics.RADIUS_MD)
        update_layout = QVBoxLayout(update_card)
        update_layout.setContentsMargins(16, 14, 16, 16)
        update_layout.setSpacing(10)
        update_layout.addWidget(self._section_title("更新状态"))

        self.status_title_label = QLabel("", update_card)
        self.status_title_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: 13px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
        )
        self.status_body_label = QLabel("", update_card)
        self.status_body_label.setWordWrap(True)
        self.status_body_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()}; font-size: 12px; line-height: 1.4; font-family: {base_font_stack(include_emoji=True)};"
        )

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self.check_update_button = QPushButton("检查更新", update_card)
        self.check_update_button.setCursor(Qt.PointingHandCursor)
        self.check_update_button.setStyleSheet(_primary_button_stylesheet())
        self.check_update_button.clicked.connect(self.check_update_requested.emit)

        self.open_update_button = QPushButton("打开发布页", update_card)
        self.open_update_button.setCursor(Qt.PointingHandCursor)
        self.open_update_button.setStyleSheet(_secondary_button_stylesheet())
        self.open_update_button.clicked.connect(self._open_update_page)

        self.open_homepage_button = QPushButton("项目主页", update_card)
        self.open_homepage_button.setCursor(Qt.PointingHandCursor)
        self.open_homepage_button.setStyleSheet(_secondary_button_stylesheet())
        self.open_homepage_button.clicked.connect(self._open_homepage)

        button_row.addWidget(self.check_update_button, 1)
        button_row.addWidget(self.open_update_button, 1)
        button_row.addWidget(self.open_homepage_button, 1)

        update_layout.addWidget(self.status_title_label)
        update_layout.addWidget(self.status_body_label)
        update_layout.addLayout(button_row)
        self.body_layout.addWidget(update_card)
        self.body_layout.addStretch(1)

    def _info_row(self, label_text: str, *, value_attr: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        label = QLabel(label_text, self.body)
        label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()}; font-size: 11px; font-family: {base_font_stack(include_emoji=True)};"
        )
        value_label = QLabel("", self.body)
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        value_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: 12px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
        )
        setattr(self, value_attr, value_label)
        row.addWidget(label, 0)
        row.addWidget(value_label, 1)
        return row

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: 12px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
        )
        return label

    @staticmethod
    def _card(*, background: str, border_alpha: int, radius: int) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            "QWidget {"
            f"background: {background};"
            f"border: 1px solid {_rgba(Colors.BORDER_DEFAULT, int(border_alpha))};"
            f"border-radius: {int(radius)}px;"
            "outline: none;"
            "}"
        )
        return card

    def _open_homepage(self) -> None:
        QDesktopServices.openUrl(QUrl(APP_REPOSITORY_URL))

    def _open_update_page(self) -> None:
        QDesktopServices.openUrl(QUrl(self._download_url or APP_RELEASES_URL))


def _primary_button_stylesheet() -> str:
    return f"""
    QPushButton {{
        background: {Colors.PRIMARY.name()};
        border: 1px solid {_rgba(Colors.PRIMARY, 150)};
        border-radius: 10px;
        color: {Colors.TEXT_ON_PRIMARY.name()};
        padding: 10px 14px;
        min-height: 40px;
        max-height: 40px;
        font-size: 13px;
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
        border-color: {_rgba(Colors.PRIMARY, 120)};
        color: {_rgba(Colors.TEXT_ON_PRIMARY, 210)};
    }}
    """


def _secondary_button_stylesheet() -> str:
    return f"""
    QPushButton {{
        background: {_rgba(Colors.BG_CARD, 250)};
        border: 1px solid {_rgba(Colors.BORDER_DEFAULT, 120)};
        border-radius: 10px;
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
        border-color: {_rgba(Colors.PRIMARY, 140)};
    }}
    QPushButton:pressed {{
        background: {_rgba(Colors.PRIMARY, 45)};
    }}
    """
