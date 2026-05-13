"""Draft reviewable real-passage benchmark fixtures from SagaDB XML."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from saga_companion.benchmark import (
    benchmark_cases_to_json_dict,
    default_draft_selection_rules,
    draft_benchmark_cases_from_ingested_xml,
)
from saga_companion.ingest import IngestedXmlSaga, ingest_saga_xml_file


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
            rule_names=tuple(args.rule) if args.rule else None,
            limit=args.limit,
            per_rule_limit=args.per_rule_limit,
            include_first_unmatched=args.include_first_unmatched,
            max_text_characters=args.max_text_characters,
        )
        if not cases:
            print(
                "warning: no benchmark cases matched the default keyword rules",
                file=sys.stderr,
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
        if args.verbose:
            _print_verbose_summary(args, ingested, len(cases))
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
    parser.add_argument(
        "--rule",
        action="append",
        choices=[rule.name for rule in default_draft_selection_rules()],
        help="Repeat to include only specific rules.",
    )
    parser.add_argument("--per-rule-limit", type=_positive_int)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--include-first-unmatched", type=_positive_int)
    parser.add_argument("--max-text-characters", type=_positive_int, default=1200)
    parser.add_argument("--max-characters", type=_positive_int, default=6000)
    parser.add_argument("--overlap-characters", type=_non_negative_int, default=500)
    return parser.parse_args(argv)


def _print_verbose_summary(
    args: argparse.Namespace,
    ingested: IngestedXmlSaga,
    drafted_case_count: int,
) -> None:
    print(f"xml_file: {args.xml_file}", file=sys.stderr)
    print(f"source_id: {ingested.saga.id}", file=sys.stderr)
    print(f"chapters: {len(ingested.chapters)}", file=sys.stderr)
    print(f"passages: {len(ingested.passages)}", file=sys.stderr)
    print(f"drafted_cases: {drafted_case_count}", file=sys.stderr)
    if args.output_file is not None:
        print(f"output_file: {args.output_file}", file=sys.stderr)


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
