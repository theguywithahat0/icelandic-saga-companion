import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from saga_companion.extract import (
    EventType,
    EvidenceRef,
    ExtractedEvent,
    ExtractedPerson,
    ExtractedPlace,
    ExtractedRelationship,
    PassageExtraction,
    RelationshipType,
    empty_passage_extraction,
)


class FakeClient:
    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.api_key = api_key


def test_benchmark_runner_outputs_json_report_shape(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_provider(monkeypatch)

    exit_code = benchmark_script.main(
        [
            "--benchmark-file",
            str(_fixture_path()),
            "--base-url",
            "http://localhost:11434/v1",
            "--model",
            "local-model",
            "--limit",
            "1",
        ],
    )

    report = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert report["provider"] == "openai_compatible"
    assert report["base_url"] == "http://localhost:11434/v1"
    assert report["model"] == "local-model"
    assert report["case_count"] == 1
    assert report["cases"][0]["id"] == "egil-simple-travel"
    assert report["cases"][0]["passage_id"] == "manual-source:chapter:0001:passage:0001"
    assert report["cases"][0]["score"]["people_precision"] == 1.0
    assert report["macro_average"]["people_recall"] == 1.0


def test_benchmark_runner_filters_by_case_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_provider(monkeypatch)

    report = benchmark_script.run_benchmark(
        benchmark_file=str(_fixture_path()),
        base_url="http://localhost:11434/v1",
        model="local-model",
        case_ids=["gudrun-simple-marriage"],
    )

    assert report["case_count"] == 1
    assert report["cases"][0]["id"] == "gudrun-simple-marriage"


def test_benchmark_runner_applies_limit_after_case_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)

    report = benchmark_script.run_benchmark(
        benchmark_file=str(_fixture_path()),
        base_url="http://localhost:11434/v1",
        model="local-model",
        case_ids=["egil-simple-travel", "gudrun-simple-marriage"],
        limit=1,
    )

    assert report["case_count"] == 1
    assert report["cases"][0]["id"] == "egil-simple-travel"


def test_benchmark_runner_no_cases_after_filter_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_provider(monkeypatch)

    exit_code = benchmark_script.main(
        [
            "--benchmark-file",
            str(_fixture_path()),
            "--base-url",
            "http://localhost:11434/v1",
            "--model",
            "local-model",
            "--case-id",
            "missing-case",
        ],
    )

    assert exit_code == 1
    assert "no benchmark cases remain" in capsys.readouterr().err


def test_benchmark_runner_limit_must_be_positive() -> None:
    with pytest.raises(SystemExit):
        benchmark_script.main(
            [
                "--benchmark-file",
                str(_fixture_path()),
                "--base-url",
                "http://localhost:11434/v1",
                "--model",
                "local-model",
                "--limit",
                "0",
            ],
        )


def test_benchmark_file_is_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_provider(monkeypatch)
    loaded_paths: list[str] = []
    original_loader = benchmark_script.load_benchmark_cases

    def tracking_loader(path: str) -> object:
        loaded_paths.append(path)
        return original_loader(path)

    monkeypatch.setattr(benchmark_script, "load_benchmark_cases", tracking_loader)

    benchmark_script.run_benchmark(
        benchmark_file=str(_fixture_path()),
        base_url="http://localhost:11434/v1",
        model="local-model",
        limit=1,
    )

    assert loaded_paths == [str(_fixture_path())]


def test_macro_averages_are_computed_correctly() -> None:
    score_a = benchmark_script.ExtractionScore(
        people_precision=1.0,
        people_recall=1.0,
        places_precision=0.0,
        places_recall=1.0,
        event_type_precision=1.0,
        event_type_recall=0.5,
        relationship_type_precision=1.0,
        relationship_type_recall=1.0,
    )
    score_b = benchmark_script.ExtractionScore(
        people_precision=0.0,
        people_recall=0.5,
        places_precision=1.0,
        places_recall=1.0,
        event_type_precision=0.0,
        event_type_recall=1.0,
        relationship_type_precision=1.0,
        relationship_type_recall=0.0,
    )

    average = benchmark_script.average_scores([score_a, score_b])

    assert average["people_precision"] == 0.5
    assert average["people_recall"] == 0.75
    assert average["places_precision"] == 0.5
    assert average["event_type_recall"] == 0.75
    assert average["relationship_type_recall"] == 0.5


