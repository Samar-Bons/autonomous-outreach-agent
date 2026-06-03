# ABOUTME: The deterministic pipeline orchestrator. It composes the stages; it is not an agent.
# ABOUTME: Control flow is plain code by design, so no safety guarantee depends on a model.
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .domain import Draft, ScheduledSend
from .protocols import (
    AnglePicker,
    Classifier,
    CopyGenerator,
    DataSource,
    EmailFinder,
    EmailSender,
    EmailVerifier,
    SafetyGate,
    SuppressionStore,
    WavePlanner,
)

_DEFAULT_WAVES: tuple[int, ...] = (1, 2, 3, 4)


@dataclass(frozen=True)
class PipelineResult:
    """A funnel-shaped summary of one pipeline run."""

    total_prospects: int
    quarantined: int
    no_angle: int
    no_email: int
    suppressed_skipped: int
    drafts_generated: int
    drafts_blocked: int
    scheduled: int
    sent: int


class Pipeline:
    """Runs source -> classify -> enrich -> generate -> gate -> schedule -> send.

    Every stage is injected, so the same orchestrator runs the real components in
    production and the stub-backed components in tests. The orchestrator itself
    holds no LLM: the model lives only inside the classifier and angle picker.
    Copy generation is deterministic template rendering, and the safety
    guarantees (suppression, the gate, caps) are this plain code.
    """

    def __init__(
        self,
        *,
        source: DataSource,
        classifier: Classifier,
        angle_picker: AnglePicker,
        email_finder: EmailFinder,
        email_verifier: EmailVerifier,
        copy_generator: CopyGenerator,
        gate: SafetyGate,
        suppression: SuppressionStore,
        planner: WavePlanner,
        sender: EmailSender,
        waves: Sequence[int] = _DEFAULT_WAVES,
    ) -> None:
        self._source = source
        self._classifier = classifier
        self._picker = angle_picker
        self._finder = email_finder
        self._verifier = email_verifier
        self._copy = copy_generator
        self._gate = gate
        self._suppression = suppression
        self._planner = planner
        self._sender = sender
        self._waves = tuple(waves)

    def run(self) -> PipelineResult:
        prospects = list(self._source.load())
        classifications = self._classifier.classify(prospects)

        quarantined = no_angle = no_email = suppressed = 0
        drafts: list[Draft] = []
        blocked = 0

        for prospect, classification in zip(prospects, classifications, strict=True):
            if classification.is_quarantined:
                quarantined += 1
                continue
            angle = self._picker.pick(prospect, classification)
            if angle is None:
                no_angle += 1
                continue
            email = self._finder.find(prospect)
            if email is None or not self._verifier.verify(email):
                no_email += 1
                continue
            if self._suppression.is_suppressed(email):
                suppressed += 1
                continue

            enriched = prospect.model_copy(update={"email": email})
            for wave in self._waves:
                draft = self._copy.generate(enriched, classification, angle, wave)
                if self._gate.validate(draft).passed:
                    drafts.append(draft)
                else:
                    blocked += 1

        scheduled: list[ScheduledSend] = self._planner.plan(drafts, {}) if drafts else []
        sent = sum(
            1
            for send, draft in zip(scheduled, drafts, strict=True)
            if self._sender.send(send, draft)
        )

        return PipelineResult(
            total_prospects=len(prospects),
            quarantined=quarantined,
            no_angle=no_angle,
            no_email=no_email,
            suppressed_skipped=suppressed,
            drafts_generated=len(drafts),
            drafts_blocked=blocked,
            scheduled=len(scheduled),
            sent=sent,
        )
