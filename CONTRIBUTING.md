# Contributing

This is a reference implementation, but the workflow is real and enforced in CI.

## Setup

    uv venv && uv pip install -e ".[dev,agent]"

## Before you push

All four must pass; CI runs the same checks.

    ruff check .
    ruff format --check .
    pyright
    pytest

## Conventions

- Every source file opens with two `# ABOUTME:` comment lines.
- `src/` is strictly typed; keep pyright strict green.
- Deterministic stages get unit tests; model-driven stages get an eval suite with labeled golden data on top of a unit test.
- Safety properties never depend on the model being right. A new safety rule is a new `DraftCheck` class, not an edit to the gate.
- No em dashes. Plain, concrete prose.
