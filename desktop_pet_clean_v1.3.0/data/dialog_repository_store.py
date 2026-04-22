from __future__ import annotations

import random
from collections.abc import Sequence


DIALOG_REPOSITORY: dict[str, list[str]] = {
    "click_feedback": [
        "我在呢，今天也要好好照顾自己呀。",
        "看到你啦，我会安静陪着你的。",
        "来啦，有什么想让我提醒的吗？",
        "辛苦啦，别忘了偶尔放松一下。",
        "摸摸头，先继续忙也没关系。",
        "我在这里，记得别太累哦。",
        "好呀，我陪你看看现在的情况。",
        "你点到我啦，那我认真陪你一下。",
    ],
    "random_chat": [
        "忙事情的时候，也别忘了照顾自己。",
        "慢一点也没关系，稳稳地来就很好。",
        "有点累的话，停几秒钟也不算偷懒。",
        "今天也在认真生活呢。",
        "别总是绷着，肩膀可以放松一点点。",
        "一步一步来，事情会慢慢变清楚的。",
        "如果有点烦，就先深呼吸一下吧。",
        "你已经很努力了，不用一直逼自己。",
        "我会在这里安安静静陪着你。",
        "喝口水，整理一下思路，也许会更顺。",
    ],
    "reminder_drink": [
        "该喝水啦，润一润喉咙会舒服很多。",
        "先喝两口水吧，状态会更稳一点。",
        "忙了这么久，记得补点水呀。",
        "喝点水再继续吧，别让自己太干了。",
        "小小提醒一下，该补水啦。",
        "放下手里的事几秒钟，喝口水吧。",
    ],
    "reminder_sedentary": [
        "你已经坐很久了，起来活动两分钟吧。",
        "站起来走一走，身体会舒服一点。",
        "可以伸个懒腰啦，别让自己一直绷着。",
        "坐太久会累的，起来动一动吧。",
        "去走两步吧，顺便放松一下肩颈。",
        "先离开座位一小会儿吧，我帮你记着节奏。",
    ],
    "hourly_report": [
        "整点啦，新的一小时开始了。",
        "现在到整点了，记得看看接下来的安排。",
        "新的一小时到了，慢慢推进就好。",
        "到点啦，别忘了活动一下肩膀和脖子。",
        "又一个整点到了，辛苦你了。",
        "现在是整点，记得给自己一点呼吸空间。",
    ],
    "weather_summary_intro": [
        "我帮你看了看天气。",
        "来，看看今天的天气情况吧。",
        "这是现在的天气信息。",
        "给你带来一份天气小报告。",
        "现在的天气大概是这样。",
    ],
    "weather_fallback": [
        "天气暂时获取失败了，等会儿再看看吧。",
        "我这会儿没拿到天气信息，稍后再试试。",
        "天气数据好像有点慢，先别着急。",
        "这次天气没有顺利拿到，下次我再帮你看。",
        "天气信息暂时不可用，不过我还在。",
    ],
    "weather_clothing": [
        "今天有点凉，记得多穿一点呀。",
        "外面温度偏低，穿暖和些会更舒服。",
        "早上出门的话，可以加一件外套哦。",
        "天气凉凉的，别让自己着凉啦。",
        "今天适合穿得稍微暖一点呢。",
    ],
    "weather_temperature_gap": [
        "今天早晚温差有点大，带件外套会更安心。",
        "白天和晚上温度差得不少，记得方便增减衣物呀。",
        "早晚会偏凉一点，别只看中午的温度哦。",
        "今天温差比较明显，穿搭尽量留一点余地吧。",
        "出门时带件薄外套，会省心很多呢。",
    ],
    "weather_take_umbrella": [
        "今天可能会下雨，带把伞会更稳妥呀。",
        "外面有降雨可能，伞记得顺手带上哦。",
        "天气不太稳定，带伞会更安心一点。",
        "看起来有点要下雨的样子，别忘了伞呀。",
        "出门前记得看看包里有没有伞哦。",
    ],
    "weather_hot_day": [
        "今天会有点热，穿轻便一些会舒服很多。",
        "气温偏高，记得及时补水呀。",
        "外面有些闷热，尽量穿得清爽一点吧。",
        "今天太阳可能会有点晒，出门多注意一点哦。",
        "天气热热的，别让自己太累啦。",
    ],
    "weather_bad_weather": [
        "外面天气不太温和，出门时多照顾好自己呀。",
        "风有点大，路上注意一点哦。",
        "天气情况一般，今天出门慢一点也没关系。",
        "外面可能会有点折腾，记得把自己照顾好。",
        "今天天气不算太友好，平安顺利最重要呀。",
    ],
    "pet_status_good": [
        "我今天状态不错呀，想继续陪着你。",
        "被照顾得很好呢，我现在很有精神。",
        "今天过得还挺开心的呀。",
        "现在感觉很舒服，谢谢你照顾我。",
        "我今天心情很好哦。",
    ],
    "pet_hungry": [
        "我有一点点饿了呀。",
        "要是能吃点东西，我会更开心。",
        "肚子开始空空的了。",
        "可以陪我吃点东西吗？",
        "我想补充一点点能量啦。",
    ],
    "pet_tired": [
        "我有点困了，休息一下会更舒服。",
        "现在有一点没精神呢。",
        "让我歇一会儿，好不好呀。",
        "我有点累啦，睡一下会恢复得更快。",
        "今天活动得有点多，想先缓一缓。",
    ],
    "pet_dirty": [
        "我好像有一点脏脏的了。",
        "如果能整理一下，我会更舒服呀。",
        "今天蹭得灰扑扑的啦。",
        "想变得干净一点点。",
        "帮我收拾一下的话，我会很开心哦。",
    ],
    "pet_growth": [
        "我好像又长大一点点啦。",
        "谢谢你一直照顾我，我在慢慢成长呀。",
        "今天的我，比之前更有精神了。",
        "和你待在一起的时间，让我慢慢长大了。",
        "我正在一点点变得更好呢。",
    ],
    "pet_favorability_up": [
        "和你待在一起，我会很安心。",
        "我越来越喜欢现在这样的相处啦。",
        "谢谢你愿意花时间陪我。",
        "被你照顾的感觉很好呀。",
        "我会记得你的温柔的。",
    ],
}

