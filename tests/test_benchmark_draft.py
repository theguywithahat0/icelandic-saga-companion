import ast
import json
from pathlib import Path

import pytest

from saga_companion.benchmark import (
    DraftSelectionRule,
    benchmark_cases_to_json_dict,
    default_draft_selection_rules,
    draft_benchmark_cases_from_ingested_xml,
    load_benchmark_cases,
)
from saga_companion.ingest import ingest_saga_xml_file


def test_default_rules_include_expected_topics() -> None:
    rule_names = {rule.name for rule in default_draft_selection_rules()}

    assert rule_names == {
        "travel",
        "killing-death",
        "marriage",
        "kinship",
        "legal-case",
        "feast",
        "dream-prophecy",
        "poetry",
    }


def test_selection_finds_matching_passages_case_insensitively(tmp_path: Path) -> None:
    ingested = _ingest_xml(
        tmp_path,
        """
        <chapter number="1"><paragraph>Egil SAILED west.</paragraph></chapter>
        <chapter number="2"><paragraph>Nothing relevant happens.</paragraph></chapter>
        """,
    )

    cases = draft_benchmark_cases_from_ingested_xml(ingested)

    assert [case.id for case in cases] == ["egils-saga-travel-0001"]
    assert cases[0].passage.text == "Egil SAILED west."
    assert "Saga egils-saga" in cases[0].description
    assert "matched rule travel" in cases[0].description
    assert "passage title Chapter 1" in cases[0].description


def test_selected_cases_have_empty_expected_labels(tmp_path: Path) -> None:
    ingested = _ingest_xml(
        tmp_path,
        "<chapter number='1'><paragraph>Gudrun married Bolli.</paragraph></chapter>",
    )

    case = draft_benchmark_cases_from_ingested_xml(ingested)[0]

    assert case.expected.people == ()
    assert case.expected.places == ()
    assert case.expected.event_types == ()
    assert case.expected.relationship_types == ()


def test_duplicate_matching_passage_uses_first_matching_rule(tmp_path: Path) -> None:
    ingested = _ingest_xml(
        tmp_path,
        "<chapter number='1'><paragraph>Egil sailed and killed a man.</paragraph></chapter>",
    )

    cases = draft_benchmark_cases_from_ingested_xml(ingested)

    assert [case.id for case in cases] == ["egils-saga-travel-0001"]


def test_limit_is_applied_after_selection(tmp_path: Path) -> None:
    ingested = _ingest_xml(
        tmp_path,
        """
        <chapter number="1"><paragraph>No match.</paragraph></chapter>
        <chapter number="2"><paragraph>He sailed away.</paragraph></chapter>
        <chapter number="3"><paragraph>She dreamed at night.</paragraph></chapter>
        """,
    )

    cases = draft_benchmark_cases_from_ingested_xml(ingested, limit=1)

    assert len(cases) == 1
    assert cases[0].passage.text == "He sailed away."


def test_max_text_characters_truncates_passage_text(tmp_path: Path) -> None:
    ingested = _ingest_xml(
        tmp_path,
        "<chapter number='1'><paragraph>He sailed across the sea.</paragraph></chapter>",
    )

    case = draft_benchmark_cases_from_ingested_xml(
        ingested,
        max_text_characters=9,
    )[0]

    assert case.passage.text == "He sailed"


def test_invalid_limit_and_max_text_characters_raise_value_error(
    tmp_path: Path,
) -> None:
    ingested = _ingest_xml(
        tmp_path,
        "<chapter number='1'><paragraph>He sailed.</paragraph></chapter>",
    )

    with pytest.raises(ValueError, match="limit"):
        draft_benchmark_cases_from_ingested_xml(ingested, limit=0)
    with pytest.raises(ValueError, match="max_text_characters"):
        draft_benchmark_cases_from_ingested_xml(ingested, max_text_characters=0)


def test_serialization_matches_loader_shape(tmp_path: Path) -> None:
    ingested = _ingest_xml(
        tmp_path,
        "<chapter number='1'><paragraph>They held a feast.</paragraph></chapter>",
    )
    cases = draft_benchmark_cases_from_ingested_xml(ingested)
    fixture = tmp_path / "draft.json"
    fixture.write_text(
        json.dumps(benchmark_cases_to_json_dict(cases)),
        encoding="utf-8",
    )

    loaded_cases = load_benchmark_cases(fixture)

    assert loaded_cases == cases


def test_rule_validation_rejects_empty_required_text() -> None:
    with pytest.raises(ValueError, match="name"):
        DraftSelectionRule("", "description", (), (), ())
    with pytest.raises(ValueError, match="description"):
        DraftSelectionRule("name", " ", (), (), ())
    with pytest.raises(ValueError, match="keywords"):
        DraftSelectionRule("name", "description", ("",), (), ())
    with pytest.raises(ValueError, match="event_types"):
        DraftSelectionRule("name", "description", (), (" ",), ())
    with pytest.raises(ValueError, match="relationship_types"):
        DraftSelectionRule("name", "description", (), (), ("",))


def test_benchmark_draft_uses_no_provider_sdk_imports() -> None:
    imported_modules = _imported_modules("draft.py")

    forbidden_imports = {
        "openai",
        "google",
        "langchain",
        "llama_index",
        "pydantic",
        "pandas",
    }
    assert forbidden_imports.isdisjoint(imported_modules)


def test_benchmark_draft_makes_no_model_calls() -> None:
    tree = ast.parse(_benchmark_source("draft.py"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"generate", "chat", "complete", "create"}


def _ingest_xml(tmp_path: Path, content: str):
    xml_path = tmp_path / "egils_saga.en.xml"
    xml_path.write_text(
        f"""\
<document>
  <metadata>
    <title>Egils saga</title>
    <basename>egils_saga.en</basename>
  </metadata>
  <content>
    {content}
  </content>
</document>
""",
        encoding="utf-8",
    )
    return ingest_saga_xml_file(xml_path, max_characters=1000, overlap_characters=0)


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
