import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from types import ModuleType

import pytest

from saga_companion.extract import empty_passage_extraction


class FakeClient:
    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 300.0,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds


def test_smoke_script_outputs_parsed_extraction_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    clients: list[FakeClient] = []

    def fake_client_factory(
        *,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 300.0,
    ) -> FakeClient:
        client = FakeClient(
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
        clients.append(client)
        return client

    def fake_extract_passage(passage: object, client: FakeClient) -> object:
        return SimpleNamespace(extraction=empty_passage_extraction("passage-1"))

    monkeypatch.setattr(smoke_script, "OpenAICompatibleExtractionClient", fake_client_factory)
    monkeypatch.setattr(smoke_script, "extract_passage", fake_extract_passage)

    exit_code = smoke_script.main(
        [
            "--base-url",
            "http://localhost:11434/v1",
            "--model",
            "local-model",
            "--passage-id",
            "passage-1",
            "--passage-text",
            "Egil sailed to Iceland.",
            "--timeout-seconds",
            "12.5",
        ],
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output == {
        "events": [],
        "passage_id": "passage-1",
        "people": [],
        "places": [],
        "relationships": [],
    }
    assert clients[0].model == "local-model"
    assert clients[0].base_url == "http://localhost:11434/v1"
    assert clients[0].timeout_seconds == 12.5


def test_smoke_script_reads_passage_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    passage_file = tmp_path / "passage.txt"
    passage_file.write_text("Egil met Arinbjorn.", encoding="utf-8")
    seen_text: list[str] = []

    def fake_extract_passage(passage: object, client: FakeClient) -> object:
        seen_text.append(passage.text)
        return SimpleNamespace(extraction=empty_passage_extraction(passage.ref.passage_id))

    monkeypatch.setattr(smoke_script, "OpenAICompatibleExtractionClient", FakeClient)
    monkeypatch.setattr(smoke_script, "extract_passage", fake_extract_passage)

    exit_code = smoke_script.main(
        [
            "--base-url",
            "http://localhost:11434/v1",
            "--model",
            "local-model",
            "--passage-file",
            str(passage_file),
        ],
    )

    assert exit_code == 0
    assert seen_text == ["Egil met Arinbjorn."]


def test_smoke_script_defaults_timeout_to_300_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients: list[FakeClient] = []

    def fake_client_factory(
        *,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 300.0,
    ) -> FakeClient:
        client = FakeClient(
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
        clients.append(client)
        return client

    monkeypatch.setattr(smoke_script, "OpenAICompatibleExtractionClient", fake_client_factory)
    monkeypatch.setattr(
        smoke_script,
        "extract_passage",
        lambda passage, client: SimpleNamespace(
            extraction=empty_passage_extraction(passage.ref.passage_id),
        ),
    )

    exit_code = smoke_script.main(
        [
            "--base-url",
            "http://localhost:11434/v1",
            "--model",
            "local-model",
            "--passage-text",
            "Egil sailed to Iceland.",
        ],
    )

    assert exit_code == 0
    assert clients[0].timeout_seconds == 300.0


@pytest.mark.parametrize(
    "extra_args",
    [
        [],
        ["--passage-text", "text", "--passage-file", "passage.txt"],
    ],
)
def test_smoke_script_requires_exactly_one_passage_input(extra_args: list[str]) -> None:
    with pytest.raises(SystemExit):
        smoke_script.main(
            [
                "--base-url",
                "http://localhost:11434/v1",
                "--model",
                "local-model",
                *extra_args,
            ],
        )


def test_smoke_script_timeout_must_be_positive() -> None:
    with pytest.raises(SystemExit):
        smoke_script.main(
            [
                "--base-url",
                "http://localhost:11434/v1",
                "--model",
                "local-model",
                "--passage-text",
                "Egil sailed to Iceland.",
                "--timeout-seconds",
                "0",
            ],
        )


def test_smoke_script_does_not_print_api_key(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SAGA_API_KEY", "secret-value")

    def fake_extract_passage(passage: object, client: FakeClient) -> object:
        assert client.api_key == "secret-value"
        return SimpleNamespace(extraction=empty_passage_extraction(passage.ref.passage_id))

    monkeypatch.setattr(smoke_script, "OpenAICompatibleExtractionClient", FakeClient)
    monkeypatch.setattr(smoke_script, "extract_passage", fake_extract_passage)

    exit_code = smoke_script.main(
        [
            "--base-url",
            "http://localhost:11434/v1",
            "--model",
            "local-model",
            "--api-key-env-var",
            "SAGA_API_KEY",
            "--passage-text",
            "Egil sailed to Iceland.",
        ],
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "secret-value" not in captured.out
    assert "secret-value" not in captured.err


def test_smoke_script_uses_no_provider_sdk_imports() -> None:
    tree = ast.parse(_script_source())

    forbidden_imports = {"openai", "google", "langchain", "llama_index", "pydantic", "pandas"}
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module.split(".", maxsplit=1)[0])

    for forbidden_import in forbidden_imports:
        assert forbidden_import not in imported_modules


def test_smoke_script_writes_no_files() -> None:
    tree = ast.parse(_script_source())

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id != "open"
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"write_text", "write_bytes"}


def _script_source() -> str:
    return _script_path().read_text(encoding="utf-8")


def _script_path() -> Path:
    return (
        Path(__file__).parents[1]
        / "tools"
        / "smoke_openai_compatible_extraction.py"
    )


def _load_smoke_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "smoke_openai_compatible_extraction",
        _script_path(),
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load smoke script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke_script = _load_smoke_script()
