import pytest

from saga_companion.extract import (
    EventType,
    ExtractionPrompt,
    RelationshipType,
    build_passage_extraction_prompt,
    event_type_values,
    expected_extraction_json_shape,
    relationship_type_values,
)
from saga_companion.schemas import CanonicalPassage, PassageRef


@pytest.mark.parametrize(
    "kwargs",
    [
        {"system": ""},
        {"system": "   "},
        {"user": ""},
        {"user": "\t"},
    ],
)
def test_extraction_prompt_rejects_empty_text(kwargs: dict[str, str]) -> None:
    values = {"system": "system", "user": "user"}
    values.update(kwargs)

    with pytest.raises(ValueError):
        ExtractionPrompt(**values)


def test_prompt_includes_passage_identifiers_and_text() -> None:
    passage = _passage()

    prompt = build_passage_extraction_prompt(passage)

    assert "source_id: egils-saga" in prompt.user
    assert "chapter_id: egils-saga:chapter:0001" in prompt.user
    assert "passage_id: egils-saga:chapter:0001:passage:0001" in prompt.user
    assert "Egil sailed to Iceland." in prompt.user


@pytest.mark.parametrize(
    "key",
    ["passage_id", "people", "places", "events", "relationships"],
)
def test_prompt_includes_required_top_level_json_keys(key: str) -> None:
    prompt = build_passage_extraction_prompt(_passage())

    assert f'"{key}"' in prompt.system


@pytest.mark.parametrize(
    "key",
    ["source_id", "chapter_id", "passage_id", "quote", "confidence"],
)
def test_prompt_includes_evidence_keys(key: str) -> None:
    prompt = build_passage_extraction_prompt(_passage())

    assert f'"{key}"' in prompt.system
    assert key in prompt.system


def test_prompt_includes_all_event_type_values() -> None:
    prompt = build_passage_extraction_prompt(_passage())

    for event_type in EventType:
        assert event_type.value in prompt.system


def test_prompt_includes_all_relationship_type_values() -> None:
    prompt = build_passage_extraction_prompt(_passage())

    for relationship_type in RelationshipType:
        assert relationship_type.value in prompt.system


def test_prompt_tells_model_to_return_json_only() -> None:
    prompt = build_passage_extraction_prompt(_passage())

    assert "Return JSON only, no markdown." in prompt.system


def test_prompt_tells_model_not_to_invent_missing_information() -> None:
    prompt = build_passage_extraction_prompt(_passage())

    assert "Do not invent missing information." in prompt.system


def test_prompt_includes_event_relationship_duplication_rules() -> None:
    prompt = build_passage_extraction_prompt(_passage())

    assert "travel event" in prompt.system
    assert "travels_to relationship" in prompt.system
    assert "killing event" in prompt.system
    assert "kills relationship" in prompt.system
    assert "marriage event" in prompt.system
    assert "marriage relationship" in prompt.system


def test_helper_enum_value_functions_return_enum_value_strings() -> None:
    assert event_type_values() == tuple(event_type.value for event_type in EventType)
    assert relationship_type_values() == tuple(
        relationship_type.value for relationship_type in RelationshipType
    )


def test_expected_json_shape_contains_extraction_categories() -> None:
    shape = expected_extraction_json_shape()

    assert "people" in shape
    assert "places" in shape
    assert "events" in shape
    assert "relationships" in shape


def _passage() -> CanonicalPassage:
    text = "Egil sailed to Iceland."
    return CanonicalPassage(
        ref=PassageRef(
            source_id="egils-saga",
            chapter_id="egils-saga:chapter:0001",
            passage_id="egils-saga:chapter:0001:passage:0001",
            passage_index=1,
        ),
        text=text,
        character_count=len(text),
    )
