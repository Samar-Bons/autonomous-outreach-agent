# Lessons

Failure modes this system is built to prevent. Each one came from running an
outbound pipeline against real inboxes; each is now guarded by a regression test
in [`tests/regression/`](./tests/regression). The lessons are generic; the
numbers and clients are not in this repo.

## 1. A safety check must not depend on state someone else can mutate

A follow-up once went to a prospect who had replied "stop." The opt-out
deduplication keyed on the inbox's read/unread state, which a human reading the
inbox owns and can flip. The check depended on state outside the system's
control.

**Fix:** opt-out detection is deterministic and runs *ahead of* the model, and
dedup keys on a log the system fully owns. A bare "stop" suppresses; "stop by
anytime" deliberately does not. Guarded by `test_optout_is_deterministic_and_conservative`.

## 2. Safety gates fail closed, never open

An early version let a draft ship when the validating model call errored
(fail-open). A wrong send is unrecoverable, so the default must be to *not* send.

**Fix:** the gate blocks on any BLOCK-severity finding, and a draft that leaks a
template variable or pitches the wrong product is held, not trusted. Guarded by
`test_gate_fails_closed_on_any_block`.

## 3. Never let a config fallthrough produce a silent zero

A scheduling table that only covered the ramp dates returned no cap for dates
past it, which silently scheduled zero sends with no error. Silence read as
success.

**Fix:** the planner falls through to a steady-state cap past the explicit
ramp, so a date beyond the table still schedules. Guarded by
`test_scheduler_has_no_silent_zero_past_the_ramp`.

## 4. A model failure is not a verdict

When the classifier's model call failed, an early version coerced the result
into a default label, silently mislabeling and sometimes mis-pitching shops.

**Fix:** a model failure yields `NEEDS_RETRY` (a quarantine state), kept distinct
from `UNCLEAR` (a real "cannot tell" decision). The system abstains rather than
inventing a label. Guarded by `test_model_failure_never_becomes_a_label`.

## 5. Idempotency is not optional when retries exist

A naive re-run once appended instead of overwriting and grew unbounded. Anything
that can retry must carry an idempotency key.

**Fix:** every scheduled send carries a deterministic `idem_key` of
campaign/email/wave, so a re-run targets the same record rather than duplicating
it. Guarded by `test_idempotency_keys_are_stable_across_runs`.
