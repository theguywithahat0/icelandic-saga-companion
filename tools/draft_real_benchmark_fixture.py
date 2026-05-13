"""Draft reviewable real-passage benchmark fixtures from SagaDB XML."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from saga_companion.benchmark import (
    benchmark_cases_to_json_dict,
    draft_benchmark_cases_from_ingested_xml,
)
from saga_companion.ingest import ingest_saga_xml_file


def main(argv: list[str] | None = None) -> int:
    """Draft benchmark fixture JSON from one XML file."""
    args = _parse_args(argv)
    try:
        ingested = ingest_saga_xml_file(
            args.xml_file,
            max_characters=args.max_characters,
            overlap_characters=args.overlap_characters,
        )
        cases = draft_benchmark_cases_from_ingested_xml(
            ingested,
            limit=args.limit,
            max_text_characters=args.max_text_characters,
        )
        output = json.dumps(
            benchmark_cases_to_json_dict(cases),
            indent=2,
            sort_keys=True,
        )
        if args.output_file is None:
            print(output)
        else:
            Path(args.output_file).write_text(f"{output}\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"draft fixture failed: {exc}", file=sys.stderr)
        return 1

    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Draft reviewable benchmark fixture cases from SagaDB XML.",
    )
    parser.add_argument("--xml-file", required=True)
    parser.add_argument("--output-file")
    parser.add_argument("--limit", type=_positive_int)
    parser.add_argument("--max-text-characters", type=_positive_int, default=1200)
    parser.add_argument("--max-characters", type=_positive_int, default=6000)
    parser.add_argument("--overlap-characters", type=_non_negative_int, default=500)
    return parser.parse_args(argv)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be greater than or equal to 0")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
