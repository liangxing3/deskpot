from __future__ import annotations

from typing import Iterable

from data.dialog_repository_store import DialogRepository


class LocalDialogProvider:
    def __init__(self, repository: DialogRepository | None = None) -> None:
        self.repository = repository or DialogRepository()

    def fetch_message(
        self,
        category: str,
        context: dict | None = None,
        excluded_texts: Iterable[str] | None = None,
    ) -> str | None:
        _ = context
        excluded = tuple(excluded_texts or ())
        message = self.repository.get_random_message(
            category,
            excluded_texts=excluded,
            default="今天也要照顾好自己呀。",
        )
        return message or None
