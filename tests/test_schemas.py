from dataclasses import FrozenInstanceError

import pytest

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


def test_enum_values() -> None:
    assert SourceFormat.PLAIN_TEXT.value == "plain_text"
    assert SourceFormat.SAGADB_XML.value == "sagadb_xml"
    assert TextBlockKind.PARAGRAPH.value == "paragraph"
    assert TextBlockKind.POETRY.value == "poetry"
    assert TextBlockKind.UNKNOWN.value == "unknown"


@pytest.mark.parametrize(
    ("raw_id", "expected"),
    [
        ("Brennu Njals_Saga", "brennu-njals-saga"),
        ("  egils__saga  ", "egils-saga"),
        ("--Laxdaela   Saga--", "laxdaela-saga"),
    ],
)
def test_source_id_normalization(raw_id: str, expected: str) -> None:
    assert build_source_id(raw_id) == expected


def test_chapter_block_and_passage_id_builders() -> None:
    source_id = "egils-saga"

    assert build_chapter_id(source_id, 3) == "egils-saga:chapter:0003"
    assert build_block_id(source_id, 3, 2) == "egils-saga:chapter:0003:block:0002"
    assert (
        build_passage_id(source_id, 3, 4)
        == "egils-saga:chapter:0003:passage:0004"
    )


def test_dataclasses_are_immutable() -> None:
    source = SourceRef(
        source_id="egils-saga",
        source_format=SourceFormat.PLAIN_TEXT,
        filename="egils_saga.txt",
        path=None,
        language=None,
        title="Egils Saga",
    )

    with pytest.raises(FrozenInstanceError):
        source.filename = "other.txt"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ChapterRef("source", "chapter", 0, None, None),
        lambda: BlockRef("source", "chapter", "block", 0, TextBlockKind.PARAGRAPH),
        lambda: PassageRef("source", "chapter", "passage", 0),
    ],
)
def test_invalid_indexes_raise_value_error(factory: object) -> None:
    with pytest.raises(ValueError):
        factory()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: SourceRef("", SourceFormat.PLAIN_TEXT, "file.txt", None, None, None),
        lambda: SourceRef("source", SourceFormat.PLAIN_TEXT, "", None, None, None),
        lambda: ChapterRef("", "chapter", 1, None, None),
        lambda: ChapterRef("source", "", 1, None, None),
        lambda: BlockRef("", "chapter", "block", 1, TextBlockKind.PARAGRAPH),
        lambda: BlockRef("source", "", "block", 1, TextBlockKind.PARAGRAPH),
        lambda: BlockRef("source", "chapter", "", 1, TextBlockKind.PARAGRAPH),
        lambda: PassageRef("", "chapter", "passage", 1),
        lambda: PassageRef("source", "", "passage", 1),
        lambda: PassageRef("source", "chapter", "", 1),
    ],
)
def test_empty_ids_raise_value_error(factory: object) -> None:
    with pytest.raises(ValueError):
        factory()


def test_empty_canonical_text_raises_value_error() -> None:
    with pytest.raises(ValueError):
        CanonicalChapter(
            ref=ChapterRef("source", "chapter", 1, None, None),
            text="",
            character_count=0,
        )


def test_incorrect_character_count_raises_value_error() -> None:
    with pytest.raises(ValueError):
        CanonicalPassage(
            ref=PassageRef("source", "chapter", "passage", 1),
            text="Text.",
            character_count=999,
        )


def test_canonical_block_accepts_poetry_lines_as_tuple() -> None:
    block = CanonicalBlock(
        ref=BlockRef("source", "chapter", "block", 1, TextBlockKind.POETRY),
        text="Line one.\nLine two.",
        character_count=len("Line one.\nLine two."),
        lines=("Line one.", "Line two."),
    )

    assert block.lines == ("Line one.", "Line two.")


def test_source_ref_can_represent_plain_text_and_sagadb_xml_sources() -> None:
    plain_text = SourceRef(
        source_id="egils-saga",
        source_format=SourceFormat.PLAIN_TEXT,
        filename="egils_saga.txt",
        path="sources/egils_saga.txt",
        language=None,
        title="Egils Saga",
    )
    sagadb_xml = SourceRef(
        source_id="bandamanna-saga",
        source_format=SourceFormat.SAGADB_XML,
        filename="bandamanna_saga.en.xml",
        path="sources/bandamanna_saga.en.xml",
        language="en",
        title="Bandamanna saga",
    )

    assert plain_text.source_format is SourceFormat.PLAIN_TEXT
    assert sagadb_xml.source_format is SourceFormat.SAGADB_XML
