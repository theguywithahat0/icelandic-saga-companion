"""Manual smoke test for OpenAI-compatible extraction providers."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from saga_companion.extract import (
    ExtractionParseError,
    ExtractionResult,
    OpenAICompatibleExtractionClient,
    ProviderResponseError,
    build_passage_extraction_prompt,
    passage_extraction_to_dict,
    parse_passage_extraction_response,
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
        provider_client = OpenAICompatibleExtractionClient(
            model=args.model,
            base_url=args.base_url,
            api_key=api_key,
            timeout_seconds=args.timeout_seconds,
        )
        debug_client = _DebugCaptureClient(provider_client)
        result = extract_passage(
            passage,
            debug_client,
            allow_markdown_json=args.allow_markdown_json,
        )
        print(
            json.dumps(
                passage_extraction_to_dict(result.extraction),
                indent=2,
                sort_keys=True,
            ),
        )
    except (OSError, ValueError, ExtractionParseError, ProviderResponseError) as exc:
        print(f"smoke extraction failed: {exc}", file=sys.stderr)
        if args.debug_provider_response:
            _print_debug_provider_response(
                model=args.model,
                base_url=args.base_url,
                timeout_seconds=args.timeout_seconds,
                provider_client=locals().get("provider_client"),
                raw_response=locals().get("debug_client").raw_response
                if "debug_client" in locals()
                else None,
            )
        return 1
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manually smoke test an OpenAI-compatible extraction endpoint.",
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key-env-var")
    parser.add_argument("--timeout-seconds", type=_positive_float, default=300.0)
    parser.add_argument("--debug-provider-response", action="store_true")
    parser.add_argument("--allow-markdown-json", action="store_true")
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


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("timeout-seconds must be greater than 0")
    return parsed


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


class _DebugCaptureClient:
    def __init__(self, client: OpenAICompatibleExtractionClient) -> None:
        self._client = client
        self.raw_response: str | None = None

    def generate(self, system: str, user: str) -> str:
        self.raw_response = self._client.generate(system=system, user=user)
        return self.raw_response

    def __getattr__(self, name: str) -> object:
        return getattr(self._client, name)


def extract_passage(
    passage: CanonicalPassage,
    client: _DebugCaptureClient,
    *,
    allow_markdown_json: bool,
) -> ExtractionResult:
    prompt = build_passage_extraction_prompt(passage)
    raw_response = client.generate(system=prompt.system, user=prompt.user)
    extraction = parse_passage_extraction_response(
        raw_response,
        allow_markdown_json=allow_markdown_json,
    )
    return ExtractionResult(
        passage=passage,
        prompt=prompt,
        raw_response=raw_response,
        extraction=extraction,
    )


def _print_debug_provider_response(
    *,
    model: str,
    base_url: str,
    timeout_seconds: float,
    provider_client: object,
    raw_response: str | None,
) -> None:
    print("provider debug:", file=sys.stderr)
    print(f"  model: {model}", file=sys.stderr)
    print(f"  base_url: {base_url}", file=sys.stderr)
    print(f"  timeout_seconds: {timeout_seconds}", file=sys.stderr)
    if raw_response is not None:
        print("  raw_response_preview:", file=sys.stderr)
        print(_preview(raw_response), file=sys.stderr)
    debug_response = getattr(provider_client, "debug_response", None)
    if callable(debug_response):
        print("  provider_response:", file=sys.stderr)
        print(
            json.dumps(debug_response(), indent=2, sort_keys=True),
            file=sys.stderr,
        )


def _preview(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


if __name__ == "__main__":
    raise SystemExit(main())
