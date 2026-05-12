"""Canonical source and provenance schemas."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class SourceFormat(Enum):
    """Supported source formats."""

    PLAIN_TEXT = "plain_text"
    SAGADB_XML = "sagadb_xml"


class TextBlockKind(Enum):
    """Kinds of source text blocks."""

    PARAGRAPH = "paragraph"
    POETRY = "poetry"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceRef:
    """Reference to a source text."""

    source_id: str
    source_format: SourceFormat
    filename: str
    path: str | None
    language: str | None
    title: str | None

    def __post_init__(self) -> None:
        _require_id(self.source_id, "source_id")
        _require_id(self.filename, "filename")


@dataclass(frozen=True)
class ChapterRef:
    """Reference to a chapter within a source."""

    source_id: str
    chapter_id: str
    chapter_index: int
    chapter_number: str | None
    chapter_title: str | None

    def __post_init__(self) -> None:
        _require_id(self.source_id, "source_id")
        _require_id(self.chapter_id, "chapter_id")
        _require_positive_index(self.chapter_index, "chapter_index")


@dataclass(frozen=True)
class BlockRef:
    """Reference to a text block within a chapter."""

    source_id: str
    chapter_id: str
    block_id: str
    block_index: int
    kind: TextBlockKind

    def __post_init__(self) -> None:
        _require_id(self.source_id, "source_id")
        _require_id(self.chapter_id, "chapter_id")
        _require_id(self.block_id, "block_id")
        _require_positive_index(self.block_index, "block_index")


@dataclass(frozen=True)
class PassageRef:
    """Reference to a chunked passage within a chapter."""

    source_id: str
    chapter_id: str
    passage_id: str
    passage_index: int

    def __post_init__(self) -> None:
        _require_id(self.source_id, "source_id")
        _require_id(self.chapter_id, "chapter_id")
        _require_id(self.passage_id, "passage_id")
        _require_positive_index(self.passage_index, "passage_index")


@dataclass(frozen=True)
class CanonicalChapter:
    """Canonical text-bearing chapter."""

    ref: ChapterRef
    text: str
    character_count: int

    def __post_init__(self) -> None:
        _validate_text(self.text, self.character_count)


@dataclass(frozen=True)
class CanonicalBlock:
    """Canonical text-bearing chapter block."""

    ref: BlockRef
    text: str
    character_count: int
    lines: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_text(self.text, self.character_count)


@dataclass(frozen=True)
class CanonicalPassage:
    """Canonical text-bearing passage."""

    ref: PassageRef
    text: str
    character_count: int

    def __post_init__(self) -> None:
        _validate_text(self.text, self.character_count)


def build_source_id(raw_id: str) -> str:
    """Normalize a raw source identifier."""
    normalized = raw_id.replace("_", "-").lower()
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized)
    source_id = normalized.strip("-")
    _require_id(source_id, "source_id")
    return source_id


def build_chapter_id(source_id: str, chapter_index: int) -> str:
    """Build a stable chapter identifier."""
    _require_id(source_id, "source_id")
    _require_positive_index(chapter_index, "chapter_index")
    return f"{source_id}:chapter:{chapter_index:04d}"


def build_block_id(source_id: str, chapter_index: int, block_index: int) -> str:
    """Build a stable block identifier."""
    chapter_id = build_chapter_id(source_id, chapter_index)
    _require_positive_index(block_index, "block_index")
    return f"{chapter_id}:block:{block_index:04d}"


def build_passage_id(source_id: str, chapter_index: int, passage_index: int) -> str:
    """Build a stable passage identifier."""
    chapter_id = build_chapter_id(source_id, chapter_index)
    _require_positive_index(passage_index, "passage_index")
    return f"{chapter_id}:passage:{passage_index:04d}"


def _require_id(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _require_positive_index(value: int, field_name: str) -> None:
    if value < 1:
        raise ValueError(f"{field_name} must be greater than or equal to 1")


def _validate_text(text: str, character_count: int) -> None:
    if not text:
        raise ValueError("text must not be empty")
    if character_count != len(text):
        raise ValueError("character_count must equal len(text)")
