from pathlib import Path

import pytest

from saga_companion.extract import (
    EventType,
    ExtractionParseError,
    PassageExtraction,
    RelationshipType,
    parse_passage_extraction_response,
)


def test_valid_json_response_parses_to_passage_extraction() -> None:
    extraction = parse_passage_extraction_response(_valid_response())

    assert isinstance(extraction, PassageExtraction)
    assert extraction.passage_id == "passage"
    assert extraction.people[0].name == "Egil"
    assert extraction.places[0].name == "Iceland"
    assert extraction.events[0].event_type is EventType.TRAVEL
    assert extraction.relationships[0].relationship_type is RelationshipType.TRAVELS_TO


def test_leading_and_trailing_whitespace_is_tolerated() -> None:
    extraction = parse_passage_extraction_response(f"\n\n  {_valid_response()}  \t")

    assert extraction.passage_id == "passage"


@pytest.mark.parametrize("raw_response", ["", "   ", "\n\t"])
def test_empty_response_raises_parse_error(raw_response: str) -> None:
    with pytest.raises(ExtractionParseError, match="empty"):
        parse_passage_extraction_response(raw_response)


def test_invalid_json_raises_parse_error() -> None:
    with pytest.raises(ExtractionParseError, match="invalid JSON"):
        parse_passage_extraction_response('{"passage_id": "passage"')


@pytest.mark.parametrize("raw_response", ["[]", '"text"', "1", "null"])
def test_non_object_top_level_json_raises_parse_error(raw_response: str) -> None:
    with pytest.raises(ExtractionParseError, match="JSON object"):
        parse_passage_extraction_response(raw_response)


def test_missing_required_field_raises_parse_error() -> None:
    raw_response = _valid_response().replace('"passage_id": "passage",', "", 1)

    with pytest.raises(ExtractionParseError, match="missing required field"):
        parse_passage_extraction_response(raw_response)


def test_unknown_enum_value_raises_parse_error() -> None:
    raw_response = _valid_response().replace('"event_type": "travel"', '"event_type": "not-real"')

    with pytest.raises(ExtractionParseError, match="unknown event_type"):
        parse_passage_extraction_response(raw_response)


def test_nested_evidence_passage_id_mismatch_raises_parse_error() -> None:
    raw_response = _valid_response().replace('"passage_id": "passage"', '"passage_id": "other"', 1)

    with pytest.raises(ExtractionParseError, match="nested evidence passage_id"):
        parse_passage_extraction_response(raw_response)


def test_parser_does_not_silently_strip_markdown_code_fences_yet() -> None:
    raw_response = f"```json\n{_valid_response()}\n```"

    with pytest.raises(ExtractionParseError, match="invalid JSON"):
        parse_passage_extraction_response(raw_response)


def test_parser_uses_stdlib_only_and_no_model_sdk_imports() -> None:
    parser_path = Path(__file__).parents[1] / "src" / "saga_companion" / "extract" / "parser.py"
    source = parser_path.read_text(encoding="utf-8")

    forbidden_imports = ("openai", "google", "langchain", "llama_index", "pydantic", "pandas")
    for forbidden_import in forbidden_imports:
        assert forbidden_import not in source


def _valid_response() -> str:
    return """
{
  "passage_id": "passage",
  "people": [
    {
      "name": "Egil",
      "aliases": ["Skallagrimsson"],
      "description": null,
      "evidence": {
        "source_id": "source",
        "chapter_id": "chapter",
        "passage_id": "passage",
        "quote": "Egil sailed to Iceland.",
        "confidence": 0.9
      }
    }
  ],
  "places": [
    {
      "name": "Iceland",
      "place_type": "region",
      "description": null,
      "evidence": {
        "source_id": "source",
        "chapter_id": "chapter",
        "passage_id": "passage",
        "quote": "Iceland",
        "confidence": 0.8
      }
    }
  ],
  "events": [
    {
      "event_type": "travel",
      "summary": "Egil sails to Iceland.",
      "participants": ["Egil"],
      "place": "Iceland",
      "evidence": {
        "source_id": "source",
        "chapter_id": "chapter",
        "passage_id": "passage",
        "quote": "Egil sailed to Iceland.",
        "confidence": 0.9
      }
    }
  ],
  "relationships": [
    {
      "subject": "Egil",
      "relationship_type": "travels_to",
      "object": "Iceland",
      "description": null,
      "evidence": {
        "source_id": "source",
        "chapter_id": "chapter",
        "passage_id": "passage",
        "quote": "Egil sailed to Iceland.",
        "confidence": 0.9
      }
    }
  ]
}
""".strip()
