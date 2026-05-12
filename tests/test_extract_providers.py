import ast
from pathlib import Path

import pytest

from saga_companion.extract import (
    ManualExtractionClient,
    OpenAICompatibleExtractionClient,
    ProviderConfig,
    ProviderName,
    ProviderNotConfiguredError,
    build_extraction_client,
    provider_config_from_env,
)


def test_provider_name_enum_values() -> None:
    assert ProviderName.MANUAL.value == "manual"
    assert ProviderName.GEMINI.value == "gemini"
    assert ProviderName.OPENAI.value == "openai"
    assert ProviderName.OPENAI_COMPATIBLE.value == "openai_compatible"


def test_provider_config_accepts_valid_values() -> None:
    config = ProviderConfig(
        provider=ProviderName.MANUAL,
        model="manual-model",
        api_key_env_var="MANUAL_API_KEY",
    )

    assert config.provider is ProviderName.MANUAL
    assert config.model == "manual-model"
    assert config.api_key_env_var == "MANUAL_API_KEY"
    assert config.base_url is None


def test_provider_config_requires_provider_name() -> None:
    with pytest.raises(ValueError, match="provider"):
        ProviderConfig(
            provider="manual",  # type: ignore[arg-type]
            model=None,
            api_key_env_var=None,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"model": ""},
        {"model": "   "},
        {"api_key_env_var": ""},
        {"api_key_env_var": "\t"},
        {"base_url": ""},
        {"base_url": "   "},
    ],
)
def test_provider_config_rejects_empty_optional_text(kwargs: dict[str, str]) -> None:
    values = {
        "provider": ProviderName.MANUAL,
        "model": None,
        "api_key_env_var": None,
    }
    values.update(kwargs)

    with pytest.raises(ValueError):
        ProviderConfig(**values)


def test_provider_config_from_env_reads_model_and_stores_secret_env_var_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SAGA_MODEL", "future-model")
    monkeypatch.setenv("SAGA_API_KEY", "secret-value")
    monkeypatch.setenv("SAGA_BASE_URL", "http://localhost:11434/v1")

    config = provider_config_from_env(
        ProviderName.OPENAI_COMPATIBLE,
        model_env_var="SAGA_MODEL",
        api_key_env_var="SAGA_API_KEY",
        base_url_env_var="SAGA_BASE_URL",
    )

    assert config.provider is ProviderName.OPENAI_COMPATIBLE
    assert config.model == "future-model"
    assert config.api_key_env_var == "SAGA_API_KEY"
    assert config.base_url == "http://localhost:11434/v1"
    assert config.api_key_env_var != "secret-value"


def test_provider_config_from_env_allows_absent_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SAGA_MODEL", raising=False)

    config = provider_config_from_env(
        ProviderName.OPENAI,
        model_env_var="SAGA_MODEL",
        api_key_env_var="OPENAI_API_KEY",
    )

    assert config.model is None
    assert config.api_key_env_var == "OPENAI_API_KEY"


def test_manual_extraction_client_returns_configured_responses_in_order() -> None:
    client = ManualExtractionClient(["first", "second"])

    assert client.generate(system="system 1", user="user 1") == "first"
    assert client.generate(system="system 2", user="user 2") == "second"


def test_manual_extraction_client_records_system_and_user_calls() -> None:
    client = ManualExtractionClient(["response"])

    client.generate(system="system", user="user")

    assert client.calls == [{"system": "system", "user": "user"}]


def test_manual_extraction_client_raises_when_responses_are_exhausted() -> None:
    client = ManualExtractionClient([])

    with pytest.raises(ProviderNotConfiguredError, match="no remaining responses"):
        client.generate(system="system", user="user")


def test_build_extraction_client_returns_manual_client_for_manual_provider() -> None:
    client = build_extraction_client(
        ProviderConfig(
            provider=ProviderName.MANUAL,
            model=None,
            api_key_env_var=None,
        ),
    )

    assert isinstance(client, ManualExtractionClient)


def test_build_extraction_client_returns_openai_compatible_client() -> None:
    client = build_extraction_client(
        ProviderConfig(
            provider=ProviderName.OPENAI_COMPATIBLE,
            model="local-model",
            api_key_env_var=None,
            base_url="http://localhost:11434/v1",
        ),
    )

    assert isinstance(client, OpenAICompatibleExtractionClient)


def test_build_extraction_client_raises_for_gemini() -> None:
    config = ProviderConfig(
        provider=ProviderName.GEMINI,
        model="gemini-model",
        api_key_env_var="GEMINI_API_KEY",
    )

    with pytest.raises(ProviderNotConfiguredError, match="Gemini"):
        build_extraction_client(config)


def test_build_extraction_client_raises_for_openai() -> None:
    config = ProviderConfig(
        provider=ProviderName.OPENAI,
        model="openai-model",
        api_key_env_var="OPENAI_API_KEY",
    )

    with pytest.raises(ProviderNotConfiguredError, match="OpenAI"):
        build_extraction_client(config)


def test_provider_code_uses_no_provider_sdk_imports() -> None:
    source = _provider_source()
    tree = ast.parse(source)

    forbidden_imports = {"openai", "google", "langchain", "llama_index", "pydantic", "pandas"}
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module.split(".", maxsplit=1)[0])

    for forbidden_import in forbidden_imports:
        assert forbidden_import not in imported_modules


def test_provider_code_writes_no_files() -> None:
    source = _provider_source()

    forbidden_file_operations = (".write_text(", ".write_bytes(", "open(", "Path(")
    for forbidden_operation in forbidden_file_operations:
        assert forbidden_operation not in source


def _provider_source() -> str:
    provider_path = Path(__file__).parents[1] / "src" / "saga_companion" / "extract" / "providers.py"
    return provider_path.read_text(encoding="utf-8")
