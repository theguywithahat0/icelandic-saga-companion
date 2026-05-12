from pathlib import Path

from saga_companion.canonicalize import (
    CanonicalizedSaga,
    canonicalize_plain_text_ingestion,
    canonicalize_xml_ingestion,
    source_ref_from_plain_text,
    source_ref_from_xml,
)
from saga_companion.ingest import (
    Chapter,
    IngestedSaga,
    IngestedXmlSaga,
    Passage,
    SagaText,
    SagaXmlBlock,
    SagaXmlChapter,
    SagaXmlMetadata,
    SagaXmlText,
)
from saga_companion.schemas import SourceFormat, TextBlockKind


def test_plain_text_source_ref_conversion(tmp_path: Path) -> None:
    saga = _plain_text_saga(tmp_path)

    source = source_ref_from_plain_text(saga)

    assert source.source_id == "egils-saga"
    assert source.source_format is SourceFormat.PLAIN_TEXT
    assert source.filename == "egils_saga.txt"
    assert source.path == str(saga.path)
    assert source.language is None
    assert source.title == "Egils Saga"


def test_xml_source_ref_conversion_prefers_iso_language_and_title(tmp_path: Path) -> None:
    saga = _xml_saga(tmp_path)

    source = source_ref_from_xml(saga)

    assert source.source_id == "bandamanna-saga"
    assert source.source_format is SourceFormat.SAGADB_XML
    assert source.filename == "bandamanna_saga.en.xml"
    assert source.path == str(saga.path)
    assert source.language == "en"
    assert source.title == "Bandamanna saga"


def test_canonicalizing_plain_text_ingestion_creates_source_chapters_and_passages(
    tmp_path: Path,
) -> None:
    canonicalized = canonicalize_plain_text_ingestion(_plain_text_ingestion(tmp_path))

    assert isinstance(canonicalized, CanonicalizedSaga)
    assert canonicalized.source.source_id == "egils-saga"
    assert len(canonicalized.chapters) == 1
    assert canonicalized.blocks == []
    assert len(canonicalized.passages) == 1


def test_canonical_plain_text_ids_include_source_id(tmp_path: Path) -> None:
    canonicalized = canonicalize_plain_text_ingestion(_plain_text_ingestion(tmp_path))

    assert canonicalized.chapters[0].ref.chapter_id == "egils-saga:chapter:0001"
    assert (
        canonicalized.passages[0].ref.passage_id
        == "egils-saga:chapter:0001:passage:0001"
    )
    assert canonicalized.chapters[0].ref.chapter_number is None
    assert canonicalized.chapters[0].ref.chapter_title == "Chapter 1"


def test_canonicalizing_xml_ingestion_creates_source_chapters_blocks_and_passages(
    tmp_path: Path,
) -> None:
    canonicalized = canonicalize_xml_ingestion(_xml_ingestion(tmp_path))

    assert canonicalized.source.source_id == "bandamanna-saga"
    assert len(canonicalized.chapters) == 2
    assert len(canonicalized.blocks) == 3
    assert len(canonicalized.passages) == 2


def test_xml_poetry_block_becomes_poetry_kind_and_preserves_lines(
    tmp_path: Path,
) -> None:
    canonicalized = canonicalize_xml_ingestion(_xml_ingestion(tmp_path))
    poetry_block = canonicalized.blocks[1]

    assert poetry_block.ref.kind is TextBlockKind.POETRY
    assert poetry_block.lines == ("Line one.", "Line two.")
    assert poetry_block.text == "Line one.\nLine two."


def test_xml_paragraph_block_becomes_paragraph_kind(tmp_path: Path) -> None:
    canonicalized = canonicalize_xml_ingestion(_xml_ingestion(tmp_path))

    assert canonicalized.blocks[0].ref.kind is TextBlockKind.PARAGRAPH
    assert canonicalized.blocks[0].lines == ()


def test_empty_xml_chapters_are_skipped_for_canonical_chapters_and_blocks(
    tmp_path: Path,
) -> None:
    canonicalized = canonicalize_xml_ingestion(_xml_ingestion(tmp_path))

    assert [chapter.ref.chapter_index for chapter in canonicalized.chapters] == [1, 3]
    assert [block.ref.chapter_id for block in canonicalized.blocks] == [
        "bandamanna-saga:chapter:0001",
        "bandamanna-saga:chapter:0001",
        "bandamanna-saga:chapter:0003",
    ]


