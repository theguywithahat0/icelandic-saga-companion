"""Strict parsing for future extraction model responses."""

from __future__ import annotations

import json
from typing import Any

from saga_companion.extract.adapters import passage_extraction_from_dict
from saga_companion.extract.schemas import PassageExtraction


class ExtractionParseError(ValueError):
    """Raised when a raw extraction response cannot be parsed or validated."""


def parse_passage_extraction_response(raw_response: str) -> PassageExtraction:
    """Parse and validate a raw JSON extraction response."""
    json_text = extract_json_object(raw_response)
    if not json_text:
        raise ExtractionParseError("extraction response is empty")

    try:
        data: Any = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ExtractionParseError(f"invalid JSON extraction response: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise ExtractionParseError("extraction response must be a JSON object")

    try:
        return passage_extraction_from_dict(data)
    except ValueError as exc:
        raise ExtractionParseError(f"invalid extraction schema: {exc}") from exc


def extract_json_object(raw_response: str) -> str:
    """Return stripped response text.

    This is intentionally strict for now. Future model-repair behavior, such as
    Markdown fence stripping or JSON object extraction from surrounding text, can
    be added at this boundary without changing the typed schema adapters.
    """
    return raw_response.strip()