CATEGORY_ALIASES: dict[str, str] = {
    "click": "click_feedback",
    "click_feedback": "click_feedback",
    "random_chat": "random_chat",
    "reminder_drink": "reminder_drink",
    "reminder_sedentary": "reminder_sedentary",
    "time_report": "hourly_report",
    "hourly_report": "hourly_report",
    "weather": "weather_summary_intro",
    "weather_summary_intro": "weather_summary_intro",
    "weather_fallback": "weather_fallback",
    "weather_clothing": "weather_clothing",
    "weather_temperature_gap": "weather_temperature_gap",
    "weather_take_umbrella": "weather_take_umbrella",
    "weather_hot_day": "weather_hot_day",
    "weather_bad_weather": "weather_bad_weather",
    "pet_status_good": "pet_status_good",
    "pet_hungry": "pet_hungry",
    "pet_tired": "pet_tired",
    "pet_dirty": "pet_dirty",
    "pet_growth": "pet_growth",
    "pet_favorability_up": "pet_favorability_up",
}


class DialogRepository:
    def __init__(self, dialogs: dict[str, list[str]] | None = None) -> None:
        self._dialogs = dialogs or DIALOG_REPOSITORY

    def resolve_category(self, category: str) -> str:
        return CATEGORY_ALIASES.get(category, category)

    def get_messages(self, category: str) -> list[str]:
        return list(self._dialogs.get(self.resolve_category(category), []))

    def get_random_message(
        self,
        category: str,
        *,
        excluded_texts: Sequence[str] | None = None,
        default: str = "今天也要照顾好自己呀。",
    ) -> str:
        messages = self.get_messages(category)
        if not messages:
            return default

        excluded = set(excluded_texts or [])
        filtered = [message for message in messages if message not in excluded]
        if filtered:
            messages = filtered
        return random.choice(messages)

    def has_category(self, category: str) -> bool:
        return self.resolve_category(category) in self._dialogs

    def all_categories(self) -> list[str]:
        return list(self._dialogs.keys())


def get_dialogs(category: str) -> Sequence[str]:
    return DialogRepository().get_messages(category)
