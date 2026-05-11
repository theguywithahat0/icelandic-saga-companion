# Icelandic Saga Companion

A graph-backed AI companion for Icelandic sagas, focused on characters, relationships, places, events, and cited answers from saga texts.

## Project Direction

This repository is being refactored from a notebook-only prototype into a small Python project. The existing capstone notebook has been preserved under `notebooks/legacy_capstone.ipynb` for reference while the package structure grows around it.

Planned package areas:

- `ingest`: load and normalize saga text sources.
- `extract`: identify characters, places, events, and relationships.
- `graph`: model saga entities and connections.
- `retrieval`: find relevant passages for grounded answers.
- `companion`: coordinate user-facing companion behavior.

The current scaffold intentionally avoids heavy dependencies, generated data, and database setup. Implementation will be added incrementally.
