"""Benchmark fixture loading for extraction evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from saga_companion.schemas import CanonicalPassage, PassageRef


@dataclass(frozen=True)
class BenchmarkPassage:
    """A synthetic or curated passage used in extraction benchmarks."""

    source_id: str
    chapter_id: str
    passage_id: str
    text: str

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        _require_text(self.chapter_id, "chapter_id")
        _require_text(self.passage_id, "passage_id")
        _require_text(self.text, "text")


@dataclass(frozen=True)
class ExpectedExtraction:
    """Expected extraction labels for a benchmark passage."""

    people: tuple[str, ...]
    places: tuple[str, ...]
    event_types: tuple[str, ...]
    relationship_types: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_tuple_text(self.people, "people")
        _require_tuple_text(self.places, "places")
        _require_tuple_text(self.event_types, "event_types")
        _require_tuple_text(self.relationship_types, "relationship_types")


@dataclass(frozen=True)
class BenchmarkCase:
    """One extraction benchmark case."""

    id: str
    description: str
    passage: BenchmarkPassage
    expected: ExpectedExtraction

    def __post_init__(self) -> None:
        _require_text(self.id, "id")
        _require_text(self.description, "description")


def load_benchmark_cases(path: str | Path) -> list[BenchmarkCase]:
    """Load benchmark cases from a JSON fixture file."""
    with Path(path).open(encoding="utf-8") as file:
        data: Any = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("benchmark fixture must be a JSON object")
    cases = _required_list(data, "cases")
    return [_case_from_dict(case) for case in cases]


def canonical_passage_from_benchmark_case(case: BenchmarkCase) -> CanonicalPassage:
    """Build a canonical passage from a benchmark case."""
    return CanonicalPassage(
        ref=PassageRef(
            source_id=case.passage.source_id,
            chapter_id=case.passage.chapter_id,
            passage_id=case.passage.passage_id,
            passage_index=1,
        ),
        text=case.passage.text,
        character_count=len(case.passage.text),
    )


def _case_from_dict(data: object) -> BenchmarkCase:
    if not isinstance(data, dict):
        raise ValueError("benchmark cases must be objects")
    return BenchmarkCase(
        id=_required_str(data, "id"),
        description=_required_str(data, "description"),
        passage=_passage_from_dict(_required_dict(data, "passage")),
        expected=_expected_from_dict(_required_dict(data, "expected")),
    )


def _passage_from_dict(data: dict[str, object]) -> BenchmarkPassage:
    return BenchmarkPassage(
        source_id=_required_str(data, "source_id"),
        chapter_id=_required_str(data, "chapter_id"),
        passage_id=_required_str(data, "passage_id"),
        text=_required_str(data, "text"),
    )


def _expected_from_dict(data: dict[str, object]) -> ExpectedExtraction:
    return ExpectedExtraction(
        people=_required_str_tuple(data, "people"),
        places=_required_str_tuple(data, "places"),
        event_types=_required_str_tuple(data, "event_types"),
        relationship_types=_required_str_tuple(data, "relationship_types"),
    )


def _required_value(data: dict[str, object], field_name: str) -> object:
    if field_name not in data:
        raise ValueError(f"missing required field: {field_name}")
    return data[field_name]


def _required_str(data: dict[str, object], field_name: str) -> str:
    value = _required_value(data, field_name)
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    _require_text(value, field_name)
    return value


def _required_dict(data: dict[str, object], field_name: str) -> dict[str, object]:
    value = _required_value(data, field_name)
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _required_list(data: dict[str, object], field_name: str) -> list[object]:
    value = _required_value(data, field_name)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return value


def _required_str_tuple(data: dict[str, object], field_name: str) -> tuple[str, ...]:
    values = _required_list(data, field_name)
    if not all(isinstance(value, str) for value in values):
        raise ValueError(f"{field_name} must contain only strings")
    tuple_values = tuple(values)
    _require_tuple_text(tuple_values, field_name)
    return tuple_values


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _require_tuple_text(values: tuple[str, ...], field_name: str) -> None:
    for value in values:
        _require_text(value, field_name)
