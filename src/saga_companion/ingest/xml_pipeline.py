"""SagaDB XML ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from saga_companion.ingest.chunk_passages import Passage, chunk_chapters
from saga_companion.ingest.load_xml import (
    SagaXmlText,
    load_saga_xml_directory,
    load_saga_xml_file,
)
from saga_companion.ingest.split_chapters import Chapter


@dataclass(frozen=True)
class IngestedXmlSaga:
    """A loaded XML saga with generic chapters and passages."""

    saga: SagaXmlText
    chapters: list[Chapter]
    passages: list[Passage]


def ingest_saga_xml_file(
    path: str | Path,
    *,
    encoding: str = "utf-8",
    max_characters: int = 6000,
    overlap_characters: int = 500,
) -> IngestedXmlSaga:
    """Load, convert, and passage-chunk one SagaDB XML file."""
    saga = load_saga_xml_file(path, encoding=encoding)
    return _ingest_loaded_xml_saga(
        saga,
        max_characters=max_characters,
        overlap_characters=overlap_characters,
    )


def ingest_saga_xml_directory(
    directory: str | Path,
    *,
    pattern: str = "*.xml",
    encoding: str = "utf-8",
    max_characters: int = 6000,
    overlap_characters: int = 500,
) -> list[IngestedXmlSaga]:
    """Load, convert, and passage-chunk matching SagaDB XML files."""
    sagas = load_saga_xml_directory(directory, pattern=pattern, encoding=encoding)
    return [
        _ingest_loaded_xml_saga(
            saga,
            max_characters=max_characters,
            overlap_characters=overlap_characters,
        )
        for saga in sagas
    ]


def chapters_from_xml_saga(saga: SagaXmlText) -> list[Chapter]:
    """Convert XML chapters to generic chapters for passage chunking."""
    chapters: list[Chapter] = []
    for index, xml_chapter in enumerate(saga.chapters, start=1):
        text = xml_chapter.text.strip()
        if not text:
            continue

        chapters.append(
            Chapter(
                title=_chapter_title(xml_chapter.title, xml_chapter.number, index),
                text=text,
                index=index,
            )
        )

    return chapters


def _ingest_loaded_xml_saga(
    saga: SagaXmlText,
    *,
    max_characters: int,
    overlap_characters: int,
) -> IngestedXmlSaga:
    chapters = chapters_from_xml_saga(saga)
    passages = chunk_chapters(
        chapters,
        max_characters=max_characters,
        overlap_characters=overlap_characters,
    )
    return IngestedXmlSaga(saga=saga, chapters=chapters, passages=passages)


def _chapter_title(title: str | None, number: str, index: int) -> str:
    if title:
        return title
    if number:
        return f"Chapter {number}"
    return f"Chapter {index}"
