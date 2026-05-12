from pathlib import Path

import pytest

from saga_companion.ingest import SagaText, load_saga_directory, load_saga_file


def test_loads_single_language_tagged_saga_file(tmp_path: Path) -> None:
    saga_path = tmp_path / "brennu-njals_saga.en.txt"
    text = "First line.\nSecond line."
    saga_path.write_text(text, encoding="utf-8")

    saga = load_saga_file(saga_path)

    assert saga == SagaText(
        id="brennu-njals-saga",
        title="Brennu Njals Saga",
        language="en",
        filename="brennu-njals_saga.en.txt",
        path=saga_path,
        text=text,
        character_count=len(text),
        line_count=2,
    )


def test_loads_saga_file_without_language_code(tmp_path: Path) -> None:
    saga_path = tmp_path / "egils_saga.txt"
    saga_path.write_text("Saga text.", encoding="utf-8")

    saga = load_saga_file(saga_path)

    assert saga.id == "egils-saga"
    assert saga.title == "Egils Saga"
    assert saga.language is None


def test_directory_loading_returns_files_sorted_by_filename(tmp_path: Path) -> None:
    (tmp_path / "zeta_saga.txt").write_text("Zeta.", encoding="utf-8")
    (tmp_path / "alpha_saga.txt").write_text("Alpha.", encoding="utf-8")

    sagas = load_saga_directory(tmp_path)

    assert [saga.filename for saga in sagas] == ["alpha_saga.txt", "zeta_saga.txt"]


def test_directory_loading_ignores_subdirectories(tmp_path: Path) -> None:
    (tmp_path / "alpha_saga.txt").write_text("Alpha.", encoding="utf-8")
    (tmp_path / "nested_saga.txt").mkdir()

    sagas = load_saga_directory(tmp_path)

    assert [saga.filename for saga in sagas] == ["alpha_saga.txt"]


def test_missing_file_raises_file_not_found_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_saga_file(tmp_path / "missing.txt")


def test_directory_path_passed_to_load_saga_file_raises(tmp_path: Path) -> None:
    with pytest.raises(IsADirectoryError):
        load_saga_file(tmp_path)


def test_file_path_passed_to_load_saga_directory_raises(tmp_path: Path) -> None:
    saga_path = tmp_path / "egils_saga.txt"
    saga_path.write_text("Saga text.", encoding="utf-8")

    with pytest.raises(NotADirectoryError):
        load_saga_directory(saga_path)


def test_character_count_and_line_count_are_correct(tmp_path: Path) -> None:
    saga_path = tmp_path / "line_count_saga.txt"
    text = "Line one.\nLine two.\n"
    saga_path.write_text(text, encoding="utf-8")

    saga = load_saga_file(saga_path)

    assert saga.character_count == len(text)
    assert saga.line_count == len(text.splitlines())


def test_missing_directory_raises_file_not_found_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_saga_directory(tmp_path / "missing")
