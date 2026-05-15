"""Model-agnostic extraction runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from saga_companion.extract.parser import (
    parse_passage_extraction_response,
    validate_evidence_quotes_are_substrings,
)
from saga_companion.extract.prompts import (
    ExtractionPrompt,
    build_passage_extraction_prompt,
)
from saga_companion.extract.schemas import PassageExtraction
from saga_companion.schemas import CanonicalPassage


class ExtractionModelClient(Protocol):
    """Protocol for future model clients that can generate raw response text."""

    def generate(self, system: str, user: str) -> str:
        """Return a raw extraction response for the supplied prompts."""


@dataclass(frozen=True)
class ExtractionResult:
    """Prompt, raw response, and parsed extraction for one passage."""

    passage: CanonicalPassage
    prompt: ExtractionPrompt
    raw_response: str
    extraction: PassageExtraction


def extract_passage(
    passage: CanonicalPassage,
    client: ExtractionModelClient,
) -> ExtractionResult:
    """Extract structured data from one canonical passage with a model client."""
    prompt = build_passage_extraction_prompt(passage)
    raw_response = client.generate(system=prompt.system, user=prompt.user)
    extraction = parse_passage_extraction_response(raw_response)
    validate_evidence_quotes_are_substrings(extraction, passage_text=passage.text)
    return ExtractionResult(
        passage=passage,
        prompt=prompt,
        raw_response=raw_response,
        extraction=extraction,
    )


def extract_passages(
    passages: list[CanonicalPassage],
    client: ExtractionModelClient,
) -> list[ExtractionResult]:
    """Extract structured data from passages in order."""
    return [extract_passage(passage, client) for passage in passages]
