"""Text ingestion interfaces for saga sources."""

from saga_companion.ingest.load_sagas import (
    SagaText,
    load_saga_directory,
    load_saga_file,
)
from saga_companion.ingest.split_chapters import Chapter, split_into_chapters

__all__ = [
    "Chapter",
    "SagaText",
    "load_saga_directory",
    "load_saga_file",
    "split_into_chapters",
]
