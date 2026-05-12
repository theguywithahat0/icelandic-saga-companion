"""Utilities for splitting saga source text into chapters."""

from __future__ import annotations

from dataclasses import dataclass
import re


_CHAPTER_HEADING_RE = re.compile(
    r"^[ \t]*(?P<title>chap(?:ter)?\.?\s+(?:[ivxlcdm]+|\d+))[ \t]*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class Chapter:
    """A chapter or fallback text chunk."""

    title: str
    text: str
    index: int


def split_into_chapters(text: str) -> list[Chapter]:
    """Split source text into chapters, falling back to blank-line chunks."""
    normalized_text = _normalize_line_endings(text)
    if not normalized_text.strip():
        return []

    headings = list(_CHAPTER_HEADING_RE.finditer(normalized_text))
    if not headings:
        return _split_into_chunks(normalized_text)

    chapters: list[Chapter] = []
    for heading_index, heading in enumerate(headings):
        next_start = (
            headings[heading_index + 1].start()
            if heading_index + 1 < len(headings)
            else len(normalized_text)
        )
        body = normalized_text[heading.end() : next_start].strip()
        if body:
            chapters.append(
                Chapter(
                    title=heading.group("title").strip(),
                    text=body,
                    index=len(chapters) + 1,
                )
            )

    return chapters


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _split_into_chunks(text: str) -> list[Chapter]:
    chunks = re.split(r"\n\s*\n+", text)
    return [
        Chapter(title=f"Chunk {index}", text=chunk.strip(), index=index)
        for index, chunk in enumerate(
            (chunk for chunk in chunks if chunk.strip()),
            start=1,
        )
    ]
