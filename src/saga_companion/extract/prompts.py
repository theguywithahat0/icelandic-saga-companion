"""Prompt construction for future passage extraction."""

from __future__ import annotations

from dataclasses import dataclass
import json

from saga_companion.extract.schemas import EventType, RelationshipType
from saga_companion.schemas import CanonicalPassage


@dataclass(frozen=True)
class ExtractionPrompt:
    """System and user prompt text for one extraction request."""

    system: str
    user: str

    def __post_init__(self) -> None:
        _require_text(self.system, "system")
        _require_text(self.user, "user")


def build_passage_extraction_prompt(passage: CanonicalPassage) -> ExtractionPrompt:
    """Build prompts for extracting structured information from one passage."""
    system = _build_system_prompt()
    user = "\n".join(
        (
            "Extract structured saga information from this canonical passage.",
            "",
            f"source_id: {passage.ref.source_id}",
            f"chapter_id: {passage.ref.chapter_id}",
            f"passage_id: {passage.ref.passage_id}",
            "",
            "passage text:",
            passage.text,
        ),
    )
    return ExtractionPrompt(system=system, user=user)


def event_type_values() -> tuple[str, ...]:
    """Return valid event_type JSON values."""
    return tuple(event_type.value for event_type in EventType)


def relationship_type_values() -> tuple[str, ...]:
    """Return valid relationship_type JSON values."""
    return tuple(relationship_type.value for relationship_type in RelationshipType)


def expected_extraction_json_shape() -> dict[str, object]:
    """Return the expected PassageExtraction-compatible JSON object shape."""
    evidence = {
        "source_id": "string",
        "chapter_id": "string",
        "passage_id": "string",
        "quote": "exact supporting text from the passage",
        "confidence": 0.0,
    }
    return {
        "passage_id": "string",
        "people": [
            {
                "name": "string",
                "aliases": ["string"],
                "description": "string or null",
                "evidence": evidence,
            },
        ],
        "places": [
            {
                "name": "string",
                "place_type": "string or null",
                "description": "string or null",
                "evidence": evidence,
            },
        ],
        "events": [
            {
                "event_type": "one of the valid event_type values",
                "summary": "string",
                "participants": ["string"],
                "place": "string or null",
                "evidence": evidence,
            },
        ],
        "relationships": [
            {
                "subject": "string",
                "relationship_type": "one of the valid relationship_type values",
                "object": "string",
                "description": "string or null",
                "evidence": evidence,
            },
        ],
    }


def _build_system_prompt() -> str:
    shape = json.dumps(expected_extraction_json_shape(), indent=2, sort_keys=True)
    event_values = ", ".join(event_type_values())
    relationship_values = ", ".join(relationship_type_values())

    return "\n".join(
        (
            "You extract structured information from Icelandic saga passages.",
            "Extract people, places, events, and relationships from exactly one canonical passage.",
            "",
            "Use only evidence from the provided passage.",
            "Do not invent missing information.",
            "Quote exact supporting text from the passage for every extracted item.",
            "Each evidence confidence must be between 0.0 and 1.0.",
            "If nothing is found for a category, return an empty array for that category.",
            "Return JSON only, no markdown.",
            "",
            "Schema vocabulary discipline:",
            "event_type must be exactly one allowed EventType value.",
            "relationship_type must be exactly one allowed RelationshipType value.",
            "Never invent enum labels.",
            'If no exact event type fits, use event_type "other".',
            'If no exact relationship type fits, use relationship_type "other".',
            "",
            "Event and relationship mapping discipline:",
            'Helping, interceding, or protecting maps to relationship_type "alliance" or "other", never "helps".',
            'Wounding as an event maps to event_type "other".',
            'Wounding as a relationship maps to relationship_type "wounds".',
            'Attempted killing or threats must not create "killing" or "death" unless death actually occurs; use relationship_type "enmity" where appropriate.',
            "",
            "Extraction precision discipline:",
            "Avoid incidental or generic travel events unless travel, settlement, exile, voyage, or journey is central.",
            "Avoid generic places unless they are named or structurally important.",
            "Avoid pronouns or unnamed generic people as named people.",
            "",
            "Name discipline:",
            "Prefer names as written in the passage.",
            "Do not normalize names to external or Old Norse forms not present in the passage.",
            "Do not include titles like King or Earl in the canonical name unless needed for disambiguation.",
            "",
            "If a central travel action names a person and place, extract both a travel event and a travels_to relationship.",
            "If a passage says one person killed another, extract a killing event, a death event for the victim, and a kills relationship from killer to victim.",
            "If a passage says someone died without saying they were killed, extract a death event but do not invent a killing event or kills relationship.",
            "If two people marry, extract both a marriage event and a marriage relationship.",
            "",
            "The output must match this PassageExtraction JSON shape:",
            shape,
            "",
            "Every evidence object must contain these keys:",
            "source_id, chapter_id, passage_id, quote, confidence",
            "",
            f"Valid event_type values: {event_values}",
            f"Valid relationship_type values: {relationship_values}",
            "Your final visible assistant message content must contain the JSON object.",
            "Do not put the JSON only in reasoning, thinking, analysis, or hidden fields.",
            "The final visible content must start with { and end with }.",
        ),
    )


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
