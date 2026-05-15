"""Strict parsing for future extraction model responses."""

from __future__ import annotations

import json
import re
from typing import Any

from saga_companion.extract.adapters import passage_extraction_from_dict
from saga_companion.extract.schemas import EvidenceRef, PassageExtraction


class ExtractionParseError(ValueError):
    """Raised when a raw extraction response cannot be parsed or validated."""


def parse_passage_extraction_response(
    raw_response: str,
    *,
    allow_markdown_json: bool = False,
) -> PassageExtraction:
    """Parse and validate a raw JSON extraction response."""
    json_text = extract_json_object(raw_response)
    if allow_markdown_json:
        json_text = strip_single_json_markdown_fence(json_text)
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


def validate_evidence_quotes_are_substrings(
    extraction: PassageExtraction,
    *,
    passage_text: str,
) -> None:
    """Ensure each evidence quote is an exact substring of the canonical passage text."""
    for evidence in _all_evidence_refs(extraction):
        if evidence.quote not in passage_text:
            raise ExtractionParseError(
                "invalid evidence quote for passage "
                f"{extraction.passage_id}: {evidence.quote!r} is not an exact substring"
            )


def _all_evidence_refs(extraction: PassageExtraction) -> list[EvidenceRef]:
    return [
        *[person.evidence for person in extraction.people],
        *[place.evidence for place in extraction.places],
        *[event.evidence for event in extraction.events],
        *[relationship.evidence for relationship in extraction.relationships],
    ]


def extract_json_object(raw_response: str) -> str:
    """Return stripped response text.

    This is intentionally strict for now. Future model-repair behavior, such as
    Markdown fence stripping or JSON object extraction from surrounding text, can
    be added at this boundary without changing the typed schema adapters.
    """
    return raw_response.strip()


def strip_single_json_markdown_fence(raw_response: str) -> str:
    """Strip one whole-response Markdown JSON fence if present."""
    stripped = raw_response.strip()
    match = re.fullmatch(
        r"```(?:json)?[ \t]*\r?\n(?P<content>.*?)\r?\n```",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if match is None:
        return stripped
    return match.group("content").strip()
