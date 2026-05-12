"""Load local saga text files with lightweight metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_LANGUAGE_SUFFIX_RE = re.compile(r"^(?P<name>.+)\.(?P<language>[A-Za-z]{2,5})$")


@dataclass(frozen=True)
class SagaText:
    """A saga text file and derived metadata."""

    id: str
    title: str
    language: str | None
    filename: str
    path: Path
    text: str
    character_count: int
    line_count: int


def load_saga_file(path: str | Path, encoding: str = "utf-8") -> SagaText:
    """Read one saga text file without modifying its body text."""
    saga_path = Path(path)
    if not saga_path.exists():
        raise FileNotFoundError(saga_path)
    if saga_path.is_dir():
        raise IsADirectoryError(saga_path)

    text = saga_path.read_text(encoding=encoding)
    saga_id, title, language = _metadata_from_filename(saga_path.name)
    return SagaText(
        id=saga_id,
        title=title,
        language=language,
        filename=saga_path.name,
        path=saga_path,
        text=text,
        character_count=len(text),
        line_count=len(text.splitlines()),
    )


def load_saga_directory(
    directory: str | Path,
    pattern: str = "*.txt",
    encoding: str = "utf-8",
) -> list[SagaText]:
    """Load matching saga text files from a directory in filename order."""
    saga_directory = Path(directory)
    if not saga_directory.exists():
        raise FileNotFoundError(saga_directory)
    if not saga_directory.is_dir():
        raise NotADirectoryError(saga_directory)

    files = sorted(
        (path for path in saga_directory.glob(pattern) if path.is_file()),
        key=lambda path: path.name,
    )
    return [load_saga_file(path, encoding=encoding) for path in files]


def _metadata_from_filename(filename: str) -> tuple[str, str, str | None]:
    stem = _strip_txt_suffix(filename)
    language_match = _LANGUAGE_SUFFIX_RE.match(stem)
    if language_match:
        name = language_match.group("name")
        language = language_match.group("language")
    else:
        name = stem
        language = None

    return _build_id(name), _build_title(name), language


def _strip_txt_suffix(filename: str) -> str:
    suffix = ".txt"
    if filename.lower().endswith(suffix):
        return filename[: -len(suffix)]
    return filename


def _build_id(name: str) -> str:
    return re.sub(r"[-\s]+", "-", name.replace("_", "-").lower()).strip("-")


def _build_title(name: str) -> str:
    return name.replace("_", " ").replace("-", " ").title()
