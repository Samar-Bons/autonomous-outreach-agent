# ABOUTME: End-to-end test of the full pipeline on synthetic seed data with the stub LLM.
# ABOUTME: Real wiring everywhere except the LLM seam; proves the funnel, suppression, and caps.
from __future__ import annotations

from datetime import UTC, date, datetime

from outreach_agent.classify import ConstrainedAnglePicker, LLMClassifier
from outreach_agent.copy import TemplateCopyGenerator, TemplateStore
from outreach_agent.delivery import DryRunSender
from outreach_agent.domain import Draft, ScheduledSend, SuppressionEntry
from outreach_agent.domain.enums import SuppressionReason
from outreach_agent.enrich import SyntheticEmailFinder, SyntheticEmailVerifier
from outreach_agent.llm import RuleBasedStubLLM
from outreach_agent.pipeline import Pipeline, PipelineResult
from outreach_agent.protocols import EmailSender
from outreach_agent.safety import InMemorySuppressionStore, default_gate
from outreach_agent.schedule import FixedClock, WarmupWavePlanner
from outreach_agent.sources import DEFAULT_SEED_PATH, CsvDataSource

# A known Monday, so wave offsets land on weekdays deterministically.
_MONDAY = date(2026, 4, 20)


def _build(suppression: InMemorySuppressionStore, sender: EmailSender) -> Pipeline:
    llm = RuleBasedStubLLM()
    clock = FixedClock(_MONDAY, datetime(2026, 4, 20, 9, 0, tzinfo=UTC))
    return Pipeline(
        source=CsvDataSource(DEFAULT_SEED_PATH),
        classifier=LLMClassifier(llm),
        angle_picker=ConstrainedAnglePicker(llm),
        email_finder=SyntheticEmailFinder(),
        email_verifier=SyntheticEmailVerifier(),
        copy_generator=TemplateCopyGenerator(TemplateStore()),
        gate=default_gate(),
        suppression=suppression,
        planner=WarmupWavePlanner(clock, campaign="demo"),
        sender=sender,
    )


def test_clean_run_funnel() -> None:
    sender = DryRunSender()
    pipeline = _build(InMemorySuppressionStore(), sender)
    result = pipeline.run()

    assert isinstance(result, PipelineResult)
    assert result.total_prospects == 20
    # 3 out-of-scope businesses + 1 mobile mechanic are quarantined.
    assert result.quarantined == 4
    # One in-scope shop has no website, so no email can be found.
    assert result.no_email == 1
    # 15 in-scope, enriched prospects x 4 waves.
    assert result.drafts_generated == 60
    assert result.drafts_blocked == 0
    assert result.scheduled == 60
    assert result.sent == 60
    assert len(sender.sent) == 60


def test_no_send_lands_on_a_weekend() -> None:
    sender = DryRunSender()
    _build(InMemorySuppressionStore(), sender).run()
    for scheduled, _ in sender.sent:
        assert scheduled.send_at.weekday() < 5


def test_idempotency_keys_are_unique_per_prospect_wave() -> None:
    sender = DryRunSender()
    _build(InMemorySuppressionStore(), sender).run()
    keys = [scheduled.idem_key for scheduled, _ in sender.sent]
    assert len(keys) == len(set(keys))


def test_suppressed_email_is_never_sent() -> None:
    suppression = InMemorySuppressionStore()
    # Suppress the address the finder will derive for one in-scope prospect.
    prospects = CsvDataSource(DEFAULT_SEED_PATH).load()
    target = next(p for p in prospects if p.id == "p01")
    suppressed_email = SyntheticEmailFinder().find(target)
    assert suppressed_email is not None
    suppression.add(
        SuppressionEntry(
            email=suppressed_email,
            reason=SuppressionReason.OPT_OUT,
            source="test",
            added_at=datetime(2026, 4, 19, 12, 0, tzinfo=UTC),
        )
    )

    sender = DryRunSender()
    result = _build(suppression, sender).run()

    assert result.suppressed_skipped == 1
    assert result.drafts_generated == 56  # one prospect (4 waves) held back
    assert result.sent == 56
    assert all(scheduled.email != suppressed_email for scheduled, _ in sender.sent)


class FailOneSender:
    """EmailSender stub that fails the send for one chosen email and succeeds otherwise."""

    def __init__(self, fail_email: str) -> None:
        self._fail_email = fail_email
        self.sent: list[tuple[ScheduledSend, Draft]] = []

    def send(self, scheduled: ScheduledSend, draft: Draft) -> bool:
        if scheduled.email == self._fail_email:
            return False
        self.sent.append((scheduled, draft))
        return True


def test_failed_sends_are_not_counted() -> None:
    # Pick a real scheduled email, then run with a sender that fails just that one.
    probe = DryRunSender()
    _build(InMemorySuppressionStore(), probe).run()
    fail_email = probe.sent[0][0].email
    fail_count = sum(1 for scheduled, _ in probe.sent if scheduled.email == fail_email)

    sender = FailOneSender(fail_email)
    result = _build(InMemorySuppressionStore(), sender).run()

    assert result.sent < result.scheduled
    assert result.sent == len(sender.sent)
    assert result.sent == result.scheduled - fail_count
