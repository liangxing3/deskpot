from __future__ import annotations

from collections.abc import Sequence


LOCAL_DIALOGS: dict[str, list[str]] = {
    "click": [
        "我在，点一下就有回应。",
        "你回来了一下，我记到了。",
        "要不要先把这一小时的任务收个口？",
        "别着急，我还在旁边。",
    ],
    "random_chat": [
        "先把当前这一步做完，再切下一个窗口。",
        "屏幕前待太久，效率会先掉下去。",
        "如果卡住了，先缩小问题范围。",
        "今天的节奏别拉太满。",
    ],
    "reminder_drink": [
        "该喝水了。",
        "补点水，状态会更稳。",
        "先喝两口水。",
    ],
    "reminder_sedentary": [
        "你已经坐很久了。",
        "起来活动两分钟。",
        "去走两步，放松一下。",
    ],
    "time_report": [
        "新的一小时开始了。",
        "到整点了，留意一下当前进度。",
        "可以顺手检查这一小时的安排。",
    ],
    "weather": [
        "天气我先帮你记下来了。",
        "出门前看一眼温度更稳妥。",
        "天气信息已更新。",
    ],
}


def get_dialogs(category: str) -> Sequence[str]:
    return LOCAL_DIALOGS.get(category, LOCAL_DIALOGS["random_chat"])
