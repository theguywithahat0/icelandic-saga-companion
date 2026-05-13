"""Draft real-passage benchmark fixtures from ingested SagaDB XML."""

from __future__ import annotations

from dataclasses import dataclass
import re

from saga_companion.benchmark.fixtures import (
    BenchmarkCase,
    BenchmarkPassage,
    ExpectedExtraction,
)
from saga_companion.ingest.chunk_passages import Passage
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
            keywords=(
                "sailed",
                "went",
                "came",
                "journeyed",
                "travelled",
                "traveled",
                "rode",
                "fared",
                "journey",
                "journeying",
                "went abroad",
                "took ship",
                "ship",
            ),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="killing-death",
            description="Passages with killing or death cues.",
            keywords=(
                "killed",
                "slew",
                "slay",
                "died",
                "death",
                "dead",
                "slain",
                "slaying",
                "wounded",
                "fell",
                "corpse",
            ),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="marriage",
            description="Passages with marriage cues.",
            keywords=(
                "married",
                "wife",
                "husband",
                "wedding",
                "wed",
                "wedded",
                "betrothed",
                "bride",
            ),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="kinship",
            description="Passages with family relationship cues.",
            keywords=(
                "son",
                "daughter",
                "father",
                "mother",
                "brother",
                "sister",
                "kinsman",
                "kin",
                "foster",
                "fostered",
            ),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="legal-case",
            description="Passages with legal dispute cues.",
            keywords=(
                "law",
                "court",
                "suit",
                "judgment",
                "judgement",
                "outlaw",
                "thing",
                "althing",
                "assembly",
                "case",
                "sentence",
            ),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="feast",
            description="Passages with feast or drinking cues.",
            keywords=("feast", "ale", "banquet", "drink", "drinking", "guest", "guests"),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="dream-prophecy",
            description="Passages with dream or prophecy cues.",
            keywords=("dream", "dreamed", "prophecy", "foretold", "dreamt", "omen"),
            event_types=(),
            relationship_types=(),
        ),
        DraftSelectionRule(
            name="poetry",
            description="Passages with poetry cues.",
            keywords=("verse", "poem", "stanza", "sang", "verses", "song", "lay", "recited"),
            event_types=(),
            relationship_types=(),
        ),
    )


def draft_benchmark_cases_from_ingested_xml(
    ingested: IngestedXmlSaga,
    *,
    rules: tuple[DraftSelectionRule, ...] | None = None,
    limit: int | None = None,
    include_first_unmatched: int | None = None,
    max_text_characters: int = 1200,
) -> list[BenchmarkCase]:
    """Draft empty-label benchmark cases from keyword-matched XML passages."""
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than 0")
    if include_first_unmatched is not None and include_first_unmatched <= 0:
        raise ValueError("include_first_unmatched must be greater than 0")
    if max_text_characters <= 0:
        raise ValueError("max_text_characters must be greater than 0")

    source_id = ingested.saga.id
    selection_rules = rules if rules is not None else default_draft_selection_rules()
    cases: list[BenchmarkCase] = []
    unmatched_passages: list[Passage] = []

    for passage in ingested.passages:
        rule = _first_matching_rule(passage.text, selection_rules)
        if rule is None:
            unmatched_passages.append(passage)
            continue

        cases.append(
            _build_case(
                source_id=source_id,
                rule_name=rule.name,
                passage=passage,
                max_text_characters=max_text_characters,
            )
        )
        if limit is not None and len(cases) >= limit:
            break

    if _should_include_unmatched(
        case_count=len(cases),
        limit=limit,
        include_first_unmatched=include_first_unmatched,
    ):
        remaining_limit = None if limit is None else limit - len(cases)
        unmatched_limit = include_first_unmatched
        if remaining_limit is not None:
            unmatched_limit = min(unmatched_limit, remaining_limit)
        cases.extend(
            _build_case(
                source_id=source_id,
                rule_name="unmatched",
                passage=passage,
                max_text_characters=max_text_characters,
            )
            for passage in unmatched_passages[:unmatched_limit]
        )

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
        if any(_keyword_matches(normalized_text, keyword) for keyword in rule.keywords):
            return rule
    return None


def _keyword_matches(normalized_text: str, keyword: str) -> bool:
    escaped_keyword = re.escape(keyword.casefold())
    return re.search(rf"(?<![a-z0-9]){escaped_keyword}(?![a-z0-9])", normalized_text) is not None


def _should_include_unmatched(
    *,
    case_count: int,
    limit: int | None,
    include_first_unmatched: int | None,
) -> bool:
    if include_first_unmatched is None:
        return False
    if case_count == 0:
        return True
    if limit is not None:
        return case_count < limit
    return case_count < include_first_unmatched


def _build_case(
    *,
    source_id: str,
    rule_name: str,
    passage: Passage,
    max_text_characters: int,
) -> BenchmarkCase:
    chapter_id = f"{source_id}:chapter:{passage.chapter_index:04d}"
    passage_id = (
        f"{source_id}:chapter:{passage.chapter_index:04d}:"
        f"passage:{passage.passage_index:04d}"
    )
    return BenchmarkCase(
        id=_case_id(
            source_id,
            rule_name,
            passage.chapter_index,
            passage.passage_index,
        ),
        description=_description(source_id, rule_name, passage.title),
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


def _case_id(
    source_id: str,
    rule_name: str,
    chapter_index: int,
    passage_index: int,
) -> str:
    return (
        f"{_safe_id(source_id)}-{_safe_id(rule_name)}-"
        f"c{chapter_index:04d}-p{passage_index:04d}"
    )


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
