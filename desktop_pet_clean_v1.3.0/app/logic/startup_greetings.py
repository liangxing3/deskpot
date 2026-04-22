from __future__ import annotations

import random


STARTUP_GREETING_MESSAGES: tuple[str, ...] = (
    "汪，今天也想陪在你身边",
    "小狗来啦，先陪你一下",
    "打开电脑的第一眼就见到你啦",
    "今天也给你一点小小温柔",
    "小狗报道，陪你开始今天",
    "汪呜，希望你今天顺顺利利",
    "我在呢，慢慢来就好",
    "见到你啦，小狗心情很好",
    "今天也想做你的小陪伴",
    "小狗贴贴，别太累啦",
    "汪，今天也要对自己好一点",
    "你一来，小狗就开始开心了",
)

STARTUP_GREETING_TTL_MS = 4_800
STARTUP_GREETING_DELAY_MS = 320


def get_startup_greeting() -> str:
    return random.choice(STARTUP_GREETING_MESSAGES)
