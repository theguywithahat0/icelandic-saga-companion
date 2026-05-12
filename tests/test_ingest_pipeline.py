from pathlib import Path

import pytest

from saga_companion.ingest import ingest_saga_directory, ingest_saga_file


def test_ingesting_one_saga_file_returns_metadata_chapters_and_passages(
    tmp_path: Path,
) -> None:
    saga_path = tmp_path / "brennu-njals_saga.en.txt"
    saga_path.write_text(
        "CHAPTER I\nFirst chapter body.\n\nCHAPTER II\nSecond chapter body.",
        encoding="utf-8",
    )

    ingested = ingest_saga_file(
        saga_path,
        max_characters=100,
        overlap_characters=0,
    )

    assert ingested.saga.id == "brennu-njals-saga"
    assert ingested.saga.title == "Brennu Njals Saga"
    assert ingested.saga.language == "en"
    assert [chapter.title for chapter in ingested.chapters] == ["CHAPTER I", "CHAPTER II"]
    assert [passage.text for passage in ingested.passages] == [
        "First chapter body.",
        "Second chapter body.",
    ]


def test_passage_chunking_respects_max_characters(tmp_path: Path) -> None:
    saga_path = tmp_path / "long_saga.txt"
    saga_path.write_text("CHAPTER 1\n" + ("A" * 20 + "\n\n") * 4, encoding="utf-8")

    ingested = ingest_saga_file(
        saga_path,
        max_characters=25,
        overlap_characters=5,
    )

    assert len(ingested.passages) > 1
    assert all(passage.character_count <= 25 for passage in ingested.passages)


def test_directory_ingestion_returns_sagas_sorted_by_filename(tmp_path: Path) -> None:
    (tmp_path / "zeta_saga.txt").write_text("CHAPTER 1\nZeta.", encoding="utf-8")
    (tmp_path / "alpha_saga.txt").write_text("CHAPTER 1\nAlpha.", encoding="utf-8")

    ingested = ingest_saga_directory(
        tmp_path,
        max_characters=100,
        overlap_characters=0,
    )

    assert [saga.saga.filename for saga in ingested] == [
        "alpha_saga.txt",
        "zeta_saga.txt",
    ]


def test_empty_text_file_returns_zero_chapters_and_zero_passages(tmp_path: Path) -> None:
    saga_path = tmp_path / "empty_saga.txt"
    saga_path.write_text("", encoding="utf-8")

    ingested = ingest_saga_file(saga_path)

    assert ingested.chapters == []
    assert ingested.passages == []


def test_missing_file_error_propagates(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ingest_saga_file(tmp_path / "missing.txt")


def test_missing_directory_error_propagates(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ingest_saga_directory(tmp_path / "missing")


def test_pipeline_does_not_create_output_files(tmp_path: Path) -> None:
    saga_path = tmp_path / "egils_saga.txt"
    saga_path.write_text("CHAPTER 1\nOnly input text.", encoding="utf-8")
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    ingest_saga_file(saga_path)

    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert after == before
