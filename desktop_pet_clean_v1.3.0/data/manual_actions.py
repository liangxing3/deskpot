from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ManualActionSpec:
    action_id: str
    label: str
    bubble_text: str
    variant: str
    duration_ms: int
    hunger_delta: int = 0
    mood_delta: int = 0
    energy_delta: int = 0
    cleanliness_delta: int = 0
    favorability_delta: int = 0
    growth_exp_delta: int = 0


MANUAL_ACTION_SPECS: dict[str, ManualActionSpec] = {
    "feed": ManualActionSpec(
        action_id="feed",
        label="喂食",
        bubble_text="吃得饱饱的，心情也跟着好起来了。",
        variant="feed",
        duration_ms=5_000,
        hunger_delta=18,
        mood_delta=4,
        energy_delta=4,
        favorability_delta=3,
        growth_exp_delta=4,
    ),
    "play": ManualActionSpec(
        action_id="play",
        label="陪玩",
        bubble_text="玩得很开心，今天又是活力满满的一次互动。",
        variant="play",
        duration_ms=6_000,
        hunger_delta=-6,
        mood_delta=16,
        energy_delta=-8,
        favorability_delta=4,
        growth_exp_delta=8,
    ),
    "clean": ManualActionSpec(
        action_id="clean",
        label="清洁",
        bubble_text="整理干净以后，整只小狗都轻松了不少。",
        variant="clean",
        duration_ms=5_500,
        mood_delta=4,
        cleanliness_delta=20,
        favorability_delta=2,
        growth_exp_delta=3,
    ),
    "rest": ManualActionSpec(
        action_id="rest",
        label="休息",
        bubble_text="先好好歇一会儿，状态会慢慢回来的。",
        variant="rest",
        duration_ms=7_000,
        mood_delta=3,
        energy_delta=20,
        favorability_delta=1,
        growth_exp_delta=2,
    ),
    "petting": ManualActionSpec(
        action_id="petting",
        label="贴贴",
        bubble_text="贴贴一下，安心感立刻上来了。",
        variant="petting",
        duration_ms=4_000,
        mood_delta=6,
        favorability_delta=2,
        growth_exp_delta=1,
    ),
    "pat": ManualActionSpec(
        action_id="pat",
        label="拍一拍",
        bubble_text="收到你的回应啦，我会继续好好陪着你。",
        variant="pat",
        duration_ms=3_000,
        mood_delta=3,
        favorability_delta=1,
        growth_exp_delta=1,
    ),
    "exercise": ManualActionSpec(
        action_id="exercise",
        label="锻炼",
        bubble_text="活动了一下，精神醒过来不少。",
        variant="exercise",
        duration_ms=7_000,
        hunger_delta=-8,
        mood_delta=8,
        energy_delta=-12,
        favorability_delta=3,
        growth_exp_delta=9,
    ),
    "charge": ManualActionSpec(
        action_id="charge",
        label="充电",
        bubble_text="先补一点元气，再继续今天的陪伴。",
        variant="charge",
        duration_ms=8_000,
        mood_delta=2,
        energy_delta=16,
        favorability_delta=1,
        growth_exp_delta=2,
    ),
    "baji": ManualActionSpec(
        action_id="baji",
        label="吧唧",
        bubble_text="被认真回应了一下，心情轻快了很多。",
        variant="baji",
        duration_ms=4_000,
        mood_delta=7,
        favorability_delta=2,
        growth_exp_delta=2,
    ),
    "feather_ball": ManualActionSpec(
        action_id="feather_ball",
        label="鸡毛丸子",
        bubble_text="彩蛋互动触发，快乐值偷偷涨了一截。",
        variant="feather_ball",
        duration_ms=5_000,
        hunger_delta=-4,
        mood_delta=10,
        energy_delta=-6,
        favorability_delta=3,
        growth_exp_delta=6,
    ),
    "appear": ManualActionSpec(
        action_id="appear",
        label="随机出现",
        bubble_text="换个位置继续待命，我还在这里。",
        variant="appear",
        duration_ms=3_500,
        mood_delta=2,
        energy_delta=-1,
        growth_exp_delta=1,
    ),
    "walkdog": ManualActionSpec(
        action_id="walkdog",
        label="遛狗",
        bubble_text="跑了一圈回来，整只小狗都更精神了。",
        variant="walkdog",
        duration_ms=7_000,
        hunger_delta=-8,
        mood_delta=12,
        energy_delta=-10,
        cleanliness_delta=-4,
        favorability_delta=5,
        growth_exp_delta=12,
    ),
}
