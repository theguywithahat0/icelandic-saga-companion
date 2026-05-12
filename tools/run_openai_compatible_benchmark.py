"""Manual benchmark runner for OpenAI-compatible extraction providers."""

from __future__ import annotations

import argparse
from dataclasses import fields
import json
import os
import sys

from saga_companion.benchmark import (
    BenchmarkCase,
    ExtractionScore,
    canonical_passage_from_benchmark_case,
    load_benchmark_cases,
    score_extraction,
)
from saga_companion.extract import (
    ExtractionParseError,
    OpenAICompatibleExtractionClient,
    ProviderResponseError,
    extract_passage,
    passage_extraction_to_dict,
)


def main(argv: list[str] | None = None) -> int:
    """Run a manual extraction benchmark and print a JSON report."""
    args = _parse_args(argv)
    try:
        report = run_benchmark(
            benchmark_file=args.benchmark_file,
            base_url=args.base_url,
            model=args.model,
            api_key_env_var=args.api_key_env_var,
            limit=args.limit,
            case_ids=args.case_id,
        )
    except (
        OSError,
        ValueError,
        ExtractionParseError,
        ProviderResponseError,
    ) as exc:
        print(f"benchmark failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def run_benchmark(
    *,
    benchmark_file: str,
    base_url: str,
    model: str,
    api_key_env_var: str | None = None,
    limit: int | None = None,
    case_ids: list[str] | None = None,
) -> dict[str, object]:
    """Run benchmark cases and return a JSON-serializable report."""
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than 0")

    cases = _filtered_cases(
        load_benchmark_cases(benchmark_file),
        case_ids=case_ids,
        limit=limit,
    )
    if not cases:
        raise ValueError("no benchmark cases remain after filtering")

    api_key = os.environ.get(api_key_env_var) if api_key_env_var is not None else None
    client = OpenAICompatibleExtractionClient(
        model=model,
        base_url=base_url,
        api_key=api_key,
    )

    case_reports: list[dict[str, object]] = []
    scores: list[ExtractionScore] = []
    for case in cases:
        result = extract_passage(
            canonical_passage_from_benchmark_case(case),
            client,
        )
        score = score_extraction(case.expected, result.extraction)
        scores.append(score)
        case_reports.append(
            {
                "id": case.id,
                "description": case.description,
                "passage_id": case.passage.passage_id,
                "score": score_to_dict(score),
                "extraction": passage_extraction_to_dict(result.extraction),
            },
        )

    return {
        "provider": "openai_compatible",
        "base_url": base_url,
        "model": model,
        "case_count": len(case_reports),
        "cases": case_reports,
        "macro_average": average_scores(scores),
    }


def score_to_dict(score: ExtractionScore) -> dict[str, float]:
    """Convert an extraction score to a plain dictionary."""
    return {field.name: getattr(score, field.name) for field in fields(score)}


def average_scores(scores: list[ExtractionScore]) -> dict[str, float]:
    """Compute macro-average scores across benchmark cases."""
    if not scores:
        raise ValueError("scores must not be empty")
    return {
        field.name: sum(getattr(score, field.name) for score in scores) / len(scores)
        for field in fields(scores[0])
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manually run extraction benchmark fixtures against an OpenAI-compatible endpoint.",
    )
    parser.add_argument("--benchmark-file", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key-env-var")
    parser.add_argument("--limit", type=_positive_int)
    parser.add_argument("--case-id", action="append")
    return parser.parse_args(argv)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("limit must be greater than 0")
    return parsed


def _filtered_cases(
    cases: list[BenchmarkCase],
    *,
    case_ids: list[str] | None,
    limit: int | None,
) -> list[BenchmarkCase]:
    selected = cases
    if case_ids:
        allowed_ids = set(case_ids)
        selected = [case for case in selected if case.id in allowed_ids]
    if limit is not None:
        selected = selected[:limit]
    return selected


if __name__ == "__main__":
    raise SystemExit(main())
