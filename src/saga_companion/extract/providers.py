"""Provider adapter boundary for future extraction model clients."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import os

from saga_companion.extract.openai_compatible import (
    OpenAICompatibleExtractionClient,
)
from saga_companion.extract.runner import ExtractionModelClient


class ProviderName(Enum):
    """Known extraction provider names."""

    MANUAL = "manual"
    GEMINI = "gemini"
    OPENAI = "openai"
    OPENAI_COMPATIBLE = "openai_compatible"


class ProviderNotConfiguredError(RuntimeError):
    """Raised when a requested extraction provider cannot be constructed."""


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration metadata for constructing an extraction model client."""

    provider: ProviderName
    model: str | None
    api_key_env_var: str | None
    base_url: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider, ProviderName):
            raise ValueError("provider must be a ProviderName")
        _require_optional_text(self.model, "model")
        _require_optional_text(self.api_key_env_var, "api_key_env_var")
        _require_optional_text(self.base_url, "base_url")


def provider_config_from_env(
    provider: ProviderName,
    *,
    model_env_var: str,
    api_key_env_var: str,
    base_url_env_var: str | None = None,
) -> ProviderConfig:
    """Build provider config from environment metadata without reading secrets."""
    return ProviderConfig(
        provider=provider,
        model=os.environ.get(model_env_var),
        api_key_env_var=api_key_env_var,
        base_url=os.environ.get(base_url_env_var) if base_url_env_var is not None else None,
    )


class ManualExtractionClient:
    """Manual response client for controlled local extraction tests."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, str]] = []

    def generate(self, system: str, user: str) -> str:
        """Return the next configured raw response."""
        self.calls.append({"system": system, "user": user})
        if not self._responses:
            raise ProviderNotConfiguredError("manual provider has no remaining responses")
        return self._responses.pop(0)


def build_extraction_client(config: ProviderConfig) -> ExtractionModelClient:
    """Build an extraction client for the requested provider."""
    if config.provider is ProviderName.MANUAL:
        return ManualExtractionClient([])
    if config.provider is ProviderName.OPENAI_COMPATIBLE:
        return openai_compatible_client_from_config(config)
    if config.provider is ProviderName.GEMINI:
        raise ProviderNotConfiguredError("Gemini extraction provider is not implemented yet")
    if config.provider is ProviderName.OPENAI:
        if config.base_url is not None:
            return openai_compatible_client_from_config(config)
        raise ProviderNotConfiguredError(
            "OpenAI extraction provider requires an OpenAI-compatible base_url"
        )
    raise ProviderNotConfiguredError(f"unsupported extraction provider: {config.provider}")


def openai_compatible_client_from_config(
    config: ProviderConfig,
) -> OpenAICompatibleExtractionClient:
    """Build an OpenAI-compatible client from provider config."""
    if config.model is None:
        raise ProviderNotConfiguredError("OpenAI-compatible provider requires a model")
    if config.base_url is None:
        raise ProviderNotConfiguredError("OpenAI-compatible provider requires a base_url")
    api_key = (
        os.environ.get(config.api_key_env_var)
        if config.api_key_env_var is not None
        else None
    )
    return OpenAICompatibleExtractionClient(
        model=config.model,
        base_url=config.base_url,
        api_key=api_key,
    )


def _require_optional_text(value: str | None, field_name: str) -> None:
    if value is not None and not value.strip():
        raise ValueError(f"{field_name} must not be empty")
