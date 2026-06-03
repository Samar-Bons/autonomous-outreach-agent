# ABOUTME: Unit tests for the draft-safety checks and the aggregating DefaultSafetyGate.
# ABOUTME: Each check has a trigger case; a clean draft passes; severity and aggregation hold.
from __future__ import annotations

from outreach_agent.domain import Draft, ValidationResult
from outreach_agent.domain.enums import CheckSeverity, Segment, Wave
from outreach_agent.safety.checks import (
    AiSlopCheck,
    ForbiddenBrandCheck,
    GenericAddressCheck,
    MergeFieldLeakCheck,
    SpamMarkerCheck,
)
from outreach_agent.safety.gate import default_gate


def make_draft(
    *,
    email: str = "owner@joesauto.com",
    segment: Segment = Segment.PASSENGER_LUBE,
    subject: str = "Quick question about your oil supplier",
    body: str = "Hi, we stock the grades your shop uses. Worth a chat?",
) -> Draft:
    return Draft(
        prospect_id="p1",
        email=email,
        wave=Wave.INITIAL,
        segment=segment,
        angle_key="price",
        subject=subject,
        body=body,
    )


def _has_failure(result: ValidationResult, name: str, severity: CheckSeverity) -> bool:
    return any(f.check_name == name and f.severity is severity for f in result.failures)


def test_clean_draft_passes_the_gate() -> None:
    result = default_gate().validate(make_draft())
    assert result.failures == ()
    assert result.passed is True


def test_merge_field_leak_blocks() -> None:
    draft = make_draft(body="Hi {first_name}, quick question.")
    result = MergeFieldLeakCheck().check(draft)
    assert _has_failure(result, "merge_field_leak", CheckSeverity.BLOCK)
    assert result.passed is False


def test_spam_marker_caps_word_blocks() -> None:
    draft = make_draft(subject="FREE oil sample for your shop")
    result = SpamMarkerCheck().check(draft)
    assert _has_failure(result, "spam_marker", CheckSeverity.BLOCK)


def test_spam_marker_repeated_punctuation_blocks() -> None:
    draft = make_draft(subject="Are you in?? Let me know")
    result = SpamMarkerCheck().check(draft)
    assert _has_failure(result, "spam_marker", CheckSeverity.BLOCK)


def test_spam_marker_uppercase_ratio_blocks() -> None:
    draft = make_draft(subject="HEY THERE SHOP OWNER LOOK")
    result = SpamMarkerCheck().check(draft)
    assert _has_failure(result, "spam_marker", CheckSeverity.BLOCK)


def test_ai_slop_em_dash_blocks() -> None:
    draft = make_draft(body="We can help — really we can.")
    result = AiSlopCheck().check(draft)
    assert _has_failure(result, "ai_slop", CheckSeverity.BLOCK)


def test_ai_slop_word_blocks() -> None:
    draft = make_draft(body="We leverage our supply chain for your shop.")
    result = AiSlopCheck().check(draft)
    assert _has_failure(result, "ai_slop", CheckSeverity.BLOCK)


def test_ai_slop_word_is_case_insensitive_and_word_bounded() -> None:
    # "Leverage" capitalized triggers; a slop word embedded in a larger word does not.
    assert AiSlopCheck().check(make_draft(body="Leverage that.")).passed is False
    assert AiSlopCheck().check(make_draft(body="The fundamentalist shop.")).passed is True
    assert AiSlopCheck().check(make_draft(body="No slop here at all.")).passed is True


def test_forbidden_brand_is_segment_specific() -> None:
    # 15W-40 is a heavy-duty diesel grade: fine for HD_DIESEL, wrong for PASSENGER_LUBE.
    hd = make_draft(segment=Segment.HD_DIESEL, body="We stock 15W-40 for your fleet.")
    assert ForbiddenBrandCheck().check(hd).passed is True

    lube = make_draft(segment=Segment.PASSENGER_LUBE, body="We stock 15W-40 too.")
    result = ForbiddenBrandCheck().check(lube)
    assert _has_failure(result, "forbidden_brand", CheckSeverity.BLOCK)


def test_generic_address_warns_but_does_not_block() -> None:
    draft = make_draft(email="info@joesauto.com")
    result = GenericAddressCheck().check(draft)
    assert _has_failure(result, "generic_address", CheckSeverity.WARN)
    # WARN-only means the draft still passes.
    assert result.passed is True


def test_generic_address_on_free_provider_is_ignored() -> None:
    draft = make_draft(email="info@gmail.com")
    assert GenericAddressCheck().check(draft).passed is True
    assert GenericAddressCheck().check(draft).failures == ()


def test_warn_only_draft_passes_through_full_gate() -> None:
    # A generic-address WARN is the only finding; the gate verdict still passes.
    result = default_gate().validate(make_draft(email="sales@joesauto.com"))
    assert result.passed is True
    assert _has_failure(result, "generic_address", CheckSeverity.WARN)


def test_gate_aggregates_multiple_failures() -> None:
    # A draft that trips three checks at once: leak + spam + slop.
    draft = make_draft(
        subject="FREE quote",
        body="Hi {name}, we leverage scale for you.",
    )
    result = default_gate().validate(draft)
    names = {f.check_name for f in result.failures}
    assert {"merge_field_leak", "spam_marker", "ai_slop"} <= names
    assert result.passed is False


def test_any_block_fails_even_with_a_warn_present() -> None:
    draft = make_draft(email="info@joesauto.com", subject="URGENT offer")
    result = default_gate().validate(draft)
    severities = {f.severity for f in result.failures}
    assert CheckSeverity.WARN in severities
    assert CheckSeverity.BLOCK in severities
    assert result.passed is False
