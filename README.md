# Icelandic Saga Companion

A graph-backed AI companion for Icelandic sagas, focused on characters, relationships, places, events, and cited answers from saga texts.

The project is moving from a notebook prototype into a tested Python package. The current implementation focuses on ingestion, canonical provenance schemas, and scaffolding for future extraction work.

The legacy capstone notebook is preserved at `notebooks/legacy_capstone.ipynb`.

## Current Status

Phase 1 ingestion is implemented. Phase 2 canonical schemas and provenance contracts are implemented. Phase 3 extraction scaffolding is implemented.

Real model-backed extraction workflows are still not implemented. An OpenAI-compatible HTTP provider client exists for manual testing when configured, but automated/batch extraction, graph modeling, retrieval, and companion behavior are planned and not implemented yet. No model benchmark results are included yet.

## What Works Now

- Plain-text file loading.
- SagaDB XML loading.
- Metadata extraction from XML.
- XML chapter, paragraph, and poetry parsing.
- Plain-text chapter splitting.
- Context-safe passage chunking using character budgets.
- Plain-text ingestion pipeline.
- XML ingestion pipeline.
- Canonical source, chapter, block, and passage schemas.
- Canonicalization from ingestion outputs.
- Extraction schema contracts for people, places, events, relationships, and evidence.
- Extraction JSON/dict adapters for future model output validation.
- Extraction prompt construction from canonical passages.
- Deterministic expected extraction JSON shape.
- Strict extraction response parsing and validation for raw JSON strings.
- Model-agnostic extraction runner using a client protocol.
- OpenAI-compatible HTTP provider client for manually configured endpoints.
- Benchmark fixture loading and extraction quality scoring helpers.
- Fake-client tested extraction flow.
- Development workflow with uv, pytest, and Ruff.

## Data Sources

The original notebook worked with SagaDB plain-text exports. SagaDB canonical source files are XML, and XML is the preferred long-term input format because it preserves metadata, chapter titles, paragraph boundaries, and poetry blocks.

Plain-text ingestion remains available for compatibility and simpler local experiments.

## Package Layout

- `ingest`: implemented. Loads plain text and SagaDB XML, splits chapters, and chunks passages.
- Root schema/canonicalization modules: implemented. Define shared source/provenance records and convert ingestion outputs into canonical records.
- `extract`: partially implemented. Schemas, JSON/dict adapters, prompt construction, response parsing, a model-agnostic runner, and an OpenAI-compatible HTTP provider client exist. No Gemini provider, provider SDK dependency, automated benchmark workflow, or benchmark results exist yet.
- `graph`: placeholder. Intended for future entity and relationship modeling.
- `retrieval`: placeholder. Intended for future cited passage lookup and answer grounding.
- `companion`: placeholder. Intended for future user-facing companion orchestration.

Only ingestion, canonical schemas, canonicalization, and extraction scaffolding have real implementation at this stage.

## Development

Install the project and development tools with uv:

```sh
uv sync
```

Run tests:

```sh
uv run pytest
```

Run lint checks:

```sh
uv run ruff check .
```

## Manual Provider Smoke Test

An optional manual smoke script can target OpenAI-compatible endpoints, including local servers such as Ollama, LM Studio, or vLLM-style APIs. It does not run in normal tests and has not been benchmarked.

For a local endpoint:

```sh
uv run python tools/smoke_openai_compatible_extraction.py --base-url http://localhost:11434/v1 --model <model> --timeout-seconds 300 --passage-text "Egil sailed to Iceland."
```

For an endpoint that needs a bearer token, pass the environment variable name:

```sh
uv run python tools/smoke_openai_compatible_extraction.py --base-url https://api.example.com/v1 --model <model> --api-key-env-var OPENAI_API_KEY --passage-text "Egil sailed to Iceland."
```

If a provider response fails parsing, add `--debug-provider-response` to print sanitized provider metadata and raw response previews to stderr. API key values are not printed.

Some local instruct models, such as Mistral variants, may wrap otherwise valid JSON in a single Markdown code fence. For manual runs only, add `--allow-markdown-json` to accept one whole-response `json` or plain code fence. The default parser remains strict.

## Benchmark Fixtures

Benchmark fixture and scoring scaffolding exists for evaluating extraction quality from already-parsed results. A tiny synthetic fixture is included for tests; these snippets are not claimed as real saga quotations.

A curated real-passage gold fixture is also included at `tests/fixtures/benchmark/egils_saga_real_extraction_benchmark.json`. It contains 13 reviewed passages from SagaDB's `src/egils_saga.en.xml`, with expected people, places, event types, and relationship types mapped to the extraction schema vocabulary. The source XML is public-domain SagaDB text from `sveinbjornt/sagadb.org` at commit blob `6c34b9e07ffb92cc9774571e47b5ce6b21398a93`.

Broader fixtures and automated benchmark workflows are still future work.

## Drafting Real Benchmark Fixtures

Use the draft fixture tool to create candidate benchmark cases from SagaDB XML with deterministic keyword rules. The expected labels are intentionally empty and must be reviewed by a human before the fixture is used as gold data. The tool does not call a model or provider.

Output can be redirected from stdout or written with `--output-file`:

```sh
uv run python tools/draft_real_benchmark_fixture.py --xml-file path/to/saga.en.xml --limit 10 > draft_real_benchmark.json
```

## Manual Benchmark Runner

An optional manual benchmark runner can target Ollama, local OpenAI-compatible endpoints, OpenAI-compatible cloud APIs, LM Studio, or vLLM-style servers. Normal tests do not call providers. Use `--limit` to control cost while trying models.

For a local endpoint:

```sh
uv run python tools/run_openai_compatible_benchmark.py --benchmark-file tests/fixtures/benchmark/egils_saga_real_extraction_benchmark.json --base-url http://localhost:11434/v1 --model <model> --timeout-seconds 300 --allow-markdown-json --limit 1
```

For an OpenAI-compatible cloud endpoint with a bearer token:

```sh
uv run python tools/run_openai_compatible_benchmark.py --benchmark-file tests/fixtures/benchmark/egils_saga_real_extraction_benchmark.json --base-url https://api.openai.com/v1 --model <model> --api-key-env-var OPENAI_API_KEY --limit 1
```

Add `--continue-on-error` for full fixture runs where one malformed provider response should not discard the rest of the report. This records failed cases with error details and computes macro averages over successful cases.

Save manual result files outside git, for example:

```sh
uv run python tools/run_openai_compatible_benchmark.py --benchmark-file tests/fixtures/benchmark/egils_saga_real_extraction_benchmark.json --base-url http://localhost:11434/v1 --model <model> --timeout-seconds 300 --allow-markdown-json --continue-on-error > benchmark-results/<model>-egils-real.json
```

No model benchmark results are included in git yet.

If a provider response fails parsing, add `--debug-provider-response` to print sanitized provider metadata, case id, and raw response previews to stderr. API key values are not printed.

For local instruct models that wrap valid JSON in a single Markdown code fence, add `--allow-markdown-json`. This is opt-in for manual tools only; normal parsing remains strict.

## Roadmap

- Additional provider adapters, such as Gemini, behind the model client protocol.
- Extraction prompt versioning and fixtures.
- Batch extraction workflow.
- Entity resolution.
- Graph modeling.
- Retrieval and cited answers.
- UI or API.

## Non-Goals For The Current Phase

The current project does not yet include:

- Automated, batch, or benchmarked LLM extraction workflows.
- Provider SDK dependencies.
- A graph database.
- Vector search.
- A web app.
- Generated dataset outputs.
