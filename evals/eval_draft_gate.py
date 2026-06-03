# ABOUTME: Eval #3 for the deterministic draft-safety gate: a labeled in-code corpus of drafts.
# ABOUTME: Scores detection rate of planted violations and false positives on clean drafts.
from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass

from outreach_agent.domain import Draft
from outreach_agent.domain.enums import Segment, Wave
from outreach_agent.safety.gate import default_gate

# Each case is a draft plus the name of the check that *should* BLOCK it, or
# "clean" for a draft that must pass the whole gate untouched. ``GenericAddressCheck``
# only WARNs, so it is intentionally not used as a planted-violation expectation.


@dataclass(frozen=True)
class DraftCase:
    """One labeled draft: the expected BLOCKing check name, or ``"clean"``."""

    draft: Draft
    expected: str


def _draft(
    case_id: str,
    *,
    segment: Segment = Segment.PASSENGER_LUBE,
    subject: str = "Quick question about your oil supplier",
    body: str = "Hi, we stock the grades your shop uses. Worth a chat?",
    email: str = "owner@joesauto.com",
) -> Draft:
    return Draft(
        prospect_id=case_id,
        email=email,
        wave=Wave.INITIAL,
        segment=segment,
        angle_key="price",
        subject=subject,
        body=body,
    )


CORPUS: tuple[DraftCase, ...] = (
    # --- planted violations: merge-field leak ---
    DraftCase(
        _draft("leak-1", body="Hi {first_name}, quick question about oil."),
        "merge_field_leak",
    ),
    DraftCase(
        _draft("leak-2", subject="Question for {shop_name}"),
        "merge_field_leak",
    ),
    # --- planted violations: spam markers ---
    DraftCase(_draft("spam-1", subject="FREE oil sample for your shop"), "spam_marker"),
    DraftCase(_draft("spam-2", subject="ACT NOW on your oil order"), "spam_marker"),
    DraftCase(_draft("spam-3", subject="Are you in?? Reply today"), "spam_marker"),
    DraftCase(_draft("spam-4", subject="Save $$ on bulk oil"), "spam_marker"),
    DraftCase(_draft("spam-5", subject="HUGE BULK OIL DEAL TODAY ONLY"), "spam_marker"),
    # --- planted violations: AI slop ---
    DraftCase(_draft("slop-1", body="We can help — really we can."), "ai_slop"),
    DraftCase(
        _draft("slop-2", body="We leverage our supply chain to serve your shop."),
        "ai_slop",
    ),
    DraftCase(
        _draft("slop-3", subject="A robust oil supply for your shop"),
        "ai_slop",
    ),
    # --- planted violations: forbidden brand (segment-specific) ---
    DraftCase(
        _draft(
            "brand-1",
            segment=Segment.PASSENGER_LUBE,
            body="We also carry 15W-40 for heavier work.",
        ),
        "forbidden_brand",
    ),
    DraftCase(
        _draft(
            "brand-2",
            segment=Segment.PASSENGER_LUBE,
            body="Need DEF or diesel exhaust fluid too?",
        ),
        "forbidden_brand",
    ),
    DraftCase(
        _draft(
            "brand-3",
            segment=Segment.HD_DIESEL,
            body="We stock 0W-16 for your fleet.",
        ),
        "forbidden_brand",
    ),
    # --- clean drafts (must pass the whole gate) ---
    DraftCase(_draft("clean-1"), "clean"),
    DraftCase(
        _draft(
            "clean-2",
            segment=Segment.HD_DIESEL,
            body="We stock 15W-40 for your fleet at a fair price.",
        ),
        "clean",
    ),
    DraftCase(
        _draft(
            "clean-3",
            subject="Oil supply for Joe's Auto",
            body="Saw your shop on Main St. We deliver weekly. Open to a quick call?",
        ),
        "clean",
    ),
    DraftCase(
        _draft(
            "clean-4",
            email="info@gmail.com",
            body="Free shipping is not what we lead with; we lead on price.",
        ),
        "clean",
    ),
    DraftCase(
        _draft(
            "clean-5",
            segment=Segment.DEALER_FLEET,
            body="Bulk pricing for your dealership service bays. Worth a look?",
        ),
        "clean",
    ),
)


@dataclass(frozen=True)
class DraftGateMetrics:
    """Aggregate quality of one draft-gate eval run."""

    total: int
    planted: int
    clean: int
    detection_rate: float
    false_positive_count: int
    misses: tuple[str, ...]


def run() -> DraftGateMetrics:
    """Run the gate over the corpus and score detection and false positives."""
    return evaluate(CORPUS)


def evaluate(corpus: Sequence[DraftCase]) -> DraftGateMetrics:
    """Score the gate over ``corpus``.

    ``detection_rate`` is the fraction of planted violations whose expected check
    actually fired a BLOCK. ``false_positive_count`` is the number of clean drafts
    that drew any BLOCK at all.
    """
    gate = default_gate()
    planted = 0
    detected = 0
    clean = 0
    false_positives = 0
    misses: list[str] = []

    for case in corpus:
        result = gate.validate(case.draft)
        blocked_checks = {f.check_name for f in result.failures if f.severity.value == "block"}
        if case.expected == "clean":
            clean += 1
            if blocked_checks:
                false_positives += 1
                misses.append(f"{case.draft.prospect_id}: unexpected block {blocked_checks}")
            continue
        planted += 1
        if case.expected in blocked_checks:
            detected += 1
        else:
            misses.append(
                f"{case.draft.prospect_id}: expected {case.expected}, got {blocked_checks}"
            )

    return DraftGateMetrics(
        total=len(corpus),
        planted=planted,
        clean=clean,
        detection_rate=detected / planted if planted else 1.0,
        false_positive_count=false_positives,
        misses=tuple(misses),
    )


def to_markdown(metrics: DraftGateMetrics) -> str:
    """Render metrics as a Markdown report fragment."""
    lines = [
        "# Draft-gate eval",
        "",
        f"- drafts: {metrics.total}",
        f"- planted violations: {metrics.planted}",
        f"- clean drafts: {metrics.clean}",
        f"- detection rate: {metrics.detection_rate:.3f}",
        f"- false positives: {metrics.false_positive_count}",
    ]
    if metrics.misses:
        lines.append("")
        lines.append("## Misses")
        for miss in metrics.misses:
            lines.append(f"- {miss}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic draft-gate eval.")
    parser.parse_args()
    print(to_markdown(run()))


if __name__ == "__main__":
    main()
