# ABOUTME: Integration test: classification feeding the angle picker over a mixed set.
# ABOUTME: Confirms quarantined prospects get no angle and in-scope ones get a valid angle.
from __future__ import annotations

from outreach_agent.classify import ConstrainedAnglePicker, LLMClassifier, candidate_angles
from outreach_agent.domain import Prospect
from outreach_agent.llm import RuleBasedStubLLM


def _prospects() -> list[Prospect]:
    return [
        Prospect(id="diesel", name="Big Rig Diesel Service", city="Dallas", sic="Truck Repair"),
        Prospect(id="euro", name="Euro Auto Werks", city="Plano", sic="Auto Repair"),
        Prospect(id="salon", name="Sunny Nail Salon", city="Frisco", sic="Personal Care"),
        Prospect(id="mobile", name="Mike's Mobile Mechanic", city="Irving", sic="Mobile Auto"),
        Prospect(id="general", name="Joe's Auto Repair", city="Arlington", sic="Auto Repair"),
    ]


def test_pipeline_quarantines_and_assigns_angles() -> None:
    llm = RuleBasedStubLLM()
    classifier = LLMClassifier(llm)
    picker = ConstrainedAnglePicker(llm)

    prospects = _prospects()
    classifications = classifier.classify(prospects)
    by_id = {c.prospect_id: c for c in classifications}

    # Out-of-scope and mobile mechanic are quarantined: no angle.
    assert picker.pick(prospects[2], by_id["salon"]) is None
    assert picker.pick(prospects[3], by_id["mobile"]) is None

    # In-scope prospects get an angle drawn from their archetype's candidates.
    for pid, prospect in zip(
        ["diesel", "euro", "general"], [prospects[0], prospects[1], prospects[4]], strict=True
    ):
        cls = by_id[pid]
        selection = picker.pick(prospect, cls)
        assert selection is not None
        assert selection.angle_key in candidate_angles(cls.segment, cls.archetype)
