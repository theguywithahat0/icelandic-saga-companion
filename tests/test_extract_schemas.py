from dataclasses import FrozenInstanceError

import pytest

from saga_companion.extract import (
    EventType,
    EvidenceRef,
    ExtractedEntityType,
    ExtractedEvent,
    ExtractedPerson,
    ExtractedPlace,
    ExtractedRelationship,
    PassageExtraction,
    RelationshipType,
    empty_passage_extraction,
)


def test_enum_values() -> None:
    assert ExtractedEntityType.PERSON.value == "person"
    assert ExtractedEntityType.PLACE.value == "place"
    assert ExtractedEntityType.EVENT.value == "event"
    assert RelationshipType.KINSHIP.value == "kinship"
    assert RelationshipType.TRAVELS_TO.value == "travels_to"
    assert RelationshipType.OTHER.value == "other"
    assert EventType.LEGAL_CASE.value == "legal_case"
    assert EventType.POETRY_RECITATION.value == "poetry_recitation"
    assert EventType.OTHER.value == "other"


def test_valid_evidence_ref() -> None:
    evidence = _evidence()

    assert evidence.source_id == "source"
    assert evidence.chapter_id == "chapter"
    assert evidence.passage_id == "passage"
    assert evidence.quote == "Quote."
    assert evidence.confidence == 0.75


@pytest.mark.parametrize(
    "kwargs",
    [
        {"source_id": ""},
        {"chapter_id": " "},
        {"passage_id": ""},
        {"quote": "   "},
    ],
)
def test_evidence_ref_rejects_empty_ids_and_quote(kwargs: dict[str, str]) -> None:
    values = {
        "source_id": "source",
        "chapter_id": "chapter",
        "passage_id": "passage",
        "quote": "Quote.",
        "confidence": 0.5,
    }
    values.update(kwargs)

    with pytest.raises(ValueError):
        EvidenceRef(**values)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_evidence_ref_rejects_confidence_outside_range(confidence: float) -> None:
    with pytest.raises(ValueError):
        EvidenceRef(
            source_id="source",
            chapter_id="chapter",
            passage_id="passage",
            quote="Quote.",
            confidence=confidence,
        )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ExtractedPerson("", (), None, _evidence()),
        lambda: ExtractedPlace(" ", None, None, _evidence()),
        lambda: ExtractedEvent(EventType.OTHER, "", (), None, _evidence()),
        lambda: ExtractedRelationship("", RelationshipType.OTHER, "object", None, _evidence()),
        lambda: ExtractedRelationship("subject", RelationshipType.OTHER, " ", None, _evidence()),
    ],
)
def test_extracted_items_reject_empty_required_text(factory: object) -> None:
    with pytest.raises(ValueError):
        factory()


def test_aliases_reject_empty_values() -> None:
    with pytest.raises(ValueError):
        ExtractedPerson("Egil", ("Skallagrimsson", " "), None, _evidence())


def test_participants_reject_empty_values() -> None:
    with pytest.raises(ValueError):
        ExtractedEvent(EventType.BATTLE, "A battle occurs.", ("Egil", ""), None, _evidence())


def test_passage_extraction_accepts_matching_nested_evidence_passage_ids() -> None:
    extraction = PassageExtraction(
        passage_id="passage",
        people=(ExtractedPerson("Egil", (), None, _evidence()),),
        places=(ExtractedPlace("Iceland", "region", None, _evidence()),),
        events=(ExtractedEvent(EventType.TRAVEL, "Egil travels.", ("Egil",), "Iceland", _evidence()),),
        relationships=(
            ExtractedRelationship(
                "Egil",
                RelationshipType.TRAVELS_TO,
                "Iceland",
                None,
                _evidence(),
            ),
        ),
    )

    assert extraction.passage_id == "passage"


def test_passage_extraction_rejects_mismatched_nested_evidence_passage_ids() -> None:
    mismatched = EvidenceRef(
        source_id="source",
        chapter_id="chapter",
        passage_id="other-passage",
        quote="Quote.",
        confidence=0.75,
    )

    with pytest.raises(ValueError):
        PassageExtraction(
            passage_id="passage",
            people=(ExtractedPerson("Egil", (), None, mismatched),),
            places=(),
            events=(),
            relationships=(),
        )


def test_empty_passage_extraction_returns_empty_tuples() -> None:
    extraction = empty_passage_extraction("passage")

    assert extraction.passage_id == "passage"
    assert extraction.people == ()
    assert extraction.places == ()
    assert extraction.events == ()
    assert extraction.relationships == ()


def test_dataclasses_are_immutable() -> None:
    evidence = _evidence()

    with pytest.raises(FrozenInstanceError):
        evidence.quote = "Other."


def _evidence() -> EvidenceRef:
    return EvidenceRef(
        source_id="source",
        chapter_id="chapter",
        passage_id="passage",
        quote="Quote.",
        confidence=0.75,
    )
