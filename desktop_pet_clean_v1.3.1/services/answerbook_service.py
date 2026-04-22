from __future__ import annotations

import hashlib
import logging
import random
from typing import Any

import developer_config
from data.models import AnswerBookResult
from utils.log_exceptions import log_exceptions


class AnswerBookService:
    CACHE_KEY_PREFIX = "answerbook:last"
    FALLBACK_ANSWERS = (
        "可以试试，但先把问题拆小一点。",
        "现在不适合立刻下结论。",
        "答案偏向肯定，但别忽略代价。",
        "先等等，再看一轮信息。",
        "这件事值得你主动推进。",
        "别急着问第二遍，先执行一步。",
        "风险可控，可以试探性开始。",
        "先把最关键的条件补齐。",
    )

    def __init__(self, *, logger: logging.Logger, cache_service) -> None:
        self.logger = logger
        self.cache_service = cache_service
        self._client = None

    @log_exceptions(fallback=lambda: AnswerBookResult(question="", answer="这次没有翻到明确答案。", source="fallback"))
    def ask(self, question: str) -> AnswerBookResult:
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("问题不能为空。")

        cache_key = self._cache_key(normalized_question)
        try:
            response = developer_config.invoke_uapi_answerbook_operation(
                self._build_client(),
                developer_config.UAPI_ANSWERBOOK_OPERATION,
                question=normalized_question,
            )
            result = self._extract_result(response, normalized_question)
            self.cache_service.set(
                cache_key,
                result.to_dict(),
                ttl_seconds=developer_config.DEFAULT_REMOTE_DIALOG_CACHE_TTL_SECONDS,
            )
            return result
        except Exception as exc:
            self.logger.warning("Answerbook request failed: %s", exc)

        cached = self.cache_service.get(cache_key, allow_expired=True)
        if cached:
            result = AnswerBookResult.from_dict(cached)
            result.source = "cache"
            return result

        return AnswerBookResult(
            question=normalized_question,
            answer=random.choice(self.FALLBACK_ANSWERS),
            source="fallback",
        )

    def _build_client(self) -> Any:
        if self._client is not None:
            return self._client

        for module_name in ("uapi", "uapi_sdk_python"):
            try:
                module = __import__(module_name, fromlist=["UapiClient"])
                client_class = getattr(module, "UapiClient", None)
                if client_class is None:
                    continue
                self._client = client_class(
                    base_url=developer_config.UAPI_BASE_URL,
                    token=developer_config.UAPI_TOKEN,
                    timeout=developer_config.UAPI_TIMEOUT,
                )
                return self._client
            except ImportError:
                continue

        raise RuntimeError("UAPI Python SDK is not installed.")

    def _extract_result(self, payload: Any, question: str) -> AnswerBookResult:
        if isinstance(payload, dict):
            remote_question = str(payload.get("question") or question).strip() or question
            answer = str(payload.get("answer") or payload.get("text") or "").strip()
            if answer:
                return AnswerBookResult(
                    question=remote_question,
                    answer=answer,
                    source="remote",
                )
        raise ValueError("Answerbook payload is empty.")

    @classmethod
    def _cache_key(cls, question: str) -> str:
        digest = hashlib.md5(question.encode("utf-8")).hexdigest()[:16]
        return f"{cls.CACHE_KEY_PREFIX}:{digest}"
