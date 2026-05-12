"""Plain-text saga ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from saga_companion.ingest.chunk_passages import Passage, chunk_chapters
from saga_companion.ingest.load_sagas import SagaText, load_saga_directory, load_saga_file
from saga_companion.ingest.split_chapters import Chapter, split_into_chapters


@dataclass(frozen=True)
class IngestedSaga:
    """A loaded saga with derived chapters and passages."""

    saga: SagaText
    chapters: list[Chapter]
    passages: list[Passage]


def ingest_saga_file(
    path: str | Path,
    *,
    encoding: str = "utf-8",
    max_characters: int = 6000,
    overlap_characters: int = 500,
) -> IngestedSaga:
    """Load, split, and passage-chunk one plain-text saga file."""
    saga = load_saga_file(path, encoding=encoding)
    return _ingest_loaded_saga(
        saga,
        max_characters=max_characters,
        overlap_characters=overlap_characters,
    )


def ingest_saga_directory(
    directory: str | Path,
    *,
    pattern: str = "*.txt",
    encoding: str = "utf-8",
    max_characters: int = 6000,
    overlap_characters: int = 500,
) -> list[IngestedSaga]:
    """Load, split, and passage-chunk matching saga files in a directory."""
    sagas = load_saga_directory(directory, pattern=pattern, encoding=encoding)
    return [
        _ingest_loaded_saga(
            saga,
            max_characters=max_characters,
            overlap_characters=overlap_characters,
        )
        for saga in sagas
    ]


def _ingest_loaded_saga(
    saga: SagaText,
    *,
    max_characters: int,
    overlap_characters: int,
) -> IngestedSaga:
    chapters = split_into_chapters(saga.text)
    passages = chunk_chapters(
        chapters,
        max_characters=max_characters,
        overlap_characters=overlap_characters,
    )
    return IngestedSaga(saga=saga, chapters=chapters, passages=passages)
