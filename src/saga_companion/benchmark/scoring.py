"""Scoring helpers for extraction benchmark results."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from saga_companion.benchmark.fixtures import ExpectedExtraction
from saga_companion.extract import PassageExtraction


@dataclass(frozen=True)
class ExtractionScore:
    """Precision and recall metrics for one extraction result."""

    people_precision: float
    people_recall: float
    places_precision: float
    places_recall: float
    event_type_precision: float
    event_type_recall: float
    relationship_type_precision: float
    relationship_type_recall: float


def score_extraction(
    expected: ExpectedExtraction,
    actual: PassageExtraction,
) -> ExtractionScore:
    """Score extracted labels against expected benchmark labels."""
    people_precision, people_recall = _precision_recall(
        _normalized_set(expected.people),
        _normalized_set(person.name for person in actual.people),
    )
    places_precision, places_recall = _precision_recall(
        _normalized_set(expected.places),
        _normalized_set(place.name for place in actual.places),
    )
    event_type_precision, event_type_recall = _precision_recall(
        set(expected.event_types),
        {event.event_type.value for event in actual.events},
    )
    relationship_type_precision, relationship_type_recall = _precision_recall(
        set(expected.relationship_types),
        {
            relationship.relationship_type.value
            for relationship in actual.relationships
        },
    )
    return ExtractionScore(
        people_precision=people_precision,
        people_recall=people_recall,
        places_precision=places_precision,
        places_recall=places_recall,
        event_type_precision=event_type_precision,
        event_type_recall=event_type_recall,
        relationship_type_precision=relationship_type_precision,
        relationship_type_recall=relationship_type_recall,
    )


def _precision_recall(expected: set[str], predicted: set[str]) -> tuple[float, float]:
    if not expected and not predicted:
        return 1.0, 1.0
    if not predicted:
        return 1.0, 0.0
    if not expected:
        return 0.0, 1.0

    true_positives = len(expected & predicted)
    return true_positives / len(predicted), true_positives / len(expected)


def _normalized_set(values: Iterable[str]) -> set[str]:
    return {value.casefold() for value in values}
