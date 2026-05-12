"""Context-safe passage chunking for saga chapters."""

from __future__ import annotations

from dataclasses import dataclass
import re

from saga_companion.ingest.split_chapters import Chapter


_PARAGRAPH_RE = re.compile(r"\n\s*\n+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Passage:
    """A context-bounded passage derived from a chapter."""

    id: str
    chapter_index: int
    passage_index: int
    title: str
    text: str
    character_count: int


@dataclass(frozen=True)
class _Piece:
    text: str
    separator: str


def chunk_chapter(
    chapter: Chapter,
    *,
    max_characters: int = 6000,
    overlap_characters: int = 500,
) -> list[Passage]:
    """Split one chapter into context-bounded passages."""
    _validate_parameters(max_characters, overlap_characters)

    chapter_text = chapter.text.strip()
    if not chapter_text:
        return []
    if len(chapter_text) <= max_characters:
        return [_build_passage(chapter, chapter_text, passage_index=1)]

    pieces = _split_into_pieces(chapter_text, max_characters)
    passage_texts = _pack_pieces(pieces, max_characters, overlap_characters)
    return [
        _build_passage(chapter, text, passage_index=index)
        for index, text in enumerate(passage_texts, start=1)
    ]


def chunk_chapters(
    chapters: list[Chapter],
    *,
    max_characters: int = 6000,
    overlap_characters: int = 500,
) -> list[Passage]:
    """Chunk chapters in order and return a flat passage list."""
    _validate_parameters(max_characters, overlap_characters)
    passages: list[Passage] = []
    for chapter in chapters:
        passages.extend(
            chunk_chapter(
                chapter,
                max_characters=max_characters,
                overlap_characters=overlap_characters,
            )
        )
    return passages


def _validate_parameters(max_characters: int, overlap_characters: int) -> None:
    if max_characters <= 0:
        raise ValueError("max_characters must be greater than 0")
    if overlap_characters < 0:
        raise ValueError("overlap_characters must be greater than or equal to 0")
    if overlap_characters >= max_characters:
        raise ValueError("overlap_characters must be less than max_characters")


def _split_into_pieces(text: str, max_characters: int) -> list[_Piece]:
    pieces: list[_Piece] = []
    for paragraph in _PARAGRAPH_RE.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        paragraph_separator = "\n\n" if pieces else ""
        if len(paragraph) <= max_characters:
            pieces.append(_Piece(text=paragraph, separator=paragraph_separator))
            continue

        sentence_pieces = _split_paragraph(paragraph, max_characters)
        for index, sentence_piece in enumerate(sentence_pieces):
            separator = paragraph_separator if index == 0 else sentence_piece.separator
            pieces.append(_Piece(text=sentence_piece.text, separator=separator))

    return pieces


def _split_paragraph(paragraph: str, max_characters: int) -> list[_Piece]:
    pieces: list[_Piece] = []
    for sentence in _SENTENCE_RE.split(paragraph):
        sentence = sentence.strip()
        if not sentence:
            continue

        sentence_separator = " " if pieces else ""
        if len(sentence) <= max_characters:
            pieces.append(_Piece(text=sentence, separator=sentence_separator))
            continue

        hard_pieces = _hard_split(sentence, max_characters)
        for index, hard_piece in enumerate(hard_pieces):
            separator = sentence_separator if index == 0 else ""
            pieces.append(_Piece(text=hard_piece, separator=separator))

    return pieces


def _hard_split(text: str, max_characters: int) -> list[str]:
    return [
        text[start : start + max_characters].strip()
        for start in range(0, len(text), max_characters)
        if text[start : start + max_characters].strip()
    ]


def _pack_pieces(
    pieces: list[_Piece],
    max_characters: int,
    overlap_characters: int,
) -> list[str]:
    passages: list[str] = []
    current = ""

    for piece in pieces:
        tentative = _append_piece(current, piece)
        if len(tentative) <= max_characters:
            current = tentative
            continue

        if current.strip():
            passages.append(current.strip())
        current = _start_next_passage(
            previous=passages[-1] if passages else "",
            piece=piece,
            max_characters=max_characters,
            overlap_characters=overlap_characters,
        )

    if current.strip():
        passages.append(current.strip())

    return passages


def _append_piece(current: str, piece: _Piece) -> str:
    if not current:
        return piece.text
    return f"{current}{piece.separator}{piece.text}"


def _start_next_passage(
    *,
    previous: str,
    piece: _Piece,
    max_characters: int,
    overlap_characters: int,
) -> str:
    piece_text = piece.text.strip()
    if overlap_characters == 0 or not previous:
        return piece_text

    overlap = previous[-overlap_characters:].strip()
    if not overlap:
        return piece_text

    separator = piece.separator if piece.separator else " "
    available_overlap = max_characters - len(separator) - len(piece_text)
    if available_overlap <= 0:
        return piece_text

    overlap = overlap[-available_overlap:].strip()
    if not overlap:
        return piece_text

    return f"{overlap}{separator}{piece_text}".strip()


def _build_passage(chapter: Chapter, text: str, passage_index: int) -> Passage:
    passage_text = text.strip()
    return Passage(
        id=f"chapter-{chapter.index:04d}-passage-{passage_index:04d}",
        chapter_index=chapter.index,
        passage_index=passage_index,
        title=chapter.title,
        text=passage_text,
        character_count=len(passage_text),
    )
