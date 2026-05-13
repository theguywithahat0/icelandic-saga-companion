import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType

from saga_companion.benchmark import load_benchmark_cases


def test_cli_prints_json_to_stdout_when_no_output_file_is_provided(
    tmp_path: Path,
    capsys,
) -> None:
    xml_path = _write_xml(tmp_path)

    exit_code = draft_script.main(
        [
            "--xml-file",
            str(xml_path),
            "--limit",
            "1",
            "--max-characters",
            "1000",
            "--overlap-characters",
            "0",
        ]
    )

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert exit_code == 0
    assert len(data["cases"]) == 1
    assert data["cases"][0]["id"] == "egils-saga-travel-0001"
    assert captured.err == ""


def test_cli_writes_only_when_output_file_is_provided(
    tmp_path: Path,
    capsys,
) -> None:
    xml_path = _write_xml(tmp_path)
    output_path = tmp_path / "draft_real_benchmark.json"

    exit_code = draft_script.main(
        [
            "--xml-file",
            str(xml_path),
            "--output-file",
            str(output_path),
            "--limit",
            "1",
            "--max-characters",
            "1000",
            "--overlap-characters",
            "0",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["cases"]


def test_cli_without_output_file_does_not_write_files(
    tmp_path: Path,
    capsys,
) -> None:
    xml_path = _write_xml(tmp_path)
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    draft_script.main(
        [
            "--xml-file",
            str(xml_path),
            "--limit",
            "1",
            "--max-characters",
            "1000",
            "--overlap-characters",
            "0",
        ]
    )

    capsys.readouterr()
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert after == before


def test_cli_output_can_be_loaded_by_benchmark_loader(tmp_path: Path) -> None:
    xml_path = _write_xml(tmp_path)
    output_path = tmp_path / "draft.json"

    exit_code = draft_script.main(
        [
            "--xml-file",
            str(xml_path),
            "--output-file",
            str(output_path),
            "--limit",
            "2",
            "--max-characters",
            "1000",
            "--overlap-characters",
            "0",
        ]
    )

    cases = load_benchmark_cases(output_path)
    assert exit_code == 0
    assert [case.id for case in cases] == [
        "egils-saga-travel-0001",
        "egils-saga-killing-death-0001",
    ]


def test_cli_uses_no_provider_sdk_imports() -> None:
    imported_modules = _imported_modules()

    forbidden_imports = {
        "openai",
        "google",
        "langchain",
        "llama_index",
        "pydantic",
        "pandas",
    }
    assert forbidden_imports.isdisjoint(imported_modules)


def test_cli_makes_no_model_calls() -> None:
    tree = ast.parse(_script_path().read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"generate", "chat", "complete", "create"}


def _write_xml(tmp_path: Path) -> Path:
    xml_path = tmp_path / "egils_saga.en.xml"
    xml_path.write_text(
        """\
<document>
  <metadata>
    <title>Egils saga</title>
    <basename>egils_saga.en</basename>
  </metadata>
  <content>
    <chapter number="1"><paragraph>He sailed west.</paragraph></chapter>
    <chapter number="2"><paragraph>He killed a foe.</paragraph></chapter>
  </content>
</document>
""",
        encoding="utf-8",
    )
    return xml_path


def _script_path() -> Path:
    return Path(__file__).parents[1] / "tools" / "draft_real_benchmark_fixture.py"


def _load_draft_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("draft_real_benchmark_fixture", _script_path())
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load draft_real_benchmark_fixture script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _imported_modules() -> set[str]:
    tree = ast.parse(_script_path().read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module.split(".", maxsplit=1)[0])
    return imported_modules


draft_script = _load_draft_script()
