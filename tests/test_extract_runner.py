from pathlib import Path

import pytest

from saga_companion.extract import (
    ExtractionParseError,
    ExtractionResult,
    PassageExtraction,
    extract_passage,
    extract_passages,
)
from saga_companion.schemas import CanonicalPassage, PassageRef


class FakeExtractionClient:
    def __init__(
        self,
        responses: list[str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.responses = list(responses or [])
        self.error = error
        self.calls: list[dict[str, str]] = []

    def generate(self, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        if self.error is not None:
            raise self.error
        return self.responses.pop(0)


def test_fake_client_receives_generated_system_and_user_prompt() -> None:
    passage = _passage("passage-1", "Egil sailed to Iceland.")
    client = FakeExtractionClient([_valid_response("passage-1")])

    result = extract_passage(passage, client)

    assert client.calls == [{"system": result.prompt.system, "user": result.prompt.user}]
    assert "Extract people, places, events, and relationships" in client.calls[0]["system"]
    assert "passage_id: passage-1" in client.calls[0]["user"]
    assert "Egil sailed to Iceland." in client.calls[0]["user"]


def test_fake_client_raw_json_response_is_parsed_into_passage_extraction() -> None:
    client = FakeExtractionClient([_valid_response("passage-1")])

    result = extract_passage(_passage("passage-1", "Egil sailed to Iceland."), client)

    assert isinstance(result.extraction, PassageExtraction)
    assert result.extraction.passage_id == "passage-1"
    assert result.extraction.people[0].name == "Egil"


def test_extraction_result_includes_passage_prompt_raw_response_and_extraction() -> None:
    passage = _passage("passage-1", "Egil sailed to Iceland.")
    raw_response = _valid_response("passage-1")
    client = FakeExtractionClient([raw_response])

    result = extract_passage(passage, client)

    assert isinstance(result, ExtractionResult)
    assert result.passage is passage
    assert result.raw_response == raw_response
    assert result.prompt.system
    assert result.prompt.user
    assert result.extraction.passage_id == "passage-1"


def test_extract_passages_preserves_input_order() -> None:
    passages = [
        _passage("passage-1", "Egil sailed to Iceland."),
        _passage("passage-2", "Egil met Arinbjorn."),
    ]
    client = FakeExtractionClient(
        [
            _valid_response("passage-1"),
            _valid_response("passage-2"),
        ],
    )

    results = extract_passages(passages, client)

    assert [result.passage for result in results] == passages
    assert [result.extraction.passage_id for result in results] == [
        "passage-1",
        "passage-2",
    ]
    assert [call["user"] for call in client.calls] == [
        results[0].prompt.user,
        results[1].prompt.user,
    ]


def test_parser_errors_propagate() -> None:
    client = FakeExtractionClient(["not json"])

    with pytest.raises(ExtractionParseError):
        extract_passage(_passage("passage-1", "Egil sailed to Iceland."), client)




def test_non_substring_evidence_quote_raises_parse_error() -> None:
    client = FakeExtractionClient([_invalid_quote_response("passage-1")])

    with pytest.raises(ExtractionParseError, match="invalid evidence quote.*passage-1"):
        extract_passage(_passage("passage-1", "Egil sailed to Iceland."), client)

def test_client_errors_propagate() -> None:
    client = FakeExtractionClient(error=RuntimeError("client failed"))

    with pytest.raises(RuntimeError, match="client failed"):
        extract_passage(_passage("passage-1", "Egil sailed to Iceland."), client)


def test_runner_uses_no_real_model_sdk_imports() -> None:
    source = _runner_source()

    forbidden_imports = ("openai", "google", "langchain", "llama_index", "pydantic", "pandas")
    for forbidden_import in forbidden_imports:
        assert forbidden_import not in source


def test_runner_writes_no_files() -> None:
    source = _runner_source()

    forbidden_file_operations = (".write_text(", ".write_bytes(", "open(", "Path(")
    for forbidden_operation in forbidden_file_operations:
        assert forbidden_operation not in source


def _passage(passage_id: str, text: str) -> CanonicalPassage:
    return CanonicalPassage(
        ref=PassageRef(
            source_id="source",
            chapter_id="chapter",
            passage_id=passage_id,
            passage_index=1,
        ),
        text=text,
        character_count=len(text),
    )


def _valid_response(passage_id: str) -> str:
    return f"""
{{
  "passage_id": "{passage_id}",
  "people": [
    {{
      "name": "Egil",
      "aliases": [],
      "description": null,
      "evidence": {{
        "source_id": "source",
        "chapter_id": "chapter",
        "passage_id": "{passage_id}",
        "quote": "Egil",
        "confidence": 0.9
      }}
    }}
  ],
  "places": [],
  "events": [],
  "relationships": []
}}
""".strip()


def _runner_source() -> str:
    runner_path = Path(__file__).parents[1] / "src" / "saga_companion" / "extract" / "runner.py"
    return runner_path.read_text(encoding="utf-8")


def _invalid_quote_response(passage_id: str) -> str:
    return _valid_response(passage_id).replace('"quote": "Egil"', '"quote": "Egil ... Iceland"', 1)
