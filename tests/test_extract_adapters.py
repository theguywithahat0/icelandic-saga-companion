import pytest

from saga_companion.extract import (
    EventType,
    EvidenceRef,
    ExtractedEvent,
    ExtractedPerson,
    ExtractedPlace,
    ExtractedRelationship,
    PassageExtraction,
    RelationshipType,
    empty_passage_extraction,
    event_from_dict,
    event_to_dict,
    evidence_from_dict,
    evidence_to_dict,
    passage_extraction_from_dict,
    passage_extraction_to_dict,
    person_from_dict,
    person_to_dict,
    place_from_dict,
    place_to_dict,
    relationship_from_dict,
    relationship_to_dict,
)


def test_evidence_ref_round_trip() -> None:
    evidence = _evidence()

    assert evidence_from_dict(evidence_to_dict(evidence)) == evidence


def test_extracted_person_round_trip() -> None:
    person = ExtractedPerson("Egil", ("Skallagrimsson",), None, _evidence())

    data = person_to_dict(person)

    assert data["aliases"] == ["Skallagrimsson"]
    assert person_from_dict(data) == person


def test_extracted_place_round_trip() -> None:
    place = ExtractedPlace("Iceland", "region", None, _evidence())

    assert place_from_dict(place_to_dict(place)) == place


def test_extracted_event_round_trip_with_enum_string() -> None:
    event = ExtractedEvent(
        EventType.TRAVEL,
        "Egil travels to Iceland.",
        ("Egil",),
        "Iceland",
        _evidence(),
    )

    data = event_to_dict(event)

    assert data["event_type"] == "travel"
    assert event_from_dict(data) == event


def test_extracted_relationship_round_trip_with_enum_string() -> None:
    relationship = ExtractedRelationship(
        "Egil",
        RelationshipType.TRAVELS_TO,
        "Iceland",
        None,
        _evidence(),
    )

    data = relationship_to_dict(relationship)

    assert data["relationship_type"] == "travels_to"
    assert relationship_from_dict(data) == relationship


def test_passage_extraction_round_trip_with_all_categories_populated() -> None:
    extraction = _full_extraction()

    data = passage_extraction_to_dict(extraction)

    assert data["people"]
    assert data["places"]
    assert data["events"]
    assert data["relationships"]
    assert passage_extraction_from_dict(data) == extraction


def test_empty_passage_extraction_round_trip() -> None:
    extraction = empty_passage_extraction("passage")

    assert passage_extraction_from_dict(passage_extraction_to_dict(extraction)) == extraction


def test_unknown_event_type_raises_value_error() -> None:
    data = event_to_dict(_full_extraction().events[0])
    data["event_type"] = "not-an-event"

    with pytest.raises(ValueError, match="unknown event_type"):
        event_from_dict(data)


def test_unknown_relationship_type_raises_value_error() -> None:
    data = relationship_to_dict(_full_extraction().relationships[0])
    data["relationship_type"] = "not-a-relationship"

    with pytest.raises(ValueError, match="unknown relationship_type"):
        relationship_from_dict(data)


def test_missing_required_field_raises_value_error() -> None:
    data = evidence_to_dict(_evidence())
    del data["quote"]

    with pytest.raises(ValueError, match="missing required field: quote"):
        evidence_from_dict(data)


def test_wrong_evidence_type_raises_value_error() -> None:
    data = person_to_dict(_full_extraction().people[0])
    data["evidence"] = "not evidence"

    with pytest.raises(ValueError, match="evidence must be a dictionary"):
        person_from_dict(data)


@pytest.mark.parametrize("field_name", ["aliases", "participants"])
def test_aliases_and_participants_wrong_type_raise_value_error(field_name: str) -> None:
    if field_name == "aliases":
        data = person_to_dict(_full_extraction().people[0])
        data[field_name] = "Egil"
        loader = person_from_dict
    else:
        data = event_to_dict(_full_extraction().events[0])
        data[field_name] = "Egil"
        loader = event_from_dict

    with pytest.raises(ValueError, match=f"{field_name} must be a list"):
        loader(data)


def test_nested_dataclass_validation_rejects_invalid_confidence() -> None:
    data = evidence_to_dict(_evidence())
    data["confidence"] = 2.0

    with pytest.raises(ValueError, match="confidence"):
        evidence_from_dict(data)


def test_nested_dataclass_validation_rejects_mismatched_passage_id() -> None:
    data = passage_extraction_to_dict(_full_extraction())
    data["people"][0]["evidence"]["passage_id"] = "other"

    with pytest.raises(ValueError, match="nested evidence passage_id"):
        passage_extraction_from_dict(data)


def _evidence() -> EvidenceRef:
    return EvidenceRef(
        source_id="source",
        chapter_id="chapter",
        passage_id="passage",
        quote="Quote.",
        confidence=0.75,
    )


def _full_extraction() -> PassageExtraction:
    return PassageExtraction(
        passage_id="passage",
        people=(ExtractedPerson("Egil", ("Skallagrimsson",), None, _evidence()),),
        places=(ExtractedPlace("Iceland", "region", None, _evidence()),),
        events=(
            ExtractedEvent(
                EventType.TRAVEL,
                "Egil travels to Iceland.",
                ("Egil",),
                "Iceland",
                _evidence(),
            ),
        ),
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
