import ast
import json
from pathlib import Path
import urllib.error
import urllib.request

import pytest

from saga_companion.extract import (
    OpenAICompatibleExtractionClient,
    ProviderConfig,
    ProviderName,
    ProviderResponseError,
    build_extraction_client,
    openai_compatible_client_from_config,
)
import saga_companion.extract.openai_compatible as openai_compatible


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.body = body
        self.status = status
        self.closed = False

    def read(self) -> bytes:
        return self.body

    def close(self) -> None:
        self.closed = True


def test_openai_compatible_client_sends_expected_request_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[urllib.request.Request, float]] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        calls.append((request, timeout))
        return _response({"choices": [{"message": {"content": "raw extraction"}}]})

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)
    client = OpenAICompatibleExtractionClient(
        model="local-model",
        base_url="http://localhost:11434/v1",
        timeout_seconds=12.5,
    )

    assert client.generate(system="system prompt", user="user prompt") == "raw extraction"

    request, timeout = calls[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert request.full_url == "http://localhost:11434/v1/chat/completions"
    assert request.get_method() == "POST"
    assert timeout == 12.5
    assert payload == {
        "model": "local-model",
        "messages": [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "user prompt"},
        ],
        "temperature": 0,
    }
    assert _headers(request)["content-type"] == "application/json"


def test_authorization_header_is_included_when_api_key_is_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _captured_request(monkeypatch, api_key="secret-key")

    assert _headers(request)["authorization"] == "Bearer secret-key"


def test_authorization_header_is_omitted_when_api_key_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = _captured_request(monkeypatch, api_key=None)

    assert "authorization" not in _headers(request)


def test_openai_compatible_client_returns_choice_message_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        return _response({"choices": [{"message": {"content": "parsed text"}}]})

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)
    client = OpenAICompatibleExtractionClient(
        model="model",
        base_url="http://example.test/v1/chat/completions",
    )

    assert client.generate(system="system", user="user") == "parsed text"


def test_openai_compatible_client_raises_on_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(
        request: urllib.request.Request,
        timeout: float,
    ) -> FakeResponse:
        raise urllib.error.HTTPError(
            url=request.full_url,
            code=500,
            msg="server error",
            hdrs={},
            fp=None,
        )

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)
    client = OpenAICompatibleExtractionClient(model="model", base_url="http://example.test/v1")

    with pytest.raises(ProviderResponseError, match="HTTP error"):
        client.generate(system="system", user="user")


def test_openai_compatible_client_raises_on_non_2xx_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        return _response({"error": "bad"}, status=503)

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)
    client = OpenAICompatibleExtractionClient(model="model", base_url="http://example.test/v1")

    with pytest.raises(ProviderResponseError, match="non-2xx"):
        client.generate(system="system", user="user")


def test_openai_compatible_client_raises_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        return FakeResponse(b"not json")

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)
    client = OpenAICompatibleExtractionClient(model="model", base_url="http://example.test/v1")

    with pytest.raises(ProviderResponseError, match="invalid JSON"):
        client.generate(system="system", user="user")


@pytest.mark.parametrize(
    "response_body",
    [
        {},
        {"choices": []},
        {"choices": ["not object"]},
        {"choices": [{}]},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": None}}]},
    ],
)
def test_openai_compatible_client_raises_on_missing_response_content(
    monkeypatch: pytest.MonkeyPatch,
    response_body: dict[str, object],
) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        return _response(response_body)

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)
    client = OpenAICompatibleExtractionClient(model="model", base_url="http://example.test/v1")

    with pytest.raises(ProviderResponseError):
        client.generate(system="system", user="user")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"model": ""},
        {"model": "   "},
        {"base_url": ""},
        {"base_url": "\t"},
        {"timeout_seconds": 0},
        {"timeout_seconds": -1},
    ],
)
def test_openai_compatible_client_validates_constructor_values(
    kwargs: dict[str, object],
) -> None:
    values = {
        "model": "model",
        "base_url": "http://example.test/v1",
        "timeout_seconds": 60.0,
    }
    values.update(kwargs)

    with pytest.raises(ValueError):
        OpenAICompatibleExtractionClient(**values)


def test_openai_compatible_client_from_config_reads_api_key_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[urllib.request.Request] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        calls.append(request)
        return _response({"choices": [{"message": {"content": "raw"}}]})

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("SAGA_API_KEY", "secret-value")
    config = ProviderConfig(
        provider=ProviderName.OPENAI_COMPATIBLE,
        model="model",
        api_key_env_var="SAGA_API_KEY",
        base_url="http://example.test/v1",
    )

    client = openai_compatible_client_from_config(config)
    client.generate(system="system", user="user")

    assert not hasattr(client, "api_key")
    assert _headers(calls[0])["authorization"] == "Bearer secret-value"


def test_build_extraction_client_returns_openai_compatible_client() -> None:
    client = build_extraction_client(
        ProviderConfig(
            provider=ProviderName.OPENAI_COMPATIBLE,
            model="model",
            api_key_env_var=None,
            base_url="http://example.test/v1",
        ),
    )

    assert isinstance(client, OpenAICompatibleExtractionClient)


def test_build_extraction_client_uses_openai_compatible_for_openai_with_base_url() -> None:
    client = build_extraction_client(
        ProviderConfig(
            provider=ProviderName.OPENAI,
            model="model",
            api_key_env_var=None,
            base_url="http://example.test/v1",
        ),
    )

    assert isinstance(client, OpenAICompatibleExtractionClient)


def test_build_extraction_client_does_not_make_network_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        raise AssertionError("construction must not make a network call")

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)

    build_extraction_client(
        ProviderConfig(
            provider=ProviderName.OPENAI_COMPATIBLE,
            model="model",
            api_key_env_var=None,
            base_url="http://example.test/v1",
        ),
    )


def test_openai_compatible_code_uses_no_provider_sdk_imports() -> None:
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


def test_openai_compatible_code_writes_no_files() -> None:
    source = _provider_source()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in {"open", "Path"}
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"write_text", "write_bytes"}


def _captured_request(
    monkeypatch: pytest.MonkeyPatch,
    *,
    api_key: str | None,
) -> urllib.request.Request:
    calls: list[urllib.request.Request] = []

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        calls.append(request)
        return _response({"choices": [{"message": {"content": "raw"}}]})

    monkeypatch.setattr(openai_compatible.urllib.request, "urlopen", fake_urlopen)
    client = OpenAICompatibleExtractionClient(
        model="model",
        base_url="http://example.test/v1",
        api_key=api_key,
    )
    client.generate(system="system", user="user")
    return calls[0]


def _headers(request: urllib.request.Request) -> dict[str, str]:
    return {key.lower(): value for key, value in request.header_items()}


def _response(body: dict[str, object], status: int = 200) -> FakeResponse:
    return FakeResponse(json.dumps(body).encode("utf-8"), status=status)


def _provider_source() -> str:
    provider_path = (
        Path(__file__).parents[1]
        / "src"
        / "saga_companion"
        / "extract"
        / "openai_compatible.py"
    )
    return provider_path.read_text(encoding="utf-8")
