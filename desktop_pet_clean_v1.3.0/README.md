# 桌宠助手

当前版本：`v1.3.0`

一个基于 `Python + PySide6` 的 Windows 桌宠项目。当前代码已经收敛到单一正式运行链，不再以旧兼容文件作为开发入口。

正式运行链：

```text
main.py -> app/controller.py -> ui/*
```

## 项目概览

这个项目的目标不是继续在旧仓库上堆补丁，而是在干净目录中维护一套可持续演进的桌宠实现。  
当前版本已经具备主窗、托盘、状态窗、设置窗、天气、答案之书、关于页、检查更新、启动欢迎气泡、后台天气监测与显著变化提醒等完整链路。

当前设计原则：

- 只有一套正式控制器：`app/controller.py`
- 只有一套正式桌宠主窗：`ui/pet_window.py`
- 功能弹窗统一复用：`ui/dialog_shell.py`
- 气泡统一复用：`ui/dialog_bubble.py`
- 业务逻辑尽量放在 `app/logic/` 和 `services/`
- UI 层只负责显示与交互，不承担复杂调度

## 当前功能

### 桌宠主窗

- 无边框、透明、置顶的 GIF 桌宠窗口
- 基于像素命中的点击与拖拽
- 左键交互、右键菜单、拖拽保存位置
- 启动时播放 `APPEAR` 动画
- 启动后首次显示欢迎气泡

### 气泡系统

- 气泡跟随宠物位置
- 使用统一气泡组件，不额外造新通知 UI
- 支持优先级和自动消失
- 用于欢迎语、交互反馈、天气变化提醒等场景

### 功能窗口

- `状态`
- `设置`
- `天气设置`
- `天气`
- `答案之书`
- `关于`

所有功能窗口都走统一 `DialogShell`，位置由 controller 统一管理和持久化。

### 托盘与版本

- 系统托盘常驻
- 支持显示/隐藏主窗
- 支持打开状态、天气、答案之书、设置、关于
- 支持检查更新
- 托盘 tooltip 显示当前版本号

### 天气能力

- 手动刷新天气
- 天气摘要窗口
- 天气设置窗口
- 后台天气监测
- 显著变化提醒

后台天气监测当前行为：

- 程序启动后先做一次初始化天气抓取
- 后续每小时后台抓取一次天气快照
- 将本次快照与上一有效快照比较
- 仅在变化显著时才通过现有气泡系统提醒
- 同类提醒有冷却去重，默认 3 小时内不重复提醒

### 答案之书与随机文案

- 答案之书正式实现：`ui/answer_book_dialog_v2.py`
- 随机文案/一言通过服务层获取
- 服务异常时会走缓存或本地兜底，不直接阻塞 UI

## 目录结构

```text
desktop_pet_clean - 1/
├─ main.py
├─ app/
│  ├─ app_metadata.py
│  ├─ controller.py
│  └─ logic/
│     ├─ animation_selector.py
│     ├─ pet_actions.py
│     ├─ reminders.py
│     ├─ scheduler.py
│     ├─ startup_greetings.py
│     └─ weather_monitor.py
├─ data/
│  ├─ config_manager.py
│  ├─ models.py
│  ├─ pet_models.py
│  ├─ pet_repository.py
│  └─ runtime_state_manager.py
├─ services/
│  ├─ answerbook_service.py
│  ├─ cache_service.py
│  ├─ dialog_service.py
│  ├─ local_dialog_provider.py
│  ├─ uapi_dialog_provider.py
│  ├─ update_service.py
│  ├─ weather_care_advisor.py
│  └─ weather_service.py
├─ ui/
│  ├─ about_dialog.py
│  ├─ answer_book_dialog_v2.py
│  ├─ dialog_bubble.py
│  ├─ dialog_shell.py
│  ├─ pet_window.py
│  ├─ settings_window.py
│  ├─ status_window.py
│  ├─ theme.py
│  ├─ tray_menu.py
│  ├─ weather_dialog.py
│  └─ weather_settings_dialog.py
├─ utils/
├─ assets/
├─ config.json
├─ developer_config.py
├─ AGENTS.md
├─ AI_HANDOFF.md
└─ requirements.txt
```

说明：

- `*_clean.py`、旧 `v2`、兼容壳文件不是正式开发入口
- 当前正式答案之书文件是 `ui/answer_book_dialog_v2.py`
- 当前正式主窗由 `ui/pet_window.py` 接入 controller

## 核心模块

### `main.py`

负责：

- 初始化日志
- 创建 `QApplication`
- 创建 `AppController`
- 进入事件循环

