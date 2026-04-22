from __future__ import annotations

import logging
from typing import Any

import developer_config


class ProviderUnavailableError(RuntimeError):
    pass


class UapiDialogProvider:
    MAX_FETCH_ATTEMPTS = 3

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self._client = None

    def fetch_message(
        self,
        category: str,
        context: dict | None = None,
        excluded_texts: set[str] | None = None,
    ) -> str | None:
        if not developer_config.UAPI_TOKEN or not developer_config.UAPI_RANDOM_DIALOG_OPERATION:
            raise ProviderUnavailableError("UAPI token or operation is not configured.")

        client = self._build_client()
        excluded = set(excluded_texts or [])
        for _ in range(self.MAX_FETCH_ATTEMPTS):
            response = developer_config.invoke_uapi_dialog_operation(
                client,
                developer_config.UAPI_RANDOM_DIALOG_OPERATION,
                category=category,
                context=context or {},
            )
            text = self._extract_text(response)
            if not text:
                continue
            if text in excluded:
                continue
            return text
        raise ValueError("UAPI dialog payload is empty or duplicated.")

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

        raise ProviderUnavailableError("UAPI Python SDK is not installed.")

    def _extract_text(self, payload: Any) -> str | None:
        if payload is None:
            return None
        if isinstance(payload, str):
            return payload.strip() or None
        if isinstance(payload, dict):
            for key in ("text", "content", "message", "data", "sentence"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, dict):
                    nested = self._extract_text(value)
                    if nested:
                        return nested
            return None
        if isinstance(payload, list):
            for item in payload:
                text = self._extract_text(item)
                if text:
                    return text
        return None
