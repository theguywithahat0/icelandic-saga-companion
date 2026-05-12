# Icelandic Saga Companion

A graph-backed AI companion for Icelandic sagas, focused on characters, relationships, places, events, and cited answers from saga texts.

The project is moving from a notebook prototype into a tested Python package. The current implementation focuses on ingestion, canonical provenance schemas, and typed contracts for future extraction work.

The legacy capstone notebook is preserved at `notebooks/legacy_capstone.ipynb`.

## Current Status

Phase 1 ingestion is implemented. Phase 2 canonical schemas and provenance contracts are implemented.

Actual model-based AI extraction, graph modeling, retrieval, and companion behavior are planned but not implemented yet.

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
- Development workflow with uv, pytest, and Ruff.

## Data Sources

The original notebook worked with SagaDB plain-text exports. SagaDB canonical source files are XML, and XML is the preferred long-term input format because it preserves metadata, chapter titles, paragraph boundaries, and poetry blocks.

Plain-text ingestion remains available for compatibility and simpler local experiments.

## Package Layout

- `ingest`: implemented. Loads plain text and SagaDB XML, splits chapters, and chunks passages.
- Root schema/canonicalization modules: implemented. Define shared source/provenance records and convert ingestion outputs into canonical records.
- `extract`: partially implemented. Schemas and JSON/dict adapters exist, but no model extraction is implemented yet.
- `graph`: placeholder. Intended for future entity and relationship modeling.
- `retrieval`: placeholder. Intended for future cited passage lookup and answer grounding.
- `companion`: placeholder. Intended for future user-facing companion orchestration.

Only ingestion, canonical schemas, canonicalization, and extraction contracts/adapters have real implementation at this stage.

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

## Roadmap

- Model-backed extraction from canonical passages.
- Extraction prompt and versioning layer.
- Entity resolution.
- Graph modeling.
- Retrieval and cited answers.
- UI or API.

## Non-Goals For The Current Phase

The current project does not yet include:

- Actual LLM extraction calls.
- A graph database.
- Vector search.
- A web app.
- Generated dataset outputs.
