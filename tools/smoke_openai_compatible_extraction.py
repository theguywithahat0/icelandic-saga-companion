"""Manual smoke test for OpenAI-compatible extraction providers."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from saga_companion.extract import (
    ExtractionParseError,
    OpenAICompatibleExtractionClient,
    ProviderResponseError,
    extract_passage,
    passage_extraction_to_dict,
)
from saga_companion.schemas import CanonicalPassage, PassageRef


def main(argv: list[str] | None = None) -> int:
    """Run a manual OpenAI-compatible extraction smoke test."""
    args = _parse_args(argv)
    try:
        passage_text = _passage_text(args)
        passage = _canonical_passage(
            source_id=args.source_id,
            chapter_id=args.chapter_id,
            passage_id=args.passage_id,
            text=passage_text,
        )
        api_key = (
            os.environ.get(args.api_key_env_var)
            if args.api_key_env_var is not None
            else None
        )
        client = OpenAICompatibleExtractionClient(
            model=args.model,
            base_url=args.base_url,
            api_key=api_key,
        )
        result = extract_passage(passage, client)
        print(
            json.dumps(
                passage_extraction_to_dict(result.extraction),
                indent=2,
                sort_keys=True,
            ),
        )
    except (OSError, ValueError, ExtractionParseError, ProviderResponseError) as exc:
        print(f"smoke extraction failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manually smoke test an OpenAI-compatible extraction endpoint.",
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key-env-var")
    parser.add_argument("--source-id", default="manual-source")
    parser.add_argument("--chapter-id", default="manual-source:chapter:0001")
    parser.add_argument(
        "--passage-id",
        default="manual-source:chapter:0001:passage:0001",
    )

    passage_group = parser.add_mutually_exclusive_group(required=True)
    passage_group.add_argument("--passage-text")
    passage_group.add_argument("--passage-file")
    return parser.parse_args(argv)


def _passage_text(args: argparse.Namespace) -> str:
    if args.passage_text is not None:
        return args.passage_text
    return Path(args.passage_file).read_text(encoding="utf-8")


def _canonical_passage(
    *,
    source_id: str,
    chapter_id: str,
    passage_id: str,
    text: str,
) -> CanonicalPassage:
    return CanonicalPassage(
        ref=PassageRef(
            source_id=source_id,
            chapter_id=chapter_id,
            passage_id=passage_id,
            passage_index=1,
        ),
        text=text,
        character_count=len(text),
    )


if __name__ == "__main__":
    raise SystemExit(main())
