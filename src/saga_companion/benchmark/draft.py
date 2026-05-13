"""Draft real-passage benchmark fixtures from ingested SagaDB XML."""

from __future__ import annotations

from dataclasses import dataclass
import re

from saga_companion.benchmark.fixtures import (
    BenchmarkCase,
    BenchmarkPassage,
    ExpectedExtraction,
)
from saga_companion.ingest.xml_pipeline import IngestedXmlSaga


@dataclass(frozen=True)
class DraftSelectionRule:
    """Keyword-based rule for selecting candidate benchmark passages."""

    name: str
    description: str
    keywords: tuple[str, ...]
    event_types: tuple[str, ...]
    relationship_types: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.name, "name")
        _require_text(self.description, "description")
        _require_tuple_text(self.keywords, "keywords")
        _require_tuple_text(self.event_types, "event_types")
        _require_tuple_text(self.relationship_types, "relationship_types")


def default_draft_selection_rules() -> tuple[DraftSelectionRule, ...]:
    """Return deterministic keyword rules for drafting candidate benchmark cases."""
    return (
        DraftSelectionRule(
            name="travel",
            description="Passages with travel or movement cues.",
            keywords=("sailed", "went", "came", "journeyed", "travelled", "traveled", "rode"),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="killing-death",
            description="Passages with killing or death cues.",
            keywords=("killed", "slew", "slay", "died", "death", "dead"),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="marriage",
            description="Passages with marriage cues.",
            keywords=("married", "wife", "husband", "wedding"),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="kinship",
            description="Passages with family relationship cues.",
            keywords=("son", "daughter", "father", "mother", "brother", "sister"),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="legal-case",
            description="Passages with legal dispute cues.",
            keywords=("law", "court", "suit", "judgment", "judgement", "outlaw"),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="feast",
            description="Passages with feast or drinking cues.",
            keywords=("feast", "ale", "banquet"),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="dream-prophecy",
            description="Passages with dream or prophecy cues.",
            keywords=("dream", "dreamed", "prophecy", "foretold"),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="poetry",
            description="Passages with poetry cues.",
            keywords=("verse", "poem", "stanza", "sang"),
            event_types=(),
            relationship_types=(),
        ),
    )


def draft_benchmark_cases_from_ingested_xml(
    ingested: IngestedXmlSaga,
    *,
    rules: tuple[DraftSelectionRule, ...] | None = None,
    limit: int | None = None,
    max_text_characters: int = 1200,
) -> list[BenchmarkCase]:
    """Draft empty-label benchmark cases from keyword-matched XML passages."""
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than 0")
    if max_text_characters <= 0:
        raise ValueError("max_text_characters must be greater than 0")

    source_id = ingested.saga.id
    selection_rules = rules if rules is not None else default_draft_selection_rules()
    cases: list[BenchmarkCase] = []

    for passage in ingested.passages:
        rule = _first_matching_rule(passage.text, selection_rules)
        if rule is None:
            continue

        chapter_id = f"{source_id}:chapter:{passage.chapter_index:04d}"
        passage_id = (
            f"{source_id}:chapter:{passage.chapter_index:04d}:"
            f"passage:{passage.passage_index:04d}"
        )
        cases.append(
            BenchmarkCase(
                id=_case_id(source_id, rule.name, passage.passage_index),
                description=_description(source_id, rule.name, passage.title),
                passage=BenchmarkPassage(
                    source_id=source_id,
                    chapter_id=chapter_id,
                    passage_id=passage_id,
                    text=passage.text[:max_text_characters],
                ),
                expected=ExpectedExtraction(
                    people=(),
                    places=(),
                    event_types=(),
                    relationship_types=(),
                ),
            )
        )
        if limit is not None and len(cases) >= limit:
            break

    return cases


def benchmark_cases_to_json_dict(cases: list[BenchmarkCase]) -> dict[str, object]:
    """Serialize benchmark cases to the fixture shape accepted by the loader."""
    return {
        "cases": [
            {
                "id": case.id,
                "description": case.description,
                "passage": {
                    "source_id": case.passage.source_id,
                    "chapter_id": case.passage.chapter_id,
                    "passage_id": case.passage.passage_id,
                    "text": case.passage.text,
                },
                "expected": {
                    "people": list(case.expected.people),
                    "places": list(case.expected.places),
                    "event_types": list(case.expected.event_types),
                    "relationship_types": list(case.expected.relationship_types),
                },
            }
            for case in cases
        ]
    }


def _first_matching_rule(
    text: str,
    rules: tuple[DraftSelectionRule, ...],
) -> DraftSelectionRule | None:
    normalized_text = text.casefold()
    for rule in rules:
        if any(keyword.casefold() in normalized_text for keyword in rule.keywords):
            return rule
    return None


def _case_id(source_id: str, rule_name: str, passage_index: int) -> str:
    return f"{_safe_id(source_id)}-{_safe_id(rule_name)}-{passage_index:04d}"


def _description(source_id: str, rule_name: str, title: str) -> str:
    description = f"Saga {source_id}; matched rule {rule_name}"
    if title.strip():
        description = f"{description}; passage title {title.strip()}"
    return description


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _require_tuple_text(values: tuple[str, ...], field_name: str) -> None:
    for value in values:
        _require_text(value, field_name)
