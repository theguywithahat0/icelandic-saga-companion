"""Convert ingestion outputs into canonical schema objects."""

from __future__ import annotations

from dataclasses import dataclass

from saga_companion.ingest.chunk_passages import Passage
from saga_companion.ingest.load_sagas import SagaText
from saga_companion.ingest.load_xml import SagaXmlBlock, SagaXmlText
from saga_companion.ingest.pipeline import IngestedSaga
from saga_companion.ingest.split_chapters import Chapter
from saga_companion.ingest.xml_pipeline import IngestedXmlSaga
from saga_companion.schemas import (
    BlockRef,
    CanonicalBlock,
    CanonicalChapter,
    CanonicalPassage,
    ChapterRef,
    PassageRef,
    SourceFormat,
    SourceRef,
    TextBlockKind,
    build_block_id,
    build_chapter_id,
    build_passage_id,
    build_source_id,
)


@dataclass(frozen=True)
class CanonicalizedSaga:
    """Canonical source, chapter, block, and passage records for one saga."""

    source: SourceRef
    chapters: list[CanonicalChapter]
    blocks: list[CanonicalBlock]
    passages: list[CanonicalPassage]


def source_ref_from_plain_text(saga: SagaText) -> SourceRef:
    """Build a canonical source reference from a plain-text saga."""
    return SourceRef(
        source_id=build_source_id(saga.id),
        source_format=SourceFormat.PLAIN_TEXT,
        filename=saga.filename,
        path=str(saga.path) if saga.path is not None else None,
        language=saga.language,
        title=saga.title,
    )


def source_ref_from_xml(saga: SagaXmlText) -> SourceRef:
    """Build a canonical source reference from a SagaDB XML saga."""
    return SourceRef(
        source_id=build_source_id(saga.id),
        source_format=SourceFormat.SAGADB_XML,
        filename=saga.filename,
        path=str(saga.path) if saga.path is not None else None,
        language=saga.metadata.language_iso or saga.metadata.language,
        title=saga.metadata.title or saga.metadata.title_orig,
    )


def canonicalize_plain_text_ingestion(ingested: IngestedSaga) -> CanonicalizedSaga:
    """Canonicalize a plain-text ingestion result."""
    source = source_ref_from_plain_text(ingested.saga)
    return CanonicalizedSaga(
        source=source,
        chapters=[
            _canonical_chapter(
                source_id=source.source_id,
                chapter=chapter,
                chapter_number=None,
                chapter_title=chapter.title,
            )
            for chapter in ingested.chapters
        ],
        blocks=[],
        passages=_canonical_passages(source.source_id, ingested.passages),
    )


def canonicalize_xml_ingestion(ingested: IngestedXmlSaga) -> CanonicalizedSaga:
    """Canonicalize a SagaDB XML ingestion result."""
    source = source_ref_from_xml(ingested.saga)
    xml_chapters_by_index = {
        index: xml_chapter
        for index, xml_chapter in enumerate(ingested.saga.chapters, start=1)
        if xml_chapter.text.strip()
    }
    chapters = [
        _canonical_chapter(
            source_id=source.source_id,
            chapter=chapter,
            chapter_number=xml_chapters_by_index[chapter.index].number or None,
            chapter_title=xml_chapters_by_index[chapter.index].title or chapter.title,
        )
        for chapter in ingested.chapters
    ]
    blocks = _canonical_blocks_from_xml(
        source_id=source.source_id,
        xml_blocks_by_chapter_index={
            chapter_index: xml_chapter.blocks
            for chapter_index, xml_chapter in xml_chapters_by_index.items()
        },
    )
    return CanonicalizedSaga(
        source=source,
        chapters=chapters,
        blocks=blocks,
        passages=_canonical_passages(source.source_id, ingested.passages),
    )


def _canonical_chapter(
    *,
    source_id: str,
    chapter: Chapter,
    chapter_number: str | None,
    chapter_title: str | None,
) -> CanonicalChapter:
    chapter_id = build_chapter_id(source_id, chapter.index)
    return CanonicalChapter(
        ref=ChapterRef(
            source_id=source_id,
            chapter_id=chapter_id,
            chapter_index=chapter.index,
            chapter_number=chapter_number,
            chapter_title=chapter_title,
        ),
        text=chapter.text,
        character_count=len(chapter.text),
    )


def _canonical_blocks_from_xml(
    *,
    source_id: str,
    xml_blocks_by_chapter_index: dict[int, list[SagaXmlBlock]],
) -> list[CanonicalBlock]:
    blocks: list[CanonicalBlock] = []
    for chapter_index, xml_blocks in xml_blocks_by_chapter_index.items():
        chapter_id = build_chapter_id(source_id, chapter_index)
        for block_index, xml_block in enumerate(xml_blocks, start=1):
            blocks.append(
                CanonicalBlock(
                    ref=BlockRef(
                        source_id=source_id,
                        chapter_id=chapter_id,
                        block_id=build_block_id(source_id, chapter_index, block_index),
                        block_index=block_index,
                        kind=_block_kind(xml_block.kind),
                    ),
                    text=xml_block.text,
                    character_count=len(xml_block.text),
                    lines=tuple(xml_block.lines),
                )
            )
    return blocks


def _canonical_passages(source_id: str, passages: list[Passage]) -> list[CanonicalPassage]:
    return [
        CanonicalPassage(
            ref=PassageRef(
                source_id=source_id,
                chapter_id=build_chapter_id(source_id, passage.chapter_index),
                passage_id=build_passage_id(
                    source_id,
                    passage.chapter_index,
                    passage.passage_index,
                ),
                passage_index=passage.passage_index,
            ),
            text=passage.text,
            character_count=passage.character_count,
        )
        for passage in passages
    ]


def _block_kind(kind: str) -> TextBlockKind:
    if kind == "paragraph":
        return TextBlockKind.PARAGRAPH
    if kind == "poetry":
        return TextBlockKind.POETRY
    return TextBlockKind.UNKNOWN
