"""Load SagaDB-style XML saga source files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import xml.etree.ElementTree as ET


_LANGUAGE_SUFFIX_RE = re.compile(r"^(?P<name>.+)\.[A-Za-z]{2,5}$")


@dataclass(frozen=True)
class SagaXmlMetadata:
    """Metadata parsed from a SagaDB XML document."""

    title: str | None
    title_orig: str | None
    language: str | None
    language_iso: str | None
    basename: str | None
    translator: str | None
    editor: str | None
    translation_date: str | None
    source_name: str | None
    source_url: str | None
    raw: dict[str, str]


@dataclass(frozen=True)
class SagaXmlBlock:
    """An ordered text block parsed from a SagaDB XML chapter."""

    kind: str
    text: str
    lines: list[str]


@dataclass(frozen=True)
class SagaXmlChapter:
    """A chapter parsed from SagaDB XML content."""

    number: str
    title: str | None
    blocks: list[SagaXmlBlock]
    paragraphs: list[str]
    text: str
    character_count: int


@dataclass(frozen=True)
class SagaXmlText:
    """A SagaDB XML file with metadata and chapter text."""

    id: str
    metadata: SagaXmlMetadata
    filename: str
    path: Path
    chapters: list[SagaXmlChapter]
    text: str
    character_count: int


def load_saga_xml_file(path: str | Path, encoding: str = "utf-8") -> SagaXmlText:
    """Load one SagaDB-style XML file."""
    xml_path = Path(path)
    if not xml_path.exists():
        raise FileNotFoundError(xml_path)
    if xml_path.is_dir():
        raise IsADirectoryError(xml_path)

    parser = ET.XMLParser(encoding=encoding)
    root = ET.parse(xml_path, parser=parser).getroot()
    metadata = _parse_metadata(root.find("metadata"))
    chapters = _parse_chapters(root.find("content"))
    text = "\n\n".join(chapter.text for chapter in chapters if chapter.text)
    id_source = metadata.basename or _strip_xml_suffix(xml_path.name)

    return SagaXmlText(
        id=_build_id(id_source),
        metadata=metadata,
        filename=xml_path.name,
        path=xml_path,
        chapters=chapters,
        text=text,
        character_count=len(text),
    )


def load_saga_xml_directory(
    directory: str | Path,
    pattern: str = "*.xml",
    encoding: str = "utf-8",
) -> list[SagaXmlText]:
    """Load matching SagaDB-style XML files from a directory."""
    xml_directory = Path(directory)
    if not xml_directory.exists():
        raise FileNotFoundError(xml_directory)
    if not xml_directory.is_dir():
        raise NotADirectoryError(xml_directory)

    files = sorted(
        (path for path in xml_directory.glob(pattern) if path.is_file()),
        key=lambda path: path.name,
    )
    return [load_saga_xml_file(path, encoding=encoding) for path in files]


def _parse_metadata(metadata_element: ET.Element | None) -> SagaXmlMetadata:
    raw = _metadata_raw(metadata_element)
    return SagaXmlMetadata(
        title=raw.get("title"),
        title_orig=raw.get("title_orig"),
        language=raw.get("language"),
        language_iso=raw.get("language_iso"),
        basename=raw.get("basename"),
        translator=raw.get("trans"),
        editor=raw.get("editor"),
        translation_date=raw.get("trans_date"),
        source_name=raw.get("sourcename"),
        source_url=raw.get("sourceurl"),
        raw=raw,
    )


def _metadata_raw(metadata_element: ET.Element | None) -> dict[str, str]:
    if metadata_element is None:
        return {}

    raw: dict[str, str] = {}
    for child in list(metadata_element):
        value = _clean_text(child.text)
        if value is not None:
            raw[child.tag] = value
    return raw


def _parse_chapters(content_element: ET.Element | None) -> list[SagaXmlChapter]:
    if content_element is None:
        return []

    return [
        _parse_chapter(chapter_element)
        for chapter_element in content_element.findall("chapter")
    ]


def _parse_chapter(chapter_element: ET.Element) -> SagaXmlChapter:
    blocks = _parse_chapter_blocks(chapter_element)
    paragraphs = [block.text for block in blocks if block.kind == "paragraph"]
    text = "\n\n".join(block.text for block in blocks)
    return SagaXmlChapter(
        number=chapter_element.get("number", ""),
        title=chapter_element.get("title"),
        blocks=blocks,
        paragraphs=paragraphs,
        text=text,
        character_count=len(text),
    )


def _parse_chapter_blocks(chapter_element: ET.Element) -> list[SagaXmlBlock]:
    blocks: list[SagaXmlBlock] = []
    for child in list(chapter_element):
        if child.tag == "paragraph":
            block = _parse_paragraph_block(child)
        elif child.tag == "poetry":
            block = _parse_poetry_block(child)
        else:
            block = None

        if block is not None:
            blocks.append(block)

    return blocks


def _parse_paragraph_block(paragraph_element: ET.Element) -> SagaXmlBlock | None:
    text = _clean_text(paragraph_element.text)
    if text is None:
        return None
    return SagaXmlBlock(kind="paragraph", text=text, lines=[])


def _parse_poetry_block(poetry_element: ET.Element) -> SagaXmlBlock | None:
    lines = [
        line
        for line in (
            _clean_text(line_element.text)
            for line_element in poetry_element.findall("line")
        )
        if line is not None
    ]
    if not lines:
        return None
    return SagaXmlBlock(kind="poetry", text="\n".join(lines), lines=lines)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None
    return stripped


def _strip_xml_suffix(filename: str) -> str:
    suffix = ".xml"
    if filename.lower().endswith(suffix):
        return filename[: -len(suffix)]
    return filename


def _build_id(name: str) -> str:
    language_match = _LANGUAGE_SUFFIX_RE.match(name)
    if language_match:
        name = language_match.group("name")
    return re.sub(r"[-\s]+", "-", name.replace("_", "-").lower()).strip("-")
