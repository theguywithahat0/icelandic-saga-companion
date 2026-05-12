"""Schema contracts for future extraction outputs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExtractedEntityType(Enum):
    """Entity categories that extraction can produce."""

    PERSON = "person"
    PLACE = "place"
    EVENT = "event"


class RelationshipType(Enum):
    """Relationship categories that extraction can produce."""

    KINSHIP = "kinship"
    MARRIAGE = "marriage"
    ALLIANCE = "alliance"
    ENMITY = "enmity"
    KILLS = "kills"
    WOUNDS = "wounds"
    AVENGES = "avenges"
    FOSTERS = "fosters"
    SERVES = "serves"
    RULES = "rules"
    OWNS = "owns"
    TRAVELS_TO = "travels_to"
    MENTIONS = "mentions"
    OTHER = "other"


class EventType(Enum):
    """Event categories that extraction can produce."""

    BIRTH = "birth"
    DEATH = "death"
    KILLING = "killing"
    BATTLE = "battle"
    MARRIAGE = "marriage"
    LEGAL_CASE = "legal_case"
    TRAVEL = "travel"
    FEAST = "feast"
    DREAM = "dream"
    PROPHECY = "prophecy"
    POETRY_RECITATION = "poetry_recitation"
    OTHER = "other"


@dataclass(frozen=True)
class EvidenceRef:
    """Evidence supporting one extracted item."""

    source_id: str
    chapter_id: str
    passage_id: str
    quote: str
    confidence: float

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        _require_text(self.chapter_id, "chapter_id")
        _require_text(self.passage_id, "passage_id")
        _require_text(self.quote, "quote")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class ExtractedPerson:
    """A person extracted from a passage."""

    name: str
    aliases: tuple[str, ...]
    description: str | None
    evidence: EvidenceRef

    def __post_init__(self) -> None:
        _require_text(self.name, "name")
        _require_non_empty_items(self.aliases, "aliases")


@dataclass(frozen=True)
class ExtractedPlace:
    """A place extracted from a passage."""

    name: str
    place_type: str | None
    description: str | None
    evidence: EvidenceRef

    def __post_init__(self) -> None:
        _require_text(self.name, "name")


@dataclass(frozen=True)
class ExtractedEvent:
    """An event extracted from a passage."""

    event_type: EventType
    summary: str
    participants: tuple[str, ...]
    place: str | None
    evidence: EvidenceRef

    def __post_init__(self) -> None:
        _require_text(self.summary, "summary")
        _require_non_empty_items(self.participants, "participants")


@dataclass(frozen=True)
class ExtractedRelationship:
    """A relationship extracted from a passage."""

    subject: str
    relationship_type: RelationshipType
    object: str
    description: str | None
    evidence: EvidenceRef

    def __post_init__(self) -> None:
        _require_text(self.subject, "subject")
        _require_text(self.object, "object")


@dataclass(frozen=True)
class PassageExtraction:
    """All extracted items for one passage."""

    passage_id: str
    people: tuple[ExtractedPerson, ...]
    places: tuple[ExtractedPlace, ...]
    events: tuple[ExtractedEvent, ...]
    relationships: tuple[ExtractedRelationship, ...]

    def __post_init__(self) -> None:
        _require_text(self.passage_id, "passage_id")
        for item in (
            *self.people,
            *self.places,
            *self.events,
            *self.relationships,
        ):
            if item.evidence.passage_id != self.passage_id:
                raise ValueError("nested evidence passage_id must match passage_id")


def empty_passage_extraction(passage_id: str) -> PassageExtraction:
    """Create an empty extraction result for a passage."""
    return PassageExtraction(
        passage_id=passage_id,
        people=(),
        places=(),
        events=(),
        relationships=(),
    )


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _require_non_empty_items(values: tuple[str, ...], field_name: str) -> None:
    for value in values:
        if not value.strip():
            raise ValueError(f"{field_name} must not contain empty values")