### `app/controller.py`

应用唯一装配层，负责：

- 加载配置、宠物状态、运行时状态
- 创建主窗、托盘和功能 Dialog
- 连接所有 UI 信号
- 驱动动画切换与气泡显示
- 调用天气、答案之书、更新检查等服务
- 保存窗口位置和运行状态
- 接入 scheduler 统一调度

### `app/logic/`

纯逻辑层，不直接操作界面：

- `animation_selector.py`：动画选择与切换
- `pet_actions.py`：喂食、陪玩、清洁、休息等动作逻辑
- `startup_greetings.py`：启动欢迎语文案池
- `scheduler.py`：统一定时轮询
- `reminders.py`：提醒事件判定
- `weather_monitor.py`：天气快照比较、提醒文案、签名去重

### `data/models.py`

核心数据模型集中定义在这里，包括：

- `AppConfig`
- `WindowPosition`
- `PetVitals`
- `WeatherSnapshot`
- `WeatherAlertState`

天气后台监测依赖这里的快照和冷却状态持久化。

### `services/`

服务层负责对外能力接入：

- `weather_service.py`：天气获取与快照构建
- `answerbook_service.py`：答案之书
- `dialog_service.py`：随机文案/一言入口
- `update_service.py`：检查更新
- `cache_service.py`：缓存读写

## 天气后台监测说明

当前天气监测链路如下：

1. 启动时 controller 会先做一次 seed 抓取
2. `AppScheduler` 每分钟轮询一次 `ReminderEngine`
3. `ReminderEngine` 根据 `last_checked_at + 60 分钟` 决定是否发出 `weather_monitor_tick`
4. controller 收到 tick 后在后台线程调用 `weather_service.get_weather(...)`
5. 天气服务构建详细 `WeatherSnapshot`
6. `weather_monitor.compare_weather_snapshots(...)` 比较上一快照和当前快照
7. 若命中显著变化且未进入冷却，则调用现有 `_show_bubble(...)` 发提醒

当前已实现的显著变化类型包括：

- 天气现象明显变化
- 从无降水到有降水
- 雨势增强
- 温度变化较大
- 体感温度变化较大
- 风力明显增强
- 降雨概率突增
- AQI 明显恶化
- 新天气预警
- 天气预警等级上升

去重策略：

- 为变化生成提醒签名
- 默认同签名 3 小时内不重复提醒
- 更严重的变化可以突破冷却
- 城市变化时会重置监测上下文，不直接跨城市比较

## 天气字段与接口能力

当前天气快照会尽量保留现有 API 返回的详细字段，包括：

- 城市 / 位置
- 天气现象文本
- 条件代码
- 当前温度 / 最高 / 最低
- 体感温度
- 湿度
- 风向 / 风级 / 风速
- 降水量 / 降水概率
- 气压
- 能见度
- AQI
- 预警列表 / 预警文本
- `forecast`
- `hourly`
- `life_indices`
- `raw_payload`

限制说明：

- 是否返回更详细的 `hourly / minutely / indices` 字段，受 `developer_config.py` 中当前请求参数和远端接口能力影响
- 当前实现已经按现有接口能力做最佳接入，不会伪造接口没有返回的字段

## 运行环境

推荐环境：

- Windows
- Python `3.13`
- `PySide6`

依赖：

```text
PySide6>=6.7
requests>=2.31
uapi-sdk-python>=0.1
pyinstaller>=6.0
```

安装依赖：

```powershell
D:\Python313\python.exe -m pip install -r requirements.txt
```

运行项目：

```powershell
cd "E:\Users\liangxing\Desktop\deskpot\desktop_pet_clean - 1"
D:\Python313\python.exe main.py
```

## 配置与运行时数据

### 静态配置

- 项目默认配置：`config.json`
- 开发者接口配置：`developer_config.py`

### 运行时状态

程序优先写入：

- `%APPDATA%\DesktopPetAssistantV1`

如果该位置不可写，则回退到项目目录下：

- `.appdata/DesktopPetAssistantV1`

其中会保存：

- 用户配置
- 宠物状态
- 运行时状态
- 天气监测快照与提醒冷却记录
- 日志
- 缓存

## 当前状态

当前代码已完成：

- 统一正式运行链
- 主窗 / 托盘 / 统一 Dialog
- 关于页与版本号
- 检查更新入口
- 启动欢迎气泡
- 天气后台监测与显著变化提醒

当前仍建议继续验证：

- 天气后台监测的真实 1 小时轮询
- 真实天气突变时的提醒体感
- 不同网络场景下的降级表现
- 天气窗口是否继续展示更多已入模字段

