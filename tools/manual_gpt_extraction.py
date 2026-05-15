"""Manual GPT-backed extraction runner for canonical passages."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

from saga_companion.extract import (
    ExtractionParseError,
    ExtractionResult,
    OpenAICompatibleExtractionClient,
    ProviderResponseError,
    build_passage_extraction_prompt,
    passage_extraction_to_dict,
    parse_passage_extraction_response,
    validate_evidence_quotes_are_substrings,
)
from saga_companion.canonicalize import canonicalize_xml_ingestion
from saga_companion.ingest.xml_pipeline import ingest_saga_xml_file
from saga_companion.schemas import CanonicalPassage, PassageRef


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        passages = _load_passages(args)
        if args.limit is not None:
            passages = passages[: args.limit]
        if not passages:
            raise ValueError("no canonical passages remain after filtering")

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

        records = run_manual_extraction(
            passages=passages,
            client=debug_client,
            progress=args.progress,
            allow_markdown_json=args.allow_markdown_json,
            continue_on_error=args.continue_on_error,
        )

        if args.output_file is None:
            _write_records(records=records, output_format=args.output_format, stream=sys.stdout)
        else:
            output_path = Path(args.output_file)
            with output_path.open("w", encoding="utf-8") as stream:
                _write_records(records=records, output_format=args.output_format, stream=stream)
    except (OSError, ValueError, ExtractionParseError, ProviderResponseError) as exc:
        print(f"manual extraction failed: {exc}", file=sys.stderr)
        return 1

    return 0


def run_manual_extraction(
    *,
    passages: list[CanonicalPassage],
    client: _DebugCaptureClient,
    progress: bool,
    allow_markdown_json: bool,
    continue_on_error: bool,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    total = len(passages)
    for index, passage in enumerate(passages, start=1):
        started = time.monotonic()
        if progress:
            print(f"[{index}/{total}] started {passage.ref.passage_id}", file=sys.stderr)
        try:
            result = extract_passage(
                passage,
                client,
                allow_markdown_json=allow_markdown_json,
            )
            records.append(
                {
                    "passage": _passage_to_dict(passage),
                    "status": "ok",
                    "extraction": passage_extraction_to_dict(result.extraction),
                }
            )
            if progress:
                elapsed = time.monotonic() - started
                print(
                    f"[{index}/{total}] finished {passage.ref.passage_id} status=ok ({elapsed:.2f}s)",
                    file=sys.stderr,
                )
        except (ExtractionParseError, ProviderResponseError, ValueError, OSError) as exc:
            if not continue_on_error:
                raise
            records.append(
                {
                    "passage": _passage_to_dict(passage),
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            if progress:
                elapsed = time.monotonic() - started
                print(
                    f"[{index}/{total}] finished {passage.ref.passage_id} status=failed ({elapsed:.2f}s)",
                    file=sys.stderr,
                )
    return records


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
    validate_evidence_quotes_are_substrings(extraction, passage_text=passage.text)
    return ExtractionResult(
        passage=passage,
        prompt=prompt,
        raw_response=raw_response,
        extraction=extraction,
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manual GPT-backed extraction over canonical passages.",
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--xml-file")
    input_group.add_argument("--passages-file")
    parser.add_argument("--max-characters", type=_positive_int, default=6000)
    parser.add_argument("--overlap-characters", type=_non_negative_int, default=500)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key-env-var", default="OPENAI_API_KEY")
    parser.add_argument("--timeout-seconds", type=_positive_float, default=300.0)
    parser.add_argument("--limit", type=_positive_int)
    parser.add_argument("--allow-markdown-json", action="store_true")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--output-file")
    parser.add_argument(
        "--output-format",
        choices=["json", "jsonl"],
        default="jsonl",
    )
    return parser.parse_args(argv)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("limit must be greater than 0")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("timeout-seconds must be greater than 0")
    return parsed


def _load_passages(args: argparse.Namespace) -> list[CanonicalPassage]:
    if args.xml_file is not None:
        ingested = ingest_saga_xml_file(
            args.xml_file,
            max_characters=args.max_characters,
            overlap_characters=args.overlap_characters,
        )
        return canonicalize_xml_ingestion(ingested).passages

    assert args.passages_file is not None
    text = Path(args.passages_file).read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        return []

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in stripped.splitlines() if line.strip()]

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("passages file must decode to a list or JSONL objects")

    return [_canonical_passage_from_obj(item) for item in data]


def _canonical_passage_from_obj(obj: object) -> CanonicalPassage:
    if not isinstance(obj, dict):
        raise ValueError("each passage record must be an object")
    text = _required_text(obj.get("text"), "text")
    source_id = _required_text(obj.get("source_id"), "source_id")
    chapter_id = _required_text(obj.get("chapter_id"), "chapter_id")
    passage_id = _required_text(obj.get("passage_id"), "passage_id")
    passage_index = int(obj.get("passage_index", 1))
    character_count = int(obj.get("character_count", len(text)))
    return CanonicalPassage(
        ref=PassageRef(
            source_id=source_id,
            chapter_id=chapter_id,
            passage_id=passage_id,
            passage_index=passage_index,
        ),
        text=text,
        character_count=character_count,
    )


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _passage_to_dict(passage: CanonicalPassage) -> dict[str, object]:
    return {
        "source_id": passage.ref.source_id,
        "chapter_id": passage.ref.chapter_id,
        "passage_id": passage.ref.passage_id,
        "passage_index": passage.ref.passage_index,
        "text": passage.text,
        "character_count": passage.character_count,
    }


def _write_records(*, records: list[dict[str, object]], output_format: str, stream: object) -> None:
    if output_format == "json":
        print(json.dumps(records, indent=2, sort_keys=True), file=stream)
        return
    for record in records:
        print(json.dumps(record, sort_keys=True), file=stream)


class _DebugCaptureClient:
    def __init__(self, client: OpenAICompatibleExtractionClient) -> None:
        self._client = client

    def generate(self, system: str, user: str) -> str:
        return self._client.generate(system=system, user=user)


if __name__ == "__main__":
    raise SystemExit(main())
