from __future__ import annotations

import hashlib
import logging
from collections import deque
from typing import Any, Iterable

import developer_config
from data.models import DialogMessage


class DialogService:
    RECENT_KEY = "dialog:recent_texts"

    def __init__(
        self,
        *,
        logger: logging.Logger,
        cache_service,
        remote_provider=None,
        local_provider=None,
    ) -> None:
        self.logger = logger
        self.cache_service = cache_service
        self.remote_provider = remote_provider
        self.local_provider = local_provider
        cached_recent = cache_service.get(self.RECENT_KEY, allow_expired=True) or []
        self._recent_texts: deque[str] = deque(cached_recent, maxlen=12)

    def fetch_message(
        self,
        category: str,
        *,
        context: dict[str, Any] | None = None,
        prefer_remote: bool = True,
    ) -> DialogMessage:
        excluded = set(self._recent_texts)
        text = None
        source = "local"

        if prefer_remote and self.remote_provider is not None:
            try:
                text = self.remote_provider.fetch_message(category, context, excluded)
                if text:
                    self.cache_service.set(
                        f"dialog:last_remote:{category}",
                        {"text": text},
                        ttl_seconds=developer_config.DEFAULT_REMOTE_DIALOG_CACHE_TTL_SECONDS,
                    )
                    source = "remote"
            except Exception as exc:
                self.logger.warning("Remote dialog fetch failed: %s", exc)

        if not text:
            cached_remote = self.cache_service.get(
                f"dialog:last_remote:{category}", allow_expired=True
            ) or {}
            cached_text = cached_remote.get("text")
            if cached_text and cached_text not in excluded:
                text = cached_text
                source = "cache"

        if not text and self.local_provider is not None:
            text = self.local_provider.fetch_message(category, context, excluded)
            source = "local"

        if not text:
            text = "我先安静待一会儿。"
            source = "fallback"

        self._remember_text(text)
        message_id = hashlib.md5(f"{category}:{text}".encode("utf-8")).hexdigest()[:12]
        return DialogMessage(
            text=text,
            category=category,
            source=source,
            expires_in_seconds=6 if category.startswith("reminder_") else 4,
            message_id=message_id,
        )

    def _remember_text(self, text: str) -> None:
        self._recent_texts.append(text)
        self.cache_service.set(
            self.RECENT_KEY,
            list(self._recent_texts),
            ttl_seconds=developer_config.DEFAULT_DIALOG_DEDUP_TTL_SECONDS,
        )

    def recent_texts(self) -> Iterable[str]:
        return tuple(self._recent_texts)
