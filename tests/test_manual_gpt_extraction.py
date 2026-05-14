import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

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

    def generate(self, system: str, user: str) -> str:
        return "{}"


def _load_script_module() -> object:
    script_path = Path(__file__).resolve().parents[1] / "tools" / "manual_gpt_extraction.py"
    spec = importlib.util.spec_from_file_location("manual_gpt_extraction", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


manual_script = _load_script_module()


def test_manual_script_outputs_jsonl_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    passages_file = tmp_path / "passages.json"
    passages_file.write_text(
        json.dumps(
            [
                {
                    "source_id": "egils",
                    "chapter_id": "egils:chapter:0001",
                    "passage_id": "egils:chapter:0001:passage:0001",
                    "passage_index": 1,
                    "text": "Egil sailed to Iceland.",
                                    }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(manual_script, "OpenAICompatibleExtractionClient", FakeClient)
    monkeypatch.setattr(
        manual_script,
        "extract_passage",
        lambda passage, client, allow_markdown_json=False: SimpleNamespace(
            extraction=empty_passage_extraction(passage.ref.passage_id)
        ),
    )

    code = manual_script.main(
        [
            "--passages-file",
            str(passages_file),
            "--base-url",
            "https://api.openai.com/v1",
            "--model",
            "gpt-4.1",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0
    lines = [line for line in captured.out.splitlines() if line.strip()]
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["passage"]["passage_id"] == "egils:chapter:0001:passage:0001"


def test_manual_script_writes_output_file_for_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    passages_file = tmp_path / "passages.jsonl"
    passages_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "source_id": "egils",
                        "chapter_id": "egils:chapter:0001",
                        "passage_id": "egils:chapter:0001:passage:0001",
                        "text": "Egil sailed to Iceland.",
                    }
                )
            ]
        ),
        encoding="utf-8",
    )
    output_file = tmp_path / "result.json"

    monkeypatch.setattr(manual_script, "OpenAICompatibleExtractionClient", FakeClient)
    monkeypatch.setattr(
        manual_script,
        "extract_passage",
        lambda passage, client, allow_markdown_json=False: SimpleNamespace(
            extraction=empty_passage_extraction(passage.ref.passage_id)
        ),
    )

    code = manual_script.main(
        [
            "--passages-file",
            str(passages_file),
            "--base-url",
            "https://api.openai.com/v1",
            "--model",
            "gpt-4.1",
            "--output-format",
            "json",
            "--output-file",
            str(output_file),
        ]
    )

    assert code == 0
    parsed = json.loads(output_file.read_text(encoding="utf-8"))
    assert isinstance(parsed, list)
    assert parsed[0]["passage"]["source_id"] == "egils"


def test_manual_script_limit_and_progress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    passages_file = tmp_path / "passages.json"
    passages_file.write_text(
        json.dumps(
            [
                {
                    "source_id": "egils",
                    "chapter_id": "egils:chapter:0001",
                    "passage_id": "egils:chapter:0001:passage:0001",
                    "text": "A",
                },
                {
                    "source_id": "egils",
                    "chapter_id": "egils:chapter:0001",
                    "passage_id": "egils:chapter:0001:passage:0002",
                    "text": "B",
                },
            ]
        ),
        encoding="utf-8",
    )

    seen: list[str] = []

    def fake_extract(passage: object, client: object, allow_markdown_json: bool = False) -> object:
        seen.append(passage.ref.passage_id)
        return SimpleNamespace(extraction=empty_passage_extraction(passage.ref.passage_id))

    monkeypatch.setattr(manual_script, "OpenAICompatibleExtractionClient", FakeClient)
    monkeypatch.setattr(manual_script, "extract_passage", fake_extract)

    code = manual_script.main(
        [
            "--passages-file",
            str(passages_file),
            "--base-url",
            "https://api.openai.com/v1",
            "--model",
            "gpt-4.1",
            "--limit",
            "1",
            "--progress",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert seen == ["egils:chapter:0001:passage:0001"]
    assert "[1/1] started" in captured.err


def test_manual_script_uses_default_openai_api_key_env_var(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    passages_file = tmp_path / "passages.json"
    passages_file.write_text(
        json.dumps(
            [
                {
                    "source_id": "egils",
                    "chapter_id": "egils:chapter:0001",
                    "passage_id": "egils:chapter:0001:passage:0001",
                    "text": "A",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "secret-key")

    clients: list[FakeClient] = []

    def fake_client_factory(**kwargs: object) -> FakeClient:
        client = FakeClient(**kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(manual_script, "OpenAICompatibleExtractionClient", fake_client_factory)
    monkeypatch.setattr(
        manual_script,
        "extract_passage",
        lambda passage, client, allow_markdown_json=False: SimpleNamespace(
            extraction=empty_passage_extraction(passage.ref.passage_id)
        ),
    )

    code = manual_script.main(
        [
            "--passages-file",
            str(passages_file),
            "--base-url",
            "https://api.openai.com/v1",
            "--model",
            "gpt-4.1",
        ]
    )

    assert code == 0
    assert clients[0].api_key == "secret-key"
