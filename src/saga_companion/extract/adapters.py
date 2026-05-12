"""Dictionary adapters for extraction schema objects."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from saga_companion.extract.schemas import (
    EventType,
    EvidenceRef,
    ExtractedEvent,
    ExtractedPerson,
    ExtractedPlace,
    ExtractedRelationship,
    PassageExtraction,
    RelationshipType,
)


EnumT = TypeVar("EnumT", EventType, RelationshipType)


def evidence_to_dict(evidence: EvidenceRef) -> dict[str, object]:
    """Serialize evidence to a plain dictionary."""
    return {
        "source_id": evidence.source_id,
        "chapter_id": evidence.chapter_id,
        "passage_id": evidence.passage_id,
        "quote": evidence.quote,
        "confidence": evidence.confidence,
    }


def person_to_dict(person: ExtractedPerson) -> dict[str, object]:
    """Serialize an extracted person to a plain dictionary."""
    return {
        "name": person.name,
        "aliases": list(person.aliases),
        "description": person.description,
        "evidence": evidence_to_dict(person.evidence),
    }


def place_to_dict(place: ExtractedPlace) -> dict[str, object]:
    """Serialize an extracted place to a plain dictionary."""
    return {
        "name": place.name,
        "place_type": place.place_type,
        "description": place.description,
        "evidence": evidence_to_dict(place.evidence),
    }


def event_to_dict(event: ExtractedEvent) -> dict[str, object]:
    """Serialize an extracted event to a plain dictionary."""
    return {
        "event_type": event.event_type.value,
        "summary": event.summary,
        "participants": list(event.participants),
        "place": event.place,
        "evidence": evidence_to_dict(event.evidence),
    }


def relationship_to_dict(relationship: ExtractedRelationship) -> dict[str, object]:
    """Serialize an extracted relationship to a plain dictionary."""
    return {
        "subject": relationship.subject,
        "relationship_type": relationship.relationship_type.value,
        "object": relationship.object,
        "description": relationship.description,
        "evidence": evidence_to_dict(relationship.evidence),
    }


def passage_extraction_to_dict(extraction: PassageExtraction) -> dict[str, object]:
    """Serialize passage extraction results to a plain dictionary."""
    return {
        "passage_id": extraction.passage_id,
        "people": [person_to_dict(person) for person in extraction.people],
        "places": [place_to_dict(place) for place in extraction.places],
        "events": [event_to_dict(event) for event in extraction.events],
        "relationships": [
            relationship_to_dict(relationship)
            for relationship in extraction.relationships
        ],
    }


def evidence_from_dict(data: dict[str, object]) -> EvidenceRef:
    """Deserialize evidence from a plain dictionary."""
    return EvidenceRef(
        source_id=_required_str(data, "source_id"),
        chapter_id=_required_str(data, "chapter_id"),
        passage_id=_required_str(data, "passage_id"),
        quote=_required_str(data, "quote"),
        confidence=_required_float(data, "confidence"),
    )


def person_from_dict(data: dict[str, object]) -> ExtractedPerson:
    """Deserialize an extracted person from a plain dictionary."""
    return ExtractedPerson(
        name=_required_str(data, "name"),
        aliases=_required_str_tuple(data, "aliases"),
        description=_optional_str(data, "description"),
        evidence=evidence_from_dict(_required_dict(data, "evidence")),
    )


def place_from_dict(data: dict[str, object]) -> ExtractedPlace:
    """Deserialize an extracted place from a plain dictionary."""
    return ExtractedPlace(
        name=_required_str(data, "name"),
        place_type=_optional_str(data, "place_type"),
        description=_optional_str(data, "description"),
        evidence=evidence_from_dict(_required_dict(data, "evidence")),
    )


def event_from_dict(data: dict[str, object]) -> ExtractedEvent:
    """Deserialize an extracted event from a plain dictionary."""
    return ExtractedEvent(
        event_type=_required_enum(data, "event_type", EventType),
        summary=_required_str(data, "summary"),
        participants=_required_str_tuple(data, "participants"),
        place=_optional_str(data, "place"),
        evidence=evidence_from_dict(_required_dict(data, "evidence")),
    )


def relationship_from_dict(data: dict[str, object]) -> ExtractedRelationship:
    """Deserialize an extracted relationship from a plain dictionary."""
    return ExtractedRelationship(
        subject=_required_str(data, "subject"),
        relationship_type=_required_enum(
            data,
            "relationship_type",
            RelationshipType,
        ),
        object=_required_str(data, "object"),
        description=_optional_str(data, "description"),
        evidence=evidence_from_dict(_required_dict(data, "evidence")),
    )


def passage_extraction_from_dict(data: dict[str, object]) -> PassageExtraction:
    """Deserialize passage extraction results from a plain dictionary."""
    return PassageExtraction(
        passage_id=_required_str(data, "passage_id"),
        people=tuple(_items_from_list(data, "people", person_from_dict)),
        places=tuple(_items_from_list(data, "places", place_from_dict)),
        events=tuple(_items_from_list(data, "events", event_from_dict)),
        relationships=tuple(
            _items_from_list(data, "relationships", relationship_from_dict)
        ),
    )


def _required_value(data: dict[str, object], field_name: str) -> object:
    if field_name not in data:
        raise ValueError(f"missing required field: {field_name}")
    return data[field_name]


def _required_str(data: dict[str, object], field_name: str) -> str:
    value = _required_value(data, field_name)
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def _optional_str(data: dict[str, object], field_name: str) -> str | None:
    value = _required_value(data, field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or None")
    return value


def _required_float(data: dict[str, object], field_name: str) -> float:
    value = _required_value(data, field_name)
    if not isinstance(value, int | float):
        raise ValueError(f"{field_name} must be a number")
    return float(value)


def _required_dict(data: dict[str, object], field_name: str) -> dict[str, object]:
    value = _required_value(data, field_name)
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dictionary")
    return value


def _required_str_tuple(data: dict[str, object], field_name: str) -> tuple[str, ...]:
    value = _required_value(data, field_name)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must contain only strings")
    return tuple(value)


def _required_enum(
    data: dict[str, object],
    field_name: str,
    enum_type: type[EnumT],
) -> EnumT:
    value = _required_str(data, field_name)
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValueError(f"unknown {field_name}: {value}") from exc


def _items_from_list(
    data: dict[str, object],
    field_name: str,
    factory: Callable[[dict[str, object]], object],
) -> list[object]:
    value = _required_value(data, field_name)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")

    items: list[object] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{field_name} items must be dictionaries")
        items.append(factory(item))
    return items