def test_canonical_text_character_counts_match(tmp_path: Path) -> None:
    canonicalized = canonicalize_xml_ingestion(_xml_ingestion(tmp_path))

    assert all(
        chapter.character_count == len(chapter.text)
        for chapter in canonicalized.chapters
    )
    assert all(block.character_count == len(block.text) for block in canonicalized.blocks)
    assert all(
        passage.character_count == len(passage.text)
        for passage in canonicalized.passages
    )


def test_canonicalization_does_not_write_files(tmp_path: Path) -> None:
    ingested = _xml_ingestion(tmp_path)
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    canonicalize_xml_ingestion(ingested)

    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert after == before


def test_no_ai_graph_or_database_dependencies_are_added() -> None:
    import saga_companion.canonicalize as canonicalize

    names = set(canonicalize.__dict__)

    assert "openai" not in names
    assert "pandas" not in names
    assert "networkx" not in names


def _plain_text_saga(tmp_path: Path) -> SagaText:
    text = "Plain chapter text."
    return SagaText(
        id="egils_saga",
        title="Egils Saga",
        language=None,
        filename="egils_saga.txt",
        path=tmp_path / "egils_saga.txt",
        text=text,
        character_count=len(text),
        line_count=1,
    )


def _plain_text_ingestion(tmp_path: Path) -> IngestedSaga:
    chapter = Chapter(title="Chapter 1", text="Plain chapter text.", index=1)
    passage = Passage(
        id="chapter-0001-passage-0001",
        chapter_index=1,
        passage_index=1,
        title="Chapter 1",
        text=chapter.text,
        character_count=len(chapter.text),
    )
    return IngestedSaga(
        saga=_plain_text_saga(tmp_path),
        chapters=[chapter],
        passages=[passage],
    )


def _xml_saga(tmp_path: Path) -> SagaXmlText:
    chapter_1_text = "Paragraph one.\n\nLine one.\nLine two."
    chapter_3_text = "Paragraph three."
    text = f"{chapter_1_text}\n\n{chapter_3_text}"
    return SagaXmlText(
        id="bandamanna_saga",
        metadata=SagaXmlMetadata(
            title="Bandamanna saga",
            title_orig="Bandamanna saga original",
            language="English",
            language_iso="en",
            basename="bandamanna_saga.en",
            translator=None,
            editor=None,
            translation_date=None,
            source_name=None,
            source_url=None,
            raw={"title": "Bandamanna saga", "language_iso": "en"},
        ),
        filename="bandamanna_saga.en.xml",
        path=tmp_path / "bandamanna_saga.en.xml",
        chapters=[
            SagaXmlChapter(
                number="1",
                title="Titled chapter",
                blocks=[
                    SagaXmlBlock(kind="paragraph", text="Paragraph one.", lines=[]),
                    SagaXmlBlock(
                        kind="poetry",
                        text="Line one.\nLine two.",
                        lines=["Line one.", "Line two."],
                    ),
                ],
                paragraphs=["Paragraph one."],
                text=chapter_1_text,
                character_count=len(chapter_1_text),
            ),
            SagaXmlChapter(
                number="2",
                title=None,
                blocks=[],
                paragraphs=[],
                text="",
                character_count=0,
            ),
            SagaXmlChapter(
                number="3",
                title=None,
                blocks=[
                    SagaXmlBlock(kind="paragraph", text="Paragraph three.", lines=[]),
                ],
                paragraphs=["Paragraph three."],
                text=chapter_3_text,
                character_count=len(chapter_3_text),
            ),
        ],
        text=text,
        character_count=len(text),
    )


def _xml_ingestion(tmp_path: Path) -> IngestedXmlSaga:
    saga = _xml_saga(tmp_path)
    chapters = [
        Chapter(title="Titled chapter", text=saga.chapters[0].text, index=1),
        Chapter(title="Chapter 3", text=saga.chapters[2].text, index=3),
    ]
    passages = [
        Passage(
            id="chapter-0001-passage-0001",
            chapter_index=1,
            passage_index=1,
            title="Titled chapter",
            text=chapters[0].text,
            character_count=len(chapters[0].text),
        ),
        Passage(
            id="chapter-0003-passage-0001",
            chapter_index=3,
            passage_index=1,
            title="Chapter 3",
            text=chapters[1].text,
            character_count=len(chapters[1].text),
        ),
    ]
    return IngestedXmlSaga(saga=saga, chapters=chapters, passages=passages)
