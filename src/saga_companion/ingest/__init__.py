"""Text ingestion interfaces for saga sources."""

from saga_companion.ingest.split_chapters import Chapter, split_into_chapters

__all__ = ["Chapter", "split_into_chapters"]
