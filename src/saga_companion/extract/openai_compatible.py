"""OpenAI-compatible HTTP extraction client."""

from __future__ import annotations

import json
from typing import Any
import urllib.error
import urllib.request


class ProviderResponseError(RuntimeError):
    """Raised when a provider response cannot be used as extraction text."""


class OpenAICompatibleExtractionClient:
    """Extraction client for OpenAI-compatible chat completions endpoints."""

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        _require_text(model, "model")
        _require_text(base_url, "base_url")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")

        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def generate(self, system: str, user: str) -> str:
        """Return generated extraction text from a chat completions response."""
        request = self._build_request(system=system, user=user)
        try:
            response = urllib.request.urlopen(request, timeout=self.timeout_seconds)
            try:
                status = getattr(response, "status", getattr(response, "code", 200))
                body = response.read()
            finally:
                close = getattr(response, "close", None)
                if close is not None:
                    close()
        except urllib.error.HTTPError as exc:
            raise ProviderResponseError(f"provider HTTP error: {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise ProviderResponseError(f"provider request failed: {exc.reason}") from exc

        if not 200 <= int(status) < 300:
            raise ProviderResponseError(f"provider returned non-2xx status: {status}")

        try:
            data: Any = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderResponseError("provider returned invalid JSON") from exc

        return _response_content(data)

    def _build_request(self, *, system: str, user: str) -> urllib.request.Request:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key is not None:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return urllib.request.Request(
            _chat_completions_url(self.base_url),
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )


def _chat_completions_url(base_url: str) -> str:
    stripped = base_url.rstrip("/")
    if stripped.endswith("/chat/completions"):
        return stripped
    return f"{stripped}/chat/completions"


def _response_content(data: Any) -> str:
    if not isinstance(data, dict):
        raise ProviderResponseError("provider response must be a JSON object")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderResponseError("provider response missing choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ProviderResponseError("provider response choice must be an object")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ProviderResponseError("provider response missing message")
    content = message.get("content")
    if not isinstance(content, str):
        raise ProviderResponseError("provider response missing message content")
    return content


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
