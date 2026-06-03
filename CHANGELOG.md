# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-03

First public reference build.

### Added
- Frozen domain models and the `Protocol` interface layer that every stage depends on.
- LLM classification with quarantine-over-guess and a constrained two-stage angle picker.
- Deterministic safety gate (merge-leak, spam, AI-slop, wrong-brand, suppression) as an open/closed `DraftCheck` chain.
- Wave scheduler with warmup caps and steady-state fallthrough; synthetic enrichment; a dry-run sender and a real Resend adapter.
- Deterministic pipeline orchestrator with no model in the control loop.
- Inbound responder on the Claude Agent SDK, behind an `AgentRunner` seam, with an opt-out short-circuit, a price guard, and a name-drop allowlist.
- Five eval suites with labeled golden data; stub results run in CI, live results are checked in.
- Disk-cached and budgeted LLM clients; ops layer (heartbeat, bounce canary, daily report).
- CI runs lint, format, strict types, and the full test suite with no API key.

### Notes
- This public reference build redacts the proprietary email copy, prompt text, and voice guide to placeholders. The architecture, safety framework, eval harness, and tests run end to end on the placeholders.
