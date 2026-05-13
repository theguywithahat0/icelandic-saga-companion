import ast
import json
from pathlib import Path

import pytest

from saga_companion.benchmark import (
    BenchmarkCase,
    BenchmarkPassage,
    ExpectedExtraction,
    canonical_passage_from_benchmark_case,
    load_benchmark_cases,
)
from saga_companion.extract import EventType, RelationshipType


def test_fixture_loader_loads_all_tiny_cases() -> None:
    cases = load_benchmark_cases(_fixture_path())

    assert [case.id for case in cases] == [
        "egil-simple-travel",
        "skallagrim-simple-killing",
        "gudrun-simple-marriage",
    ]
    assert cases[0].expected.people == ("Egil",)
    assert cases[1].expected.event_types == ("killing", "death")
    assert cases[1].expected.relationship_types == ("kills",)
    assert cases[2].passage.text == "Gudrun married Bolli at Laugar."


def test_real_egils_saga_fixture_loads_curated_cases() -> None:
    cases = load_benchmark_cases(_real_fixture_path())

    assert len(cases) == 13
    assert all(case.passage.source_id == "egils-saga" for case in cases)
    assert cases[0].id == "egils-saga-gold-c0001-p0001"
    assert "Ulf" in cases[0].expected.people
    assert "marriage" in cases[0].expected.event_types
    assert cases[-1].id == "egils-saga-gold-c0063-p0005"
    assert "poetry_recitation" in cases[-1].expected.event_types


def test_real_egils_saga_fixture_does_not_label_negated_service() -> None:
    cases = load_benchmark_cases(_real_fixture_path())
    yngvar_case = next(case for case in cases if case.id == "egils-saga-gold-c0020-p0001")

    assert yngvar_case.expected.relationship_types == ("kinship", "marriage")


def test_real_egils_saga_fixture_has_diverse_reviewed_labels() -> None:
    cases = load_benchmark_cases(_real_fixture_path())

    event_types = {event for case in cases for event in case.expected.event_types}
    relationship_types = {
        relationship
        for case in cases
        for relationship in case.expected.relationship_types
    }

    assert event_types >= {
        "battle",
        "death",
        "feast",
        "killing",
        "legal_case",
        "marriage",
        "poetry_recitation",
        "travel",
    }
    assert relationship_types >= {
        "alliance",
        "kills",
        "kinship",
        "marriage",
        "rules",
        "serves",
        "travels_to",
    }
    assert all(case.expected.people for case in cases)


def test_real_egils_saga_fixture_uses_schema_label_values() -> None:
    cases = load_benchmark_cases(_real_fixture_path())
    allowed_event_types = {event_type.value for event_type in EventType}
    allowed_relationship_types = {
        relationship_type.value for relationship_type in RelationshipType
    }

    for case in cases:
        assert set(case.expected.event_types) <= allowed_event_types
        assert set(case.expected.relationship_types) <= allowed_relationship_types


def test_real_egils_saga_fixture_preserves_source_provenance() -> None:
    data = json.loads(_real_fixture_path().read_text(encoding="utf-8"))

    assert data["source"] == {
        "title": "Egil's Saga",
        "repository": "https://github.com/sveinbjornt/sagadb.org",
        "source_path": "src/egils_saga.en.xml",
        "source_sha": "6c34b9e07ffb92cc9774571e47b5ce6b21398a93",
        "notes": (
            "Curated from real SagaDB XML passages; labels reviewed against the "
            "extraction schema vocabulary."
        ),
    }


def test_invalid_fixture_shape_raises_value_error(tmp_path: Path) -> None:
    fixture = tmp_path / "invalid.json"
    fixture.write_text('{"cases": [{"id": "missing-fields"}]}', encoding="utf-8")

    with pytest.raises(ValueError, match="missing required field"):
        load_benchmark_cases(fixture)


def test_benchmark_dataclasses_reject_empty_required_text() -> None:
    with pytest.raises(ValueError):
        BenchmarkPassage(
            source_id="source",
            chapter_id="chapter",
            passage_id="passage",
            text=" ",
        )
    with pytest.raises(ValueError):
        ExpectedExtraction(
            people=("Egil", ""),
            places=(),
            event_types=(),
            relationship_types=(),
        )
    with pytest.raises(ValueError):
        BenchmarkCase(
            id=" ",
            description="description",
            passage=BenchmarkPassage("source", "chapter", "passage", "Text."),
            expected=ExpectedExtraction((), (), (), ()),
        )


def test_canonical_passage_from_benchmark_case_builds_expected_passage() -> None:
    case = load_benchmark_cases(_fixture_path())[0]

    passage = canonical_passage_from_benchmark_case(case)

    assert passage.ref.source_id == "manual-source"
    assert passage.ref.chapter_id == "manual-source:chapter:0001"
    assert passage.ref.passage_id == "manual-source:chapter:0001:passage:0001"
    assert passage.ref.passage_index == 1
    assert passage.text == "Egil sailed to Iceland."
    assert passage.character_count == len("Egil sailed to Iceland.")


def test_benchmark_code_uses_no_provider_sdk_imports() -> None:
    imported_modules = _imported_modules("fixtures.py")

    forbidden_imports = {"openai", "google", "langchain", "llama_index", "pydantic", "pandas"}
    for forbidden_import in forbidden_imports:
        assert forbidden_import not in imported_modules


def test_benchmark_code_writes_no_files() -> None:
    tree = ast.parse(_benchmark_source("fixtures.py"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id != "open"
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"write_text", "write_bytes"}


def _fixture_path() -> Path:
    return (
        Path(__file__).parent
        / "fixtures"
        / "benchmark"
        / "tiny_extraction_benchmark.json"
    )


def _real_fixture_path() -> Path:
    return (
        Path(__file__).parent
        / "fixtures"
        / "benchmark"
        / "egils_saga_real_extraction_benchmark.json"
    )


def _benchmark_source(filename: str) -> str:
    return (
        Path(__file__).parents[1]
        / "src"
        / "saga_companion"
        / "benchmark"
        / filename
    ).read_text(encoding="utf-8")


def _imported_modules(filename: str) -> set[str]:
    tree = ast.parse(_benchmark_source(filename))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module.split(".", maxsplit=1)[0])
    return imported_modules
