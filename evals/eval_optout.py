# ABOUTME: Opt-out eval (eval #2): scores RegexOptOutDetector against a labeled golden set.
# ABOUTME: Recall is the safety-critical number; CLI prints Markdown, run() feeds the CI test.
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

from outreach_agent.domain import Reply
from outreach_agent.safety.optout import RegexOptOutDetector

GOLDEN_PATH = Path(__file__).parent / "golden" / "optout.jsonl"


@dataclass(frozen=True)
class OptOutRow:
    """One labeled reply: its fields plus the ground-truth opt-out verdict."""

    thread_id: str
    from_email: str
    subject: str
    body: str
    is_opt_out: bool

    def to_reply(self) -> Reply:
        return Reply(
            thread_id=self.thread_id,
            from_email=self.from_email,
            subject=self.subject,
            body=self.body,
        )


@dataclass(frozen=True)
class OptOutMetrics:
    """Aggregate quality of one opt-out detection run.

    ``recall`` is the safety-critical number: of the truly-opt-out replies, the
    fraction the detector caught. A single miss is a CAN-SPAM violation, so the
    CI gate requires recall == 1.0.
    """

    total: int
    precision: float
    recall: float
    false_negatives: list[str] = field(default_factory=list)
    false_positives: list[str] = field(default_factory=list)


def load_golden(path: Path) -> list[OptOutRow]:
    """Load labeled replies from a JSONL golden file."""
    rows: list[OptOutRow] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        rows.append(
            OptOutRow(
                thread_id=str(obj["thread_id"]),
                from_email=str(obj["from_email"]),
                subject=str(obj["subject"]),
                body=str(obj["body"]),
                is_opt_out=bool(obj["is_opt_out"]),
            )
        )
    return rows


def evaluate(rows: list[OptOutRow]) -> OptOutMetrics:
    """Run the detector over the golden rows and score precision/recall."""
    detector = RegexOptOutDetector()
    true_positives = 0
    false_positives: list[str] = []
    false_negatives: list[str] = []
    predicted_positive = 0
    truly_positive = 0

    for row in rows:
        predicted = detector.is_opt_out(row.to_reply())
        if row.is_opt_out:
            truly_positive += 1
        if predicted:
            predicted_positive += 1
        if predicted and row.is_opt_out:
            true_positives += 1
        elif predicted and not row.is_opt_out:
            false_positives.append(row.body)
        elif not predicted and row.is_opt_out:
            false_negatives.append(row.body)

    return OptOutMetrics(
        total=len(rows),
        precision=true_positives / predicted_positive if predicted_positive else 1.0,
        recall=true_positives / truly_positive if truly_positive else 1.0,
        false_negatives=false_negatives,
        false_positives=false_positives,
    )


def run() -> OptOutMetrics:
    """Load the golden set and score the deterministic detector against it."""
    return evaluate(load_golden(GOLDEN_PATH))


def to_markdown(metrics: OptOutMetrics) -> str:
    """Render metrics as a Markdown report fragment."""
    lines = [
        "# Opt-out eval",
        "",
        f"- replies: {metrics.total}",
        f"- precision: {metrics.precision:.3f}",
        f"- recall (safety): {metrics.recall:.3f}",
    ]
    if metrics.false_negatives:
        lines.append("")
        lines.append("## False negatives (missed opt-outs)")
        for body in metrics.false_negatives:
            lines.append(f"- {body!r}")
    if metrics.false_positives:
        lines.append("")
        lines.append("## False positives (over-suppressed)")
        for body in metrics.false_positives:
            lines.append(f"- {body!r}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the opt-out eval.")
    parser.parse_args()
    print(to_markdown(run()))


if __name__ == "__main__":
    main()
