"""Text ingestion interfaces for saga sources."""

from saga_companion.ingest.chunk_passages import Passage, chunk_chapter, chunk_chapters
from saga_companion.ingest.load_sagas import (
    SagaText,
    load_saga_directory,
    load_saga_file,
)
from saga_companion.ingest.load_xml import (
    SagaXmlBlock,
    SagaXmlChapter,
    SagaXmlMetadata,
    SagaXmlText,
    load_saga_xml_directory,
    load_saga_xml_file,
)
from saga_companion.ingest.pipeline import (
    IngestedSaga,
    ingest_saga_directory,
    ingest_saga_file,
)
from saga_companion.ingest.split_chapters import Chapter, split_into_chapters

__all__ = [
    "Chapter",
    "IngestedSaga",
    "Passage",
    "SagaText",
    "SagaXmlBlock",
    "SagaXmlChapter",
    "SagaXmlMetadata",
    "SagaXmlText",
    "chunk_chapter",
    "chunk_chapters",
    "ingest_saga_directory",
    "ingest_saga_file",
    "load_saga_directory",
    "load_saga_file",
    "load_saga_xml_directory",
    "load_saga_xml_file",
    "split_into_chapters",
]
