# autonomous-outreach-agent

A reference implementation of an autonomous, safety-gated B2B cold-outreach agent.

It sources prospects, uses LLMs to decide who to pitch (and who to leave alone),
generates grounded per-prospect copy, runs every draft through a deterministic
safety gate, schedules multi-touch email sequences inside hard compliance and
deliverability guardrails, and drafts grounded replies to inbound email. It is
built to run unattended without ever sending the wrong thing to a stranger.

> **Thesis:** an LLM that touches the real world is a safety-critical system.
> The LLM does the reasoning; deterministic code holds the guarantees. No safety
> property is ever allowed to depend on the model being right.

This is a clean-room reference build modeled on a real production system.
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

The orchestrator that runs these stages is **plain deterministic Python, by
design**. The model lives only inside classify, angle-pick, and copy; it is
never in the control loop. Letting an LLM drive orchestration is the failure
mode this architecture exists to avoid.

## Inbound: the one agentic component

Replies are handled by a grounded responder built on the **Claude Agent SDK**.
It is restricted to two in-process knowledge-base tools (search + a
reference-customer allowlist) and drafts a strict-JSON reply that a human
approves before anything sends. Deterministic guards wrap the model: an opt-out
short-circuits to suppression before any model call, and a draft that quotes a
price or names a customer off the allowlist is downgraded to a human escalation.
The agent SDK is an optional dependency (`.[agent]`).

## Evals

The model-driven stages are covered by eval suites, not just unit tests. They
run in CI with a deterministic stub (no API key) and against a real model via
each eval's `--live` flag. Latest checked-in numbers
([evals/reports/EVAL_REPORTS.md](./evals/reports/EVAL_REPORTS.md)):

| Eval | Headline metric |
|---|---|
| Classification + quarantine | pitch precision **1.000**, quarantine recall **1.000** |
| Opt-out detection | recall **1.000** (the CAN-SPAM safety line), precision 1.000 |
| Draft safety-gate | detection **1.000**, 0 false positives |
| Angle-pick quality (LLM-as-judge) | mean score 0.900 |
| Inbound guarantees | opt-out recall **1.000**, both output guards trip |

## Quickstart

```bash
uv venv && uv pip install -e ".[dev,agent]"
pytest                  # 143 unit/integration/e2e tests, stub LLM, no API key
python -m evals.run_all # regenerate the eval report
outreach run-demo       # run the whole pipeline on synthetic seed data
```

`outreach run-demo` on the 20-row synthetic seed prints the funnel:

```
prospects sourced:   20
quarantined:         4
no angle / no email: 0 / 1
suppressed (skipped): 0
drafts generated:    60
drafts blocked:      0
scheduled / sent:    60 / 60
```

To run the model-driven stages, evals, or the inbound agent for real, copy
`.env.example` to `.env`, set `ANTHROPIC_API_KEY`, and use the `--live` flags or
`pytest -m live`.

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the design, the SOLID seams, the
deterministic-orchestrator decision, and how the "LLM reasons, code guarantees"
split is enforced in the type system.

## What's real and what's synthetic

Real: the architecture, every stage's logic, the safety gates, the evals, the
Agent SDK integration, strict typing, and the test suite. Synthetic: the
company, the prospect data, the knowledge base, and the email addresses. No
scrapers target any real site; the data-acquisition layer reads a CSV.

## License

MIT. See [LICENSE](./LICENSE).
