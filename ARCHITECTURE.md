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
llm/           LLMClient   -> AnthropicClient + ClaudeCliClient (real) + RuleBasedStubLLM (tests)
classify/      Classifier + AnglePicker (two-stage, constrained)
enrich/        EmailFinder + EmailVerifier (synthetic, deterministic)
copy/          template store + CopyGenerator
safety/        DraftCheck chain + SafetyGate + SuppressionStore + OptOutDetector
schedule/      WavePlanner + Clock
delivery/      EmailSender -> DryRunSender (default)
inbound/       InboundResponder + guards (core) ; AgentSdkRunner + tools (Agent SDK)
pipeline.py    the orchestrator, dependency-injected
```

## The orchestrator is deterministic on purpose

`pipeline.py` is plain Python. It does not contain or call an LLM. The model is
confined to the classify and angle-pick stages (copy is deterministic template
rendering); the control flow, the suppression check, the cap enforcement, and
the gate all run as ordinary code.

Waves are scheduled up front, so honoring an opt-out that arrives after wave 1
is a separate, deterministic sweep: `cancel_suppressed_sends` runs each cycle
and cancels any still-scheduled wave to a now-suppressed address (the reference
build's stand-in for the production audit pass). Suppression is enforced both at
scheduling time and by this sweep, so a late opt-out still cancels waves 2-4.

This is a deliberate decision, not an oversight. An LLM driving the
orchestration loop (deciding what to run, in what order, with what volume) is
less reliable and less auditable than code, and it puts a model in the one place
where a wrong step is most expensive. Reliability lives in the deterministic
shell; the model is a function call inside it.

## The one agentic component: inbound

The inbound responder is the only place an agent loop is the right tool, because
replying to a free-text email genuinely benefits from multi-step tool use
(search the knowledge base, look up an approved reference customer, then draft).
It is built on the Claude Agent SDK and constrained to two in-process tools.

The same thesis applies: deterministic guards wrap the agent. An opt-out is
caught before any model call and routed straight to suppression; the agent's
output is policed by a price guard and a name-drop allowlist, and anything that
trips them is escalated to a human. The SDK runner sits behind an `AgentRunner`
seam, so the guards, knowledge base, and opt-out routing are fully tested in CI
with a faked runner, while the real agent loop runs via a live-gated test.

### Why the inbound agent is safe to point at untrusted email

Inbound email is attacker-controlled text, so the drafting agent is wrapped in
deterministic guards it cannot talk its way past:

1. Opt-out detection runs first, deterministically, and suppresses before any
   model call. Opt-outs never reach the LLM.
2. The price guard and name-drop allowlist run on the model's output text, not
   its self-report, so a prompt-injected draft that quotes a price, or names a
   customer from our list it did not declare, is downgraded to a human
   escalation. A wholly fabricated reference in free prose is the residual case,
   caught at human approval rather than by the guard.
3. The agent is confined to two read-only knowledge-base tools. It has no
   filesystem, shell, network, or write access.
4. `setting_sources=[]` keeps project, user, and global config out of the agent,
   so no ambient instruction can widen its capabilities.
5. `max_turns` bounds the loop, and every result is a draft a human approves.
   The agent never sends.

The key idea: the guards police the output, so injection in the email body
cannot bypass them.

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
true opt-out detection. Each eval runs in CI with a deterministic stub and
against a real model via `--live`. `python -m evals.run_all` regenerates the
checked-in report at [`evals/reports/EVAL_REPORTS.md`](./evals/reports/EVAL_REPORTS.md).

Five suites: classification + quarantine precision, opt-out detection, the draft
safety-gate, angle-pick quality (LLM-as-judge), and the inbound responder's
deterministic guarantees.

## Milestones

- **M0** scaffold + frozen contracts (domain + protocols)
- **M1** classification + angle pipeline + eval #1
- **M2** safety engine + evals #2 and #3
- **M3** copy generation + enrichment + scheduler
- **M4** deterministic pipeline orchestrator + e2e + eval #4
- **M4b** Claude Agent SDK inbound responder + eval #5
- **M5** polish, docs, checked-in eval reports
