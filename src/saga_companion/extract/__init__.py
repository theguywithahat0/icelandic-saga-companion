"""Entity and relationship extraction interfaces."""

from saga_companion.extract.schemas import (
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

__all__ = [
    "EventType",
    "EvidenceRef",
    "ExtractedEntityType",
    "ExtractedEvent",
    "ExtractedPerson",
    "ExtractedPlace",
    "ExtractedRelationship",
    "PassageExtraction",
    "RelationshipType",
    "empty_passage_extraction",
]
