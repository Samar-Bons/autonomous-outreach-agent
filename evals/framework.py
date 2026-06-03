# ABOUTME: The classification eval harness: golden-set loading and metric computation.
# ABOUTME: Reports pitch precision and quarantine recall, the two safety-relevant numbers.
from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from outreach_agent.domain import Classification, Prospect
from outreach_agent.domain.enums import QUARANTINE_ARCHETYPES, Archetype, Segment


@dataclass(frozen=True)
class GoldenRow:
    """One labeled prospect: its fields plus the ground-truth segment and archetype."""

    id: str
    name: str
    city: str
    true_segment: Segment
    true_archetype: Archetype
    sic: str | None = None
    employees: int | None = None
    website: str | None = None

    def to_prospect(self) -> Prospect:
        return Prospect(
            id=self.id,
            name=self.name,
            city=self.city,
            sic=self.sic,
            employees=self.employees,
            website=self.website,
        )

    @property
    def truly_quarantine(self) -> bool:
        return self.true_archetype in QUARANTINE_ARCHETYPES


@dataclass(frozen=True)
class ClassificationMetrics:
    """Aggregate quality of one classification run."""

    total: int
    segment_accuracy: float
    archetype_accuracy: float
    pitch_precision: float
    quarantine_recall: float
    needs_retry: int
    confusion: dict[str, int]


def load_golden(path: Path) -> list[GoldenRow]:
    """Load labeled prospects from a JSONL golden file."""
    rows: list[GoldenRow] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        rows.append(
            GoldenRow(
                id=str(obj["id"]),
                name=str(obj["name"]),
                city=str(obj["city"]),
                true_segment=Segment(obj["true_segment"]),
                true_archetype=Archetype(obj["true_archetype"]),
                sic=obj.get("sic"),
                employees=obj.get("employees"),
                website=obj.get("website"),
            )
        )
    return rows


def evaluate(
    rows: Sequence[GoldenRow], predictions: Sequence[Classification]
) -> ClassificationMetrics:
    """Score predictions against the golden labels.

    ``pitch_precision`` is the safety-critical number: of the prospects the system
    chose to pitch (predicted not-quarantine), the fraction that were truly in
    scope. ``quarantine_recall`` is the fraction of truly out-of-scope prospects
    the system correctly held back.
    """
    if len(rows) != len(predictions):
        raise ValueError("rows and predictions must align one-to-one")

    total = len(rows)
    seg_correct = 0
    arch_correct = 0
    needs_retry = 0
    pitched = 0
    pitched_correct = 0
    truly_quarantine = 0
    quarantine_caught = 0
    confusion: Counter[str] = Counter()

    for row, pred in zip(rows, predictions, strict=True):
        if pred.archetype is Archetype.NEEDS_RETRY:
            needs_retry += 1
        if pred.segment is row.true_segment:
            seg_correct += 1
        if pred.archetype is row.true_archetype:
            arch_correct += 1
        else:
            confusion[f"{row.true_archetype.value}->{pred.archetype.value}"] += 1

        if row.truly_quarantine:
            truly_quarantine += 1
            if pred.is_quarantined:
                quarantine_caught += 1
        if not pred.is_quarantined:
            pitched += 1
            if not row.truly_quarantine:
                pitched_correct += 1

    return ClassificationMetrics(
        total=total,
        segment_accuracy=seg_correct / total if total else 1.0,
        archetype_accuracy=arch_correct / total if total else 1.0,
        pitch_precision=pitched_correct / pitched if pitched else 1.0,
        quarantine_recall=quarantine_caught / truly_quarantine if truly_quarantine else 1.0,
        needs_retry=needs_retry,
        confusion=dict(confusion),
    )


def to_markdown(metrics: ClassificationMetrics) -> str:
    """Render metrics as a Markdown report fragment."""
    lines = [
        "# Classification eval",
        "",
        f"- prospects: {metrics.total}",
        f"- segment accuracy: {metrics.segment_accuracy:.3f}",
        f"- archetype accuracy: {metrics.archetype_accuracy:.3f}",
        f"- pitch precision (safety): {metrics.pitch_precision:.3f}",
        f"- quarantine recall (safety): {metrics.quarantine_recall:.3f}",
        f"- needs-retry: {metrics.needs_retry}",
    ]
    if metrics.confusion:
        lines.append("")
        lines.append("## Archetype confusion (true -> predicted)")
        for pair, count in sorted(metrics.confusion.items()):
            lines.append(f"- {pair}: {count}")
    return "\n".join(lines) + "\n"
