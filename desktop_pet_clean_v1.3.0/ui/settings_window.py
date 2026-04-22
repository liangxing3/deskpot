from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.app_metadata import APP_VERSION, display_version
from data.models import AppConfig
from ui.dialog_shell import DialogShell
from ui.theme import (
    Colors,
    Metrics,
    Typography,
    base_font_stack,
    line_edit_stylesheet,
    segmented_button_stylesheet,
    soft_button_stylesheet,
    toggle_button_stylesheet,
)


class SettingsWindow(DialogShell):
    config_changed = Signal(object)
    pet_name_changed = Signal(str)
    open_weather_settings_requested = Signal()
    check_update_requested = Signal()
    about_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(title="设置", icon_name="settings", parent=parent)
        self._updating = False
        self.resize(380, 520)
        self.setMinimumSize(360, 500)
        self._build_ui()
        self.set_title("设置")

    def sync_from_config(self, config: AppConfig, pet_name: str) -> None:
        self._updating = True
        try:
            self.pet_name_input.setText(pet_name)
            self.auto_start_toggle.setChecked(config.auto_start)
            self.auto_start_toggle.setText(_toggle_text(config.auto_start))
            self.drink_spin.setValue(config.drink_remind_interval_minutes)
            self.sedentary_spin.setValue(config.sedentary_remind_interval_minutes)
            self.hourly_toggle.setChecked(config.hourly_report_enabled)
            self.hourly_toggle.setText(_toggle_text(config.hourly_report_enabled))
            self.random_dialog_toggle.setChecked(config.random_dialog_enabled)
            self.random_dialog_toggle.setText(_toggle_text(config.random_dialog_enabled))
            self._select_font_button(config.ui_font_size_px)
            self.version_value_label.setText(display_version(APP_VERSION))
        finally:
            self._updating = False

    def _build_ui(self) -> None:
        self.body_layout.setContentsMargins(Metrics.PADDING_LG, Metrics.PADDING_LG, Metrics.PADDING_LG, Metrics.PADDING_LG)
        self.body_layout.setSpacing(12)

        hero = self._card(background=_rgba(Colors.BG_INPUT, 248), border_alpha=70, radius=Metrics.RADIUS_LG)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(14, 12, 14, 12)
        hero_layout.setSpacing(4)
        title = QLabel("应用设置", hero)
        title.setText("应用设置")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()};"
            f"font-size: {Typography.SIZE_H1}px;"
            "font-weight: 600;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        subtitle = QLabel("桌宠会按照你的习惯提醒、播报和显示。", hero)
        subtitle.setText("把常用行为、提醒节奏和界面大小收在这里。")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()};"
            "font-size: 12px;"
            f"font-family: {base_font_stack(include_emoji=True)};"
        )
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        self.body_layout.addWidget(hero)

        profile_card = self._card(background=_rgba(Colors.BG_CARD, 252), border_alpha=78, radius=Metrics.RADIUS_MD)
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setContentsMargins(16, 12, 16, 14)
        profile_layout.setSpacing(10)
        profile_layout.addWidget(self._section_title("基本信息"))

        name_row = QHBoxLayout()
        name_row.addWidget(self._field_label("宠物名称"), 0)
        self.pet_name_input = QLineEdit(profile_card)
        self.pet_name_input.setPlaceholderText("输入桌宠名字")
        self.pet_name_input.setStyleSheet(line_edit_stylesheet())
        self.pet_name_input.setPlaceholderText("输入桌宠名称")
        self.pet_name_input.editingFinished.connect(self._emit_pet_name_changed)
        name_row.addWidget(self.pet_name_input, 1)
        profile_layout.addLayout(name_row)

        auto_start_row = self._setting_row("开机启动", "将桌宠随系统一起启动")
        self.auto_start_toggle = self._toggle_button(False)
        self.auto_start_toggle.clicked.connect(self._emit_config_changed)
        auto_start_row.addWidget(self.auto_start_toggle)
        profile_layout.addLayout(auto_start_row)

        weather_button = QPushButton("天气设置…", profile_card)
        weather_button.setText("天气设置")
        weather_button.setCursor(Qt.PointingHandCursor)
        weather_button.setStyleSheet(_secondary_button_stylesheet())
        weather_button.clicked.connect(self.open_weather_settings_requested.emit)
        profile_layout.addWidget(weather_button)

        reminder_card = self._card(background=_rgba(Colors.BG_CARD, 252), border_alpha=78, radius=Metrics.RADIUS_MD)
        reminder_layout = QGridLayout(reminder_card)
        reminder_layout.setContentsMargins(16, 12, 16, 14)
        reminder_layout.setHorizontalSpacing(10)
        reminder_layout.setVerticalSpacing(10)
        reminder_layout.addWidget(self._section_title("提醒与互动"), 0, 0, 1, 2)

        reminder_layout.addWidget(self._field_label("喝水提醒"), 1, 0)
        self.drink_spin = QSpinBox(reminder_card)
        self.drink_spin.setRange(15, 240)
        self.drink_spin.setSuffix(" 分钟")
        self.drink_spin.setStyleSheet(line_edit_stylesheet())
        self.drink_spin.setSuffix(" 分钟")
        self.drink_spin.valueChanged.connect(self._emit_config_changed)
        reminder_layout.addWidget(self.drink_spin, 1, 1)

        reminder_layout.addWidget(self._field_label("久坐提醒"), 2, 0)
        self.sedentary_spin = QSpinBox(reminder_card)
        self.sedentary_spin.setRange(30, 360)
        self.sedentary_spin.setSuffix(" 分钟")
        self.sedentary_spin.setStyleSheet(line_edit_stylesheet())
        self.sedentary_spin.setSuffix(" 分钟")
        self.sedentary_spin.valueChanged.connect(self._emit_config_changed)
        reminder_layout.addWidget(self.sedentary_spin, 2, 1)

        hourly_row = self._setting_row("整点报时", "每小时整点给出一次提示")
        self.hourly_toggle = self._toggle_button(False)
        self.hourly_toggle.clicked.connect(self._emit_config_changed)
        hourly_row.addWidget(self.hourly_toggle)
        reminder_layout.addLayout(hourly_row, 3, 0, 1, 2)

        dialog_row = self._setting_row("随机对话", "允许桌宠在空闲时说话")
        self.random_dialog_toggle = self._toggle_button(False)
        self.random_dialog_toggle.clicked.connect(self._emit_config_changed)
        dialog_row.addWidget(self.random_dialog_toggle)
        reminder_layout.addLayout(dialog_row, 4, 0, 1, 2)

        font_card = self._card(background=_rgba(Colors.BG_CARD, 252), border_alpha=78, radius=Metrics.RADIUS_MD)
        font_layout = QVBoxLayout(font_card)
        font_layout.setContentsMargins(16, 12, 16, 14)
        font_layout.setSpacing(10)
        font_layout.addWidget(self._section_title("字体"))
        font_layout.addWidget(self._field_help("气泡字号和右键菜单字号会同步变化"))

        font_row = QHBoxLayout()
        font_row.setSpacing(6)
        self.font_button_group = QButtonGroup(self)
        self.font_buttons: list[QPushButton] = []
        for value, label in ((12, "小"), (13, "中"), (15, "大"), (17, "特大")):
            button = QPushButton(label, font_card)
            button.setText(_clean_text(label))
            button.setCheckable(True)
            button.setProperty("fontSizeValue", value)
            button.setStyleSheet(segmented_button_stylesheet())
            button.clicked.connect(self._emit_config_changed)
            self.font_button_group.addButton(button)
            self.font_buttons.append(button)
            font_row.addWidget(button)
        font_layout.addLayout(font_row)

        about_card = self._card(background=_rgba(Colors.BG_INPUT, 252), border_alpha=92, radius=Metrics.RADIUS_MD)
        about_layout = QVBoxLayout(about_card)
        about_layout.setContentsMargins(16, 12, 16, 14)
        about_layout.setSpacing(10)
        about_layout.addWidget(self._section_title("版本与更新"))

        version_row = QHBoxLayout()
        version_row.setSpacing(10)
        version_row.addWidget(self._field_label("当前版本"), 0)
        self.version_value_label = QLabel(display_version(APP_VERSION), about_card)
        self.version_value_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: 12px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
        )
        version_row.addWidget(self.version_value_label, 1, Qt.AlignRight)
        about_layout.addLayout(version_row)

        version_hint = self._field_help("更新检查会访问 GitHub 发布页。")
        version_hint.setWordWrap(True)
        about_layout.addWidget(version_hint)

        about_buttons = QHBoxLayout()
        about_buttons.setSpacing(8)
        check_update_button = QPushButton("检查更新", about_card)
        check_update_button.setCursor(Qt.PointingHandCursor)
        check_update_button.setStyleSheet(_secondary_button_stylesheet())
        check_update_button.clicked.connect(self.check_update_requested.emit)
        about_buttons.addWidget(check_update_button, 1)

        about_button = QPushButton("关于", about_card)
        about_button.setCursor(Qt.PointingHandCursor)
        about_button.setStyleSheet(_secondary_button_stylesheet())
        about_button.clicked.connect(self.about_requested.emit)
        about_buttons.addWidget(about_button, 1)
        about_layout.addLayout(about_buttons)

        self.body_layout.addWidget(profile_card)
        self.body_layout.addWidget(reminder_card)
        self.body_layout.addWidget(font_card)
        self.body_layout.addWidget(about_card)
        self.body_layout.addStretch(1)

    def _emit_pet_name_changed(self) -> None:
        if self._updating:
            return
        self.pet_name_changed.emit(self.pet_name_input.text().strip())

    def _emit_config_changed(self) -> None:
        if self._updating:
            return
        config = AppConfig.default()
        config.auto_start = self.auto_start_toggle.isChecked()
        config.drink_remind_interval_minutes = self.drink_spin.value()
        config.sedentary_remind_interval_minutes = self.sedentary_spin.value()
        config.hourly_report_enabled = self.hourly_toggle.isChecked()
        config.random_dialog_enabled = self.random_dialog_toggle.isChecked()
        config.ui_font_size_px = self._selected_font_size()
        self.auto_start_toggle.setText(_toggle_text(config.auto_start))
        self.hourly_toggle.setText(_toggle_text(config.hourly_report_enabled))
        self.random_dialog_toggle.setText(_toggle_text(config.random_dialog_enabled))
        self.config_changed.emit(config)

    def _selected_font_size(self) -> int:
        for button in self.font_buttons:
            if button.isChecked():
                return int(button.property("fontSizeValue"))
        return 13

    def _select_font_button(self, value: int) -> None:
        chosen = min(self.font_buttons, key=lambda button: abs(int(button.property("fontSizeValue")) - value))
        chosen.setChecked(True)

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

    @staticmethod
    def _field_label(text: str) -> QLabel:
        text = _clean_text(text)
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: 12px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
        )
        return label

    @staticmethod
    def _field_help(text: str) -> QLabel:
        text = _clean_text(text)
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {_rgba(Colors.TEXT_SECONDARY, 200)}; font-size: 10px; font-family: {base_font_stack(include_emoji=True)};"
        )
        return label

    @staticmethod
    def _section_title(text: str) -> QLabel:
        text = _clean_text(text)
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: 12px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
        )
        return label

    @staticmethod
    def _setting_row(title: str, subtitle: str) -> QHBoxLayout:
        title = _clean_text(title)
        subtitle = _clean_text(subtitle)
        row = QHBoxLayout()
        row.setSpacing(10)
        text_wrap = QVBoxLayout()
        text_wrap.setSpacing(1)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY.name()}; font-size: 12px; font-weight: 600; font-family: {base_font_stack(include_emoji=True)};"
        )
        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet(
            f"color: {_rgba(Colors.TEXT_SECONDARY, 200)}; font-size: 10px; font-family: {base_font_stack(include_emoji=True)};"
        )
        text_wrap.addWidget(title_label)
        text_wrap.addWidget(sub_label)
        row.addLayout(text_wrap, 1)
        return row

    @staticmethod
    def _toggle_button(checked: bool) -> QPushButton:
        button = QPushButton(_toggle_text(checked))
        button.setCheckable(True)
        button.setChecked(checked)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(toggle_button_stylesheet())
        return button


