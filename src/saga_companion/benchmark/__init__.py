"""Benchmark fixtures and scoring for extraction evaluation."""

from saga_companion.benchmark.fixtures import (
    BenchmarkCase,
    BenchmarkPassage,
    ExpectedExtraction,
    canonical_passage_from_benchmark_case,
    load_benchmark_cases,
)
from saga_companion.benchmark.scoring import ExtractionScore, score_extraction

__all__ = [
    "BenchmarkCase",
    "BenchmarkPassage",
    "ExpectedExtraction",
    "ExtractionScore",
    "canonical_passage_from_benchmark_case",
    "load_benchmark_cases",
    "score_extraction",
]