## 开发约束

如果继续在这个项目上开发，建议遵循：

- 先读 `AI_HANDOFF.md`
- 正式改动只落在正式运行链
- 不要把复杂逻辑写回 UI 渲染层
- 不要在 worker 线程直接操作 UI
- Dialog 保持 `parent=None`，由 controller 持有

## 发布构建

当前正式的第二阶段发布入口为：

```powershell
cd "E:\Users\liangxing\Desktop\deskpot\desktop_pet_clean - 1"
powershell -ExecutionPolicy Bypass -File .\tools\build_release.ps1
```

该脚本会顺序完成：

- 复制一份不含用户数据的干净源码副本到 `desktop_pet_clean_release_v1.3.0`
- 重新生成 `dist/DesktopPetAssistantV1`
- 重新生成安装包 `installer/DesktopPetAssistantV1-Setup-v1.3.0.exe`
- 额外生成便携压缩包 `installer/DesktopPetAssistantV1-Portable-v1.3.0.zip`

如果只想基于当前目录重做安装包，可继续使用：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_installer.ps1
```

## 说明

这份 README 以当前工作副本 `desktop_pet_clean - 1` 的实际代码状态为准。  
如果后续继续新增功能，请同步更新 `AI_HANDOFF.md`，并视情况更新 README，避免说明文档再次落后于正式链路。

<!-- Legacy README retained below for reference; hidden from rendering.
# Desktop Pet Clean

一个基于 `Python + PySide6` 的 Windows 桌宠项目。  
当前版本采用单一启动链和单一 UI 实现，不再沿用旧仓库中的 `runtime`、`v2`、兼容壳和多套分叉界面。

正式架构：

```text
main.py -> app/controller.py -> ui/*
```

## 项目定位

这个项目不是在旧仓库上继续修补，而是在干净目录中重建桌宠应用。

重构原则：

- 旧仓库只作为资产库和逻辑参考库
- `assets/`、`data/`、`services/`、`utils/` 中稳定部分可迁移复用
- `core/runtime_app_controller.py`、`core/ui_coordinator.py`、旧版 `ui/*.py`、`*_v2.py` 不再作为核心
- 新项目任何时刻只保留一套正式 UI

## 当前 UI 设计

### 1. 纯 GIF 桌宠主窗

主窗正式实现位于 `ui/pet_window_pure.py`。

它是一个完全透明、无边框、置顶的工具窗口，只显示宠物 GIF 本体，不显示传统矩形背景面板。

当前主窗特性：

- 顶级窗口透明，无系统边框
- 只显示 GIF，不显示背景壳、阴影或包裹面板
- 鼠标命中基于 GIF 当前帧透明度判断
- 只有点击到宠物非透明像素区域时，左键拖拽和右键菜单才会生效
- 左键拖拽开始后会抓取鼠标，拖出透明区域后也不会中断

### 2. 主菜单

主菜单是主窗的右键菜单，不使用额外悬浮按钮。

当前菜单结构：

- 互动
- 天气
- 答案之书
- 设置

其中“互动”为子菜单，包含：

- 喂食
- 陪玩
- 清洁
- 休息

菜单风格统一为：

- 浅粉白背景
- 半透明玫瑰描边
- 圆角卡片式边框
- 一级和二级菜单共享同一套 hover 与 checked 视觉

主菜单的弹出位置不是跟随点击点随机出现，而是相对宠物窗口固定锚定，并带有屏幕边缘避让逻辑，避免在极端位置贴边过紧。

### 3. 气泡

气泡用于消息展示，属于展示层。

当前规则：

- 气泡跟随宠物移动
- 气泡为无边框透明窗口
- 气泡不抢焦点
- Dialog 打开时，Dialog 层级高于气泡

### 4. 功能弹窗

所有功能弹窗都建立在统一的 `DialogShell` 之上。

当前包含：

- `ui/status_window.py`
- `ui/settings_window.py`
- `ui/weather_settings_dialog.py`
- `ui/weather_dialog.py`
- `ui/answer_book_dialog.py`

这些窗口共享：

- 统一标题栏
- 统一边框和圆角
- 统一关闭按钮
- 统一内容容器
- 标题栏可拖拽移动

当前位置规则：

- 首次打开时，默认相对宠物主窗排布
- 用户拖动后，窗口位置会被记录
- 再次打开时，恢复到用户上次拖动的位置
- 宠物移动时，只有气泡和主菜单保持与宠物相对关系
- 其余 Dialog 不再跟随宠物平移

## 当前功能状态

项目当前已经具备以下能力：

- 稳定启动 `QApplication`
- 显示透明桌宠主窗
- 播放默认 GIF
- 像素级命中检测
- 左键拖拽桌宠
- 右键主菜单
- 互动动作触发
- 气泡消息显示
- 系统托盘
- 状态面板
- 系统设置
- 天气设置
- 天气摘要
- 答案之书
- 宠物状态持久化
- 主窗位置持久化
- Dialog 位置持久化

## 目录结构

```text
desktop_pet_clean/
├── main.py
├── app/
│   ├── controller.py
│   └── logic/
│       ├── animation_selector.py
│       ├── pet_actions.py
│       ├── reminders.py
│       └── scheduler.py
├── ui/
│   ├── pet_window.py
│   ├── pet_window_pure.py
│   ├── dialog_bubble.py
│   ├── dialog_shell.py
│   ├── tray_menu.py
│   ├── status_window.py
│   ├── settings_window.py
│   ├── weather_dialog.py
│   ├── weather_settings_dialog.py
│   ├── answer_book_dialog.py
│   ├── theme.py
│   └── icons.py
├── data/
│   ├── models.py
│   ├── pet_models.py
│   ├── config_manager.py
│   ├── pet_repository.py
│   └── runtime_state_manager.py
├── services/
│   ├── weather_service.py
│   ├── answerbook_service.py
│   └── cache_service.py
├── utils/
│   ├── paths.py
│   ├── font_loader.py
│   ├── autostart.py
│   └── time_utils.py
├── assets/
├── config.json
├── developer_config.py
└── requirements.txt
```

## 核心模块说明

### `main.py`

只负责：

- 启动 `QApplication`
- 初始化日志
- 安装全局异常处理
- 创建 `AppController`
- 进入事件循环

### `app/controller.py`

是整个应用的唯一装配根。

主要负责：

- 加载配置和宠物状态
- 创建主窗、托盘和所有 Dialog
- 连接 Signal / Slot
- 协调动画切换和气泡展示
- 打开天气、设置、状态、答案之书等窗口
- 处理窗口位置保存和恢复
- 驱动提醒调度和天气刷新

### `ui/`

只负责界面与交互表现，不承担复杂业务协调。

其中：

- `pet_window_pure.py` 是当前正式主窗实现
- `dialog_shell.py` 是统一弹窗壳
- `dialog_bubble.py` 是桌宠气泡
- `theme.py` 统一维护样式
- `icons.py` 统一维护图标系统

### `app/logic/`

放纯逻辑，不直接操作界面。

例如：

- `pet_actions.py`：喂食、陪玩、清洁、休息等本地动作逻辑
- `animation_selector.py`：根据状态和情绪选 GIF
- `reminders.py` / `scheduler.py`：提醒与调度

### `data/`

负责数据模型和本地持久化。

关键模型包括：

- `AppConfig`
- `WindowPosition`
- `WeatherSnapshot`
- `PetStatus`

### `services/`

负责外部服务接入。

当前主要包括：

- 天气服务
- 答案之书服务
- 缓存服务

## 交互规则

当前项目的交互层级是清晰分离的：

- 桌宠主窗：纯 GIF、透明、像素级命中、左键拖拽、右键菜单
- 气泡：跟随宠物，负责短时展示消息
- 主菜单：相对宠物固定锚点弹出
- Dialog：独立可拖拽，默认相对宠物排布，之后恢复用户上次位置
- 托盘：作为全局保底入口

## 运行方式

当前建议使用已安装 `PySide6` 的 Python 3.13 解释器运行：

```powershell
cd E:\Users\liangxing\Desktop\deskpot\desktop_pet_clean
D:\Python313\python.exe main.py
```

不要直接双击 `.py` 文件运行。  
如果系统默认 `py.exe` 指向了未安装 `PySide6` 的解释器，会出现启动后立即退出的现象。

## 当前实现边界

这个新项目已经脱离旧仓库胶水结构，但仍有几项后续工作适合继续推进：

- 清理部分窗口中的历史乱码文案
- 进一步细化各 Dialog 的默认布局和避免重叠策略
- 扩展天气详情卡片
- 强化答案之书与天气服务的错误回退表现
- 丰富桌宠动作动画与交互反馈

## 结论

`desktop_pet_clean` 已经不是“旧项目修补版”，而是一个可以持续演进的干净桌宠项目基线。  
主窗、主菜单、气泡、Dialog、状态、设置、天气、答案之书等能力都已经运行在统一的架构与 UI 体系之上，后续新增功能不需要再回到旧链路中缝补。
-->