def _clean_text(text: str) -> str:
    mapping = {
        "鍩烘湰淇℃伅": "基本信息",
        "瀹犵墿鍚嶇О": "宠物名称",
        "寮€鏈哄惎鍔?": "开机启动",
        "灏嗘瀹犻殢绯荤粺涓€璧峰惎鍔?": "跟随系统一起启动桌宠。",
        "鎻愰啋涓庝簰鍔?": "提醒与互动",
        "鍠濇按鎻愰啋": "喝水提醒",
        "涔呭潗鎻愰啋": "久坐提醒",
        "鏁寸偣鎶ユ椂": "整点报时",
        "姣忓皬鏃舵暣鐐圭粰鍑轰竴娆℃彁绀?": "每到整点给出一次提示。",
        "闅忔満瀵硅瘽": "随机对话",
        "鍏佽妗屽疇鍦ㄧ┖闂叉椂璇磋瘽": "允许桌宠在空闲时主动冒泡。",
        "瀛椾綋": "显示字号",
        "姘旀场瀛楀彿鍜屽彸閿彍鍗曞瓧鍙蜂細鍚屾鍙樺寲": "气泡字号和右键菜单字号会同步变化。",
        "灏?": "小",
        "涓?": "中",
        "澶?": "大",
        "鐗瑰ぇ": "特大",
    }
    return mapping.get(text, text)


def _toggle_text(value: bool) -> str:
    return "开启" if value else "关闭"


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
    QPushButton:disabled {{
        color: {_rgba(Colors.TEXT_SECONDARY, 150)};
        background: {_rgba(Colors.BORDER_DEFAULT, 35)};
        border-color: {_rgba(Colors.BORDER_DEFAULT, 70)};
    }}
    """


def _rgba(color, alpha: int | None = None) -> str:
    resolved_alpha = color.alpha() if alpha is None else int(alpha)
    return f"rgba({color.red()},{color.green()},{color.blue()},{resolved_alpha})"


def _toggle_text(value: bool) -> str:
    return "开启" if value else "关闭"


def _toggle_text(value: bool) -> str:
    return "开启" if value else "关闭"
