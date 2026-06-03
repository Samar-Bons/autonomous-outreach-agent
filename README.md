# autonomous-outreach-agent

A reference implementation of an autonomous, safety-gated B2B cold-outreach agent.

It sources prospects, uses LLMs to decide who to pitch (and who to leave alone),
generates grounded per-prospect copy, runs every draft through a deterministic
safety gate, and schedules multi-touch email sequences inside hard compliance and
deliverability guardrails. It is built to run unattended without ever sending the
wrong thing to a stranger.

> **Thesis:** an LLM that touches the real world is a safety-critical system.
> The LLM does the reasoning; deterministic code holds the guarantees. No safety
> property is ever allowed to depend on the model being right.

This is a clean-room reference build extracted from a real production system.
Company, data, and contacts here are synthetic. Nothing in this repo targets a
real business or a third-party service.

---

## Why this exists

Getting a model to write a good cold email is easy. The hard part is the machine
around the model: knowing who *not* to email, catching opt-outs every time,
never leaking a template variable or pitching the wrong product, respecting send
caps, and being safe to leave running unattended. That machine is most of the
engineering, and it is what this repo shows.

## The pipeline

```
source -> classify -> (quarantine?) -> enrich -> generate -> SAFETY GATE -> schedule -> send
                          |                                       |
                     never pitched                  deterministic checks + suppression
```

| Stage | What it does | Who decides |
|---|---|---|
| Source | Load prospects from a data source | code |
| Classify | Segment + archetype; quarantine over guess | **LLM** |
| Enrich | Find and verify a contact email | code |
| Generate | Render grounded copy for the chosen angle | **LLM** + templates |
| Safety gate | Merge-leak, spam, AI-slop, wrong-brand, suppression | code |
| Schedule | Wave offsets under warmup caps | code |
| Send | Deliver (dry-run by default) | code |

## Evals

The model-driven stages are covered by eval suites, not just unit tests:

1. **Classification + quarantine precision** against a labeled golden set.
2. **Opt-out detection** with adversarial cases and an enforced recall of 1.0 on
   true opt-outs.
3. **Draft safety-gate** proving each deterministic check fires correctly.
4. **Angle-pick quality** via an LLM-as-judge harness.

See [`evals/`](./evals).

## Quickstart

```bash
uv venv && uv pip install -e ".[dev]"
pytest                 # unit + integration + e2e, runs with the stub LLM, no API key
outreach version
```

To run the model-driven stages or evals for real, copy `.env.example` to `.env`
and set `ANTHROPIC_API_KEY`.

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the design, the SOLID seams, and how
the "LLM reasons, code guarantees" split is enforced in the type system.

## Status

This repo is built in milestones; see the commit history and `ARCHITECTURE.md`.

## License

MIT. See [LICENSE](./LICENSE).
