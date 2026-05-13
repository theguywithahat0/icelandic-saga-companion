"""Benchmark fixtures and scoring for extraction evaluation."""

from saga_companion.benchmark.fixtures import (
    BenchmarkCase,
    BenchmarkPassage,
    ExpectedExtraction,
    canonical_passage_from_benchmark_case,
    load_benchmark_cases,
)
from saga_companion.benchmark.draft import (
    DraftSelectionRule,
    benchmark_cases_to_json_dict,
    default_draft_selection_rules,
    draft_benchmark_cases_from_ingested_xml,
)
from saga_companion.benchmark.scoring import ExtractionScore, score_extraction

__all__ = [
    "BenchmarkCase",
    "BenchmarkPassage",
    "DraftSelectionRule",
    "ExpectedExtraction",
    "ExtractionScore",
    "benchmark_cases_to_json_dict",
    "canonical_passage_from_benchmark_case",
    "default_draft_selection_rules",
    "draft_benchmark_cases_from_ingested_xml",
    "load_benchmark_cases",
    "score_extraction",
]
