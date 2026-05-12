import ast
from pathlib import Path

from saga_companion.benchmark import ExpectedExtraction, score_extraction
from saga_companion.extract import (
    EventType,
    EvidenceRef,
    ExtractedEvent,
    ExtractedPerson,
    ExtractedPlace,
    ExtractedRelationship,
    PassageExtraction,
    RelationshipType,
)


def test_score_extraction_gives_perfect_score_for_exact_match() -> None:
    score = score_extraction(
        ExpectedExtraction(
            people=("Egil",),
            places=("Iceland",),
            event_types=("travel",),
            relationship_types=("travels_to",),
        ),
        _extraction(),
    )

    assert score.people_precision == 1.0
    assert score.people_recall == 1.0
    assert score.places_precision == 1.0
    assert score.places_recall == 1.0
    assert score.event_type_precision == 1.0
    assert score.event_type_recall == 1.0
    assert score.relationship_type_precision == 1.0
    assert score.relationship_type_recall == 1.0


def test_score_extraction_handles_missing_predictions() -> None:
    score = score_extraction(
        ExpectedExtraction(
            people=("Egil",),
            places=("Iceland",),
            event_types=("travel",),
            relationship_types=("travels_to",),
        ),
        PassageExtraction(
            passage_id="passage",
            people=(),
            places=(),
            events=(),
            relationships=(),
        ),
    )

    assert score.people_precision == 1.0
    assert score.people_recall == 0.0
    assert score.places_precision == 1.0
    assert score.places_recall == 0.0
    assert score.event_type_precision == 1.0
    assert score.event_type_recall == 0.0
    assert score.relationship_type_precision == 1.0
    assert score.relationship_type_recall == 0.0


def test_score_extraction_handles_extra_predictions() -> None:
    score = score_extraction(
        ExpectedExtraction(
            people=(),
            places=(),
            event_types=(),
            relationship_types=(),
        ),
        _extraction(),
    )

    assert score.people_precision == 0.0
    assert score.people_recall == 1.0
    assert score.places_precision == 0.0
    assert score.places_recall == 1.0
    assert score.event_type_precision == 0.0
    assert score.event_type_recall == 1.0
    assert score.relationship_type_precision == 0.0
    assert score.relationship_type_recall == 1.0


def test_score_extraction_is_case_insensitive_for_people_and_places() -> None:
    score = score_extraction(
        ExpectedExtraction(
            people=("egil",),
            places=("iceland",),
            event_types=("travel",),
            relationship_types=("travels_to",),
        ),
        _extraction(),
    )

    assert score.people_precision == 1.0
    assert score.people_recall == 1.0
    assert score.places_precision == 1.0
    assert score.places_recall == 1.0


def test_score_extraction_scores_partial_matches() -> None:
    score = score_extraction(
        ExpectedExtraction(
            people=("Egil", "Thorolf"),
            places=("Iceland",),
            event_types=("travel", "killing"),
            relationship_types=("travels_to", "kills"),
        ),
        _extraction(),
    )

    assert score.people_precision == 1.0
    assert score.people_recall == 0.5
    assert score.event_type_precision == 1.0
    assert score.event_type_recall == 0.5
    assert score.relationship_type_precision == 1.0
    assert score.relationship_type_recall == 0.5


def test_benchmark_scoring_uses_no_provider_sdk_imports() -> None:
    imported_modules = _imported_modules()

    forbidden_imports = {"openai", "google", "langchain", "llama_index", "pydantic", "pandas"}
    for forbidden_import in forbidden_imports:
        assert forbidden_import not in imported_modules


def test_benchmark_scoring_writes_no_files() -> None:
    tree = ast.parse(_scoring_source())

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id != "open"
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"write_text", "write_bytes"}


def _extraction() -> PassageExtraction:
    evidence = EvidenceRef(
        source_id="source",
        chapter_id="chapter",
        passage_id="passage",
        quote="Egil sailed to Iceland.",
        confidence=0.9,
    )
    return PassageExtraction(
        passage_id="passage",
        people=(ExtractedPerson("Egil", (), None, evidence),),
        places=(ExtractedPlace("Iceland", "region", None, evidence),),
        events=(
            ExtractedEvent(
                EventType.TRAVEL,
                "Egil travels.",
                ("Egil",),
                "Iceland",
                evidence,
            ),
        ),
        relationships=(
            ExtractedRelationship(
                "Egil",
                RelationshipType.TRAVELS_TO,
                "Iceland",
                None,
                evidence,
            ),
        ),
    )


def _scoring_source() -> str:
    return (
        Path(__file__).parents[1]
        / "src"
        / "saga_companion"
        / "benchmark"
        / "scoring.py"
    ).read_text(encoding="utf-8")


def _imported_modules() -> set[str]:
    tree = ast.parse(_scoring_source())
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module.split(".", maxsplit=1)[0])
    return imported_modules
