## UI 设计与架构说明（给其他 AI/开发者）

本文档描述当前工程的 **正式 UI 运行链**、**架构分层**、**弹窗/窗口的接口约定**、以及 **统一视觉风格（theme + DialogShell）** 的使用方式。

> 目标：任何 AI/开发者只要读完本文档，就能在不破坏现有运行链的前提下，继续按同一风格改造/新增 UI。

---

## 正式运行链（不要偏离）

- **入口**：`main.py`
- **控制器**：`app/controller.py`
- **UI**：`ui/*`

重要原则：
- **controller 是 UI 的唯一装配点**：负责创建/持有弹窗实例、连接 signals、调度服务调用与线程池。
- **功能弹窗必须 `parent=None`**：由 controller 持有实例，避免父子窗口生命周期与置顶/焦点异常。
- **不要回到旧兼容文件/旧 runtime 链**：除非用户明确要求。

---

## UI 分层与职责

### AppController（`app/controller.py`）

职责：
- 懒加载创建窗口/弹窗（`_ensure_*`）
- 连接 UI signals → 调用 service → 将结果回写到 UI（通过主线程安全回调）
- 统一管理窗口可见性状态（同步托盘菜单与主窗状态）
- 管理线程池/异步任务（`submit_task`）

关键约束：
- **不要在 worker 线程直接改 UI**：只能通过 `submit_task(... on_success=..., on_error=...)` 回到主线程更新。
- UI 对外接口以 “signal + setter 方法” 为主，controller 只依赖这些稳定接口。

---

## 统一弹窗壳：DialogShell（`ui/dialog_shell.py`）

### 为什么需要 DialogShell

所有浮动面板（答案之书、天气、设置等）统一复用：
- 无边框 + 半透明背景 + 阴影
- 统一 header（图标、标题、关闭按钮）
- 统一 body 容器与布局边距
- 拖动（按住 header 拖动）
- 统一 show/hide 事件与淡出关闭动画

### 关键行为

- **拖动**：header 事件过滤器实现（按下→移动→释放）
- **尺寸修复**：在 `showEvent` 中强制激活布局并按 `sizeHint()` 调整
  - 解决 “弹窗首次弹出偏小、拖动后才变大” 的问题
- **对外 signals（controller 会连接）**
  - `visibility_changed(bool)`
  - `drag_finished(WindowPosition)`

### 如何写新的弹窗

- 继承 `DialogShell`
- 使用 `self.body_layout` 添加内容（不要自己再创建顶层 QDialog layout）
- 保持 `parent=None`（由 controller 创建：`YourDialog(None)`）

---

## 统一主题系统：theme（`ui/theme.py`）

### 用法原则

新 UI 优先从 `ui/theme.py` 获取：
- **颜色**：`Colors.*`
- **尺寸/圆角/间距**：`Metrics.*`
- **字体**：`Typography.*` + `base_font_stack(...)`
- **通用控件样式**：如 `line_edit_stylesheet()` / `segmented_button_stylesheet()` / `toggle_button_stylesheet()` 等

尽量避免：
- 在每个文件里重复写一套颜色与字体常量
- “硬边框 + 重分割线”的旧式面板感

推荐风格（当前 UI 基调）：
- **卡片化**（轻背景、弱边框、圆角）
- **层级清晰**（Hero 文案区 → 表单卡片 → 行项目）
- **减少线条**（边框 alpha 降低、更多依靠留白分组）

---

## 当前主要弹窗/窗口（接口约定）

### 1) 答案之书（`ui/answer_book_dialog_v2.py`）

controller 依赖的稳定接口（不要破坏）：
- `submit_requested: Signal(str)`
- `focus_input()`
- `set_loading(question: str)`
- `set_result(result: AnswerBookResult)`
- `set_error(message: str)`

当前设计要点：
- Hero（顶部说明）
- 问题输入卡片（支持 `Ctrl+Enter` 提交）
- 快速提问：**只显示 2 个**
- 操作行：随机 / 清空 / 翻开答案
- 答案区：答案字体更大、聚焦显示

### 2) 天气设置（`ui/weather_settings_dialog.py`）

稳定接口：
- `config_changed: Signal(object)`（发出 `AppConfig` 的 partial）
- `sync_from_config(config: AppConfig)`

设计要点：
- Hero（顶部说明）
- 位置卡片（城市输入 + 自动定位 toggle）
- 显示偏好卡片（单位分段按钮、气泡 toggle、播报时间、恶劣天气 toggle）

### 3) 整体设置（`ui/settings_window.py`）

稳定接口：
- `config_changed: Signal(object)`（发出 `AppConfig` partial）
- `pet_name_changed: Signal(str)`
- `open_weather_settings_requested: Signal()`
- `sync_from_config(config: AppConfig, pet_name: str)`

设计要点：
- Hero（顶部说明）
- 基本信息卡片（宠物名、开机启动、天气设置入口）
- 提醒与互动卡片（喝水/久坐、整点报时、随机对话）
- 字体卡片（分段按钮）

---

## UI 改造的“稳定性规则”（强制）

- **保持 controller 连接的 signals/方法签名不变**（除非同步修改 controller 并验证）
- **弹窗类仍需继承 DialogShell**（统一行为/样式）
- **不要在 worker 线程直接操作 UI**
- **改 UI 时先看 controller 的 `_ensure_*` wiring**，确认外部依赖点

---

## 新增/重做一个弹窗的推荐流程（给 AI）

1. 在 `app/controller.py` 找到或新增 `_ensure_xxx_dialog()`，确认 signals wiring
2. 新建/重写 `ui/xxx_dialog.py`，继承 `DialogShell`
3. UI 构建只在 `self.body_layout` 内完成
4. 样式优先从 `ui/theme.py` 复用；必要时补充 theme，但不要每个文件自造体系
5. 运行验证：弹窗首次打开尺寸正确、拖动正常、关闭动画正常、置顶/焦点正常

---

## 快速入口：下一次 AI 应该先读哪些文件

- `AGENTS.md`
- `AI_HANDOFF.md`
- `app/controller.py`
- `ui/dialog_shell.py`
- `ui/theme.py`
- 目标弹窗对应的 `ui/*.py`

