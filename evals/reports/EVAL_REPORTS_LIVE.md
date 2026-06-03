# Eval reports (live, real models)

Real figures, not stub numbers. The model-driven evals below were run against
live Claude models through the `claude` CLI (subscription auth), on 2026-06-03.
Models: **Claude Haiku** for classification and angle selection, **Claude
Sonnet** for the LLM-as-judge and the inbound agent. The deterministic evals
(opt-out, draft gate) measure code, so their figures are the same in CI.

Reproduce the model-driven runs with the `--live` flag on each eval; the
deterministic ones run anywhere with `python -m evals.run_all`.

> **Redacted knobs.** The model-driven figures were produced with the
> production-style prompts and tuning, which are proprietary and redacted from
> this public build (the prompt text here is a placeholder stub). The eval
> harness and the labeled golden sets are included and run, but re-running
> `--live` on the stub prompts will not reproduce these exact numbers. The
> deterministic evals (opt-out, draft gate) depend on no redacted knobs and
> reproduce exactly.

---

## Classification + quarantine (live Haiku, n=40)

```
segment accuracy:    0.875
archetype accuracy:  0.825
pitch precision:     1.000   (safety: never pitched a truly out-of-scope shop)
quarantine recall:   1.000   (safety: caught every truly out-of-scope shop)
needs-retry:         0
```

Archetype confusion (true -> predicted):
- `euro_specialist -> independent_general`: 1
- `hd_diesel -> independent_general`: 1
- `hd_diesel -> unclear`: 1
- `independent_general -> out_of_scope`: 4

Read: the model errs toward caution. The four `independent_general ->
out_of_scope` misses are in-scope shops it declined to pitch. That costs reach
but never produces a wrong send, which is why both safety metrics stay at 1.000
while raw accuracy is an honest 0.825.

## Opt-out detection (deterministic, n=20)

```
precision: 1.000
recall:    1.000   (safety: a missed opt-out is a CAN-SPAM violation)
```

The subject is a regex detector, so these are real measurements of real code,
including the adversarial "stop by anytime" case it correctly ignores.

## Draft safety-gate (deterministic, n=18)

```
detection rate:   1.000   (every planted violation caught)
false positives:  0       (every clean draft passed)
```

## Angle-quality (live LLM-as-judge, n=24 picks)

```
mean score: 0.679
min score:  0.150
below 0.6 threshold: 8 of 24
```

This is the eval doing real work. The judge flagged genuine angle mismatches:
`Hybrid Battery Experts -> specialty_euro`, `Quick Lube Express -> bulk_supply`,
`Caliber Collision -> local_proximity`, and others. The constrained shortlist
sometimes picks a defensible-but-weak angle. **Next iteration:** tighten the
archetype-to-angle shortlists for hybrid, quick-lube, and collision shops. The
eval exists to surface exactly this, and it did.

## Inbound responder (live Agent SDK, real Sonnet, n=10)

```
opt-out recall:                       1.000
price leaks in approved drafts:       0
name-drop violations in approved:     0
routes: auto_draft=3, escalate=2, noise=1, opt_out=4
```

The real agent ran the full loop: it drafted 3 grounded replies, escalated 2 it
was unsure about, and across every approved draft it never quoted a price or
named a customer outside the allowlist. The deterministic guards held against a
live model end to end.
