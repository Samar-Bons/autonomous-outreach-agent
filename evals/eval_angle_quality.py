# ABOUTME: Eval #4: an LLM-as-judge harness scoring whether the chosen angle fits the prospect.
# ABOUTME: CI runs a deterministic stub judge; --live scores with a real model.
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from outreach_agent.classify import ConstrainedAnglePicker, LLMClassifier
from outreach_agent.domain import AngleSelection, Classification, Prospect
from outreach_agent.domain.enums import ModelTier
from outreach_agent.llm import RuleBasedStubLLM, strip_code_fences
from outreach_agent.protocols import LLMClient

from .framework import load_golden

JUDGE_MARKER = "TASK=judge_angle_fit"
GOLDEN_PATH = Path(__file__).parent / "golden" / "classification.jsonl"
THRESHOLD = 0.6


@dataclass(frozen=True)
class AngleQualityMetrics:
    """Aggregate judge scores for the angles the picker chose."""

    count: int
    mean_score: float
    min_score: float
    below_threshold: list[str]


def build_judge_prompt(
    prospect: Prospect, classification: Classification, angle: AngleSelection
) -> tuple[str, str]:
    """Ask a judge model to rate how well an angle fits a business, 0 to 1."""
    # Production judge prompt is proprietary and omitted from this reference build.
    system = (
        "Rate how well the chosen angle fits the business, 0.0 to 1.0. "
        "Production prompt text is omitted from this reference build."
    )
    user = (
        f"{JUDGE_MARKER}\n"
        f"Business: {prospect.name} ({prospect.city}); "
        f"segment={classification.segment.value}; archetype={classification.archetype.value}\n"
        f"Chosen angle: {angle.angle_key}\n"
        f"Candidates considered: {', '.join(angle.candidates)}\n\n"
        'Return JSON {"score": <0.0-1.0>, "reason": "<short>"}.'
    )
    return system, user


def parse_judge_score(text: str) -> float | None:
    """Extract a 0-1 score from a judge response, or None if malformed."""
    body = strip_code_fences(text)
    try:
        raw = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    score = cast("dict[str, object]", raw).get("score")
    if isinstance(score, int | float) and 0.0 <= float(score) <= 1.0:
        return float(score)
    return None


class _ConstantJudge:
    """A deterministic stub judge for CI; returns a fixed passing score."""

    def __init__(self, score: float) -> None:
        self._score = score

    def complete(self, *, tier: ModelTier, system: str, user: str, max_tokens: int = 1024) -> str:
        return json.dumps({"score": self._score, "reason": "stub judge"})


def run(
    classifier_llm: LLMClient | None = None,
    picker_llm: LLMClient | None = None,
    judge_llm: LLMClient | None = None,
) -> AngleQualityMetrics:
    """Classify and pick angles for the golden set, then judge each chosen angle."""
    classifier_llm = classifier_llm or RuleBasedStubLLM()
    picker_llm = picker_llm or RuleBasedStubLLM()
    judge_llm = judge_llm or _ConstantJudge(0.9)

    rows = load_golden(GOLDEN_PATH)
    prospects = [row.to_prospect() for row in rows]
    classifications = LLMClassifier(classifier_llm).classify(prospects)
    picker = ConstrainedAnglePicker(picker_llm)

    scores: list[float] = []
    below: list[str] = []
    for prospect, classification in zip(prospects, classifications, strict=True):
        selection = picker.pick(prospect, classification)
        if selection is None:
            continue
        system, user = build_judge_prompt(prospect, classification, selection)
        score = parse_judge_score(
            judge_llm.complete(tier=ModelTier.SONNET, system=system, user=user)
        )
        score = score if score is not None else 0.0
        scores.append(score)
        if score < THRESHOLD:
            below.append(f"{prospect.name}: {selection.angle_key}")

    return AngleQualityMetrics(
        count=len(scores),
        mean_score=sum(scores) / len(scores) if scores else 1.0,
        min_score=min(scores) if scores else 1.0,
        below_threshold=below,
    )


def to_markdown(metrics: AngleQualityMetrics) -> str:
    """Render angle-quality metrics as a Markdown fragment."""
    lines = [
        "# Angle-quality eval (LLM-as-judge)",
        "",
        f"- angles judged: {metrics.count}",
        f"- mean score: {metrics.mean_score:.3f}",
        f"- min score: {metrics.min_score:.3f}",
        f"- below threshold ({THRESHOLD}): {len(metrics.below_threshold)}",
    ]
    for entry in metrics.below_threshold:
        lines.append(f"  - {entry}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the angle-quality eval.")
    parser.add_argument("--live", action="store_true", help="Judge with a real model.")
    parser.add_argument(
        "--cache",
        default=None,
        help="Disk cache path for live calls (makes a run resumable).",
    )
    args = parser.parse_args()

    if not args.live:
        metrics = run()
        print(to_markdown(metrics))
        return

    from outreach_agent.config import load_config
    from outreach_agent.llm import ClaudeCliClient, DiskCachedLLMClient

    # Live runs go through the Claude CLI (subscription auth). Wrapping in the
    # disk cache makes the run resumable: a re-run reuses completed calls.
    base: LLMClient = ClaudeCliClient(load_config())
    if args.cache:
        base = DiskCachedLLMClient(base, Path(args.cache))
    metrics = run(classifier_llm=base, picker_llm=base, judge_llm=base)
    print(to_markdown(metrics))


if __name__ == "__main__":
    main()