def test_benchmark_runner_does_not_print_api_key(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SAGA_API_KEY", "secret-value")
    clients: list[FakeClient] = []

    def fake_client_factory(
        *,
        model: str,
        base_url: str,
        api_key: str | None = None,
    ) -> FakeClient:
        client = FakeClient(model=model, base_url=base_url, api_key=api_key)
        clients.append(client)
        return client

    monkeypatch.setattr(
        benchmark_script,
        "OpenAICompatibleExtractionClient",
        fake_client_factory,
    )
    monkeypatch.setattr(benchmark_script, "extract_passage", _fake_extract_passage)

    exit_code = benchmark_script.main(
        [
            "--benchmark-file",
            str(_fixture_path()),
            "--base-url",
            "http://localhost:11434/v1",
            "--model",
            "local-model",
            "--api-key-env-var",
            "SAGA_API_KEY",
            "--limit",
            "1",
        ],
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert clients[0].api_key == "secret-value"
    assert "secret-value" not in captured.out
    assert "secret-value" not in captured.err


def test_benchmark_runner_uses_no_provider_sdk_imports() -> None:
    tree = ast.parse(_script_source())

    forbidden_imports = {"openai", "google", "langchain", "llama_index", "pydantic", "pandas"}
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module.split(".", maxsplit=1)[0])

    for forbidden_import in forbidden_imports:
        assert forbidden_import not in imported_modules


def test_benchmark_runner_writes_no_files() -> None:
    tree = ast.parse(_script_source())

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id != "open"
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"write_text", "write_bytes"}


def _patch_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        benchmark_script,
        "OpenAICompatibleExtractionClient",
        FakeClient,
    )
    monkeypatch.setattr(benchmark_script, "extract_passage", _fake_extract_passage)


def _fake_extract_passage(passage: object, client: FakeClient) -> object:
    if passage.ref.passage_id.endswith("0001:passage:0001"):
        extraction = _travel_extraction(passage.ref.passage_id)
    elif passage.ref.passage_id.endswith("0002:passage:0001"):
        extraction = empty_passage_extraction(passage.ref.passage_id)
    else:
        extraction = _marriage_extraction(passage.ref.passage_id)
    return SimpleNamespace(extraction=extraction)


def _travel_extraction(passage_id: str) -> PassageExtraction:
    evidence = _evidence(passage_id, "Egil sailed to Iceland.")
    return PassageExtraction(
        passage_id=passage_id,
        people=(ExtractedPerson("Egil", (), None, evidence),),
        places=(ExtractedPlace("Iceland", None, None, evidence),),
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


def _marriage_extraction(passage_id: str) -> PassageExtraction:
    evidence = _evidence(passage_id, "Gudrun married Bolli at Laugar.")
    return PassageExtraction(
        passage_id=passage_id,
        people=(
            ExtractedPerson("Gudrun", (), None, evidence),
            ExtractedPerson("Bolli", (), None, evidence),
        ),
        places=(ExtractedPlace("Laugar", None, None, evidence),),
        events=(
            ExtractedEvent(
                EventType.MARRIAGE,
                "Gudrun marries Bolli.",
                ("Gudrun", "Bolli"),
                "Laugar",
                evidence,
            ),
        ),
        relationships=(
            ExtractedRelationship(
                "Gudrun",
                RelationshipType.MARRIAGE,
                "Bolli",
                None,
                evidence,
            ),
        ),
    )


def _evidence(passage_id: str, quote: str) -> EvidenceRef:
    return EvidenceRef(
        source_id="manual-source",
        chapter_id="manual-source:chapter:0001",
        passage_id=passage_id,
        quote=quote,
        confidence=1.0,
    )


def _fixture_path() -> Path:
    return (
        Path(__file__).parent
        / "fixtures"
        / "benchmark"
        / "tiny_extraction_benchmark.json"
    )


def _script_source() -> str:
    return _script_path().read_text(encoding="utf-8")


def _script_path() -> Path:
    return (
        Path(__file__).parents[1]
        / "tools"
        / "run_openai_compatible_benchmark.py"
    )


def _load_benchmark_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "run_openai_compatible_benchmark",
        _script_path(),
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load benchmark script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


benchmark_script = _load_benchmark_script()
