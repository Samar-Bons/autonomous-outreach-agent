# Architecture

## The one idea

An LLM that emails strangers at volume is a safety-critical system. The failure
modes are asymmetric: sending nothing costs nothing, sending the wrong thing is
unrecoverable. So the system is split along a single line:

- **The LLM does the reasoning.** Is this shop a diesel fleet or a body shop?
  Which pitch fits? These are judgment calls, and the model makes them.
- **Deterministic code holds the guarantees.** Did this person opt out? Have we
  hit today's cap? Did this draft leak a template variable or pitch the wrong
  product? These are invariants, and plain code enforces them.

No safety property is allowed to depend on the model being right. That rule is
visible in the type system: model reasoning flows through one `LLMClient` seam,
while suppression, caps, dedup, and the safety checks are ordinary typed code
with exhaustive unit tests.

## Layers

```
domain/        frozen models + enums (the shared contract)
protocols.py   the interface layer: DataSource, LLMClient, Classifier,
               AnglePicker, EmailFinder, EmailVerifier, CopyGenerator,
               DraftCheck, SafetyGate, SuppressionStore, OptOutDetector,
               Clock, WavePlanner, EmailSender
config.py      model tiers, campaign settings, warmup caps, wave offsets

sources/       DataSource  -> CsvDataSource (synthetic seed)
llm/           LLMClient   -> AnthropicClient (real) + StubLLMClient (tests)
classify/      Classifier + AnglePicker (two-stage, constrained)
enrich/        EmailFinder + EmailVerifier (synthetic, deterministic)
copy/          template store + CopyGenerator
safety/        DraftCheck chain + SafetyGate + SuppressionStore + OptOutDetector
schedule/      WavePlanner + Clock
delivery/      EmailSender -> DryRunSender (default)
pipeline.py    the orchestrator, dependency-injected
```

## SOLID seams

- **Dependency inversion.** Every stage depends on a `Protocol`, never on a
  concrete class. The pipeline is assembled by injecting implementations, so the
  real Anthropic client and a deterministic stub are swapped freely. The whole
  pipeline runs in tests with zero tokens spent.
- **Open/closed safety gate.** The safety gate runs a chain of `DraftCheck`
  strategies. Adding a new rule means adding a class, not editing the gate.
- **Single responsibility.** Classification, angle selection, copy, validation,
  suppression, and scheduling are separate units with separate tests.
- **Liskov.** Stub and real implementations are behaviorally substitutable
  behind their Protocol; the e2e test exercises the same orchestrator the real
  run uses.

## Quarantine over guess

The classifier may return `NEEDS_RETRY` (a model failure) which is kept distinct
from `UNCLEAR` (a model decision that the shop is ambiguous). Both quarantine,
but only `NEEDS_RETRY` is retried. The system abstains under uncertainty rather
than inventing a default, because a wrong send is worse than no send.

## Eval strategy

Deterministic stages get unit tests. Model-driven stages get eval suites with
labeled data and explicit thresholds, including a hard recall-of-1.0 assertion on
true opt-out detection. See [`evals/`](./evals).

## Milestones

- **M0** scaffold + frozen contracts (domain + protocols)
- **M1** classification + angle pipeline + eval #1
- **M2** safety engine + evals #2 and #3
- **M3** copy generation + enrichment + scheduler
- **M4** pipeline orchestrator + e2e + eval #4
- **M5** polish, docs, checked-in eval reports
