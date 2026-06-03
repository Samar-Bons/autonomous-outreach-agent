# ABOUTME: Deterministic draft-safety checks, the last line before an LLM-written email ships.
# ABOUTME: Each check is a small, pure DraftCheck flagging one failure class (leak/spam/slop/brand).
from __future__ import annotations

import re

from ..domain import CheckFailure, Draft, ValidationResult
from ..domain.enums import CheckSeverity, Segment

# Leftover template placeholder like ``{first_name}``. A rendered draft has none.
_MERGE_FIELD_RE = re.compile(r"\{[a-zA-Z0-9_]+\}")

# Spammy all-caps words that depress deliverability when they appear in a subject.
_SPAM_WORDS: frozenset[str] = frozenset({"FREE", "GUARANTEED", "URGENT", "WINNER", "ACT NOW"})

_SPAM_WORD_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in sorted(_SPAM_WORDS)) + r")\b",
    re.IGNORECASE,
)

# AI-slop tells: words a model overuses. Word-boundary, case-insensitive matching.
AI_SLOP_WORDS: frozenset[str] = frozenset(
    {
        "delve",
        "crucial",
        "robust",
        "seamless",
        "leverage",
        "elevate",
        "comprehensive",
        "nuanced",
        "multifaceted",
        "furthermore",
        "moreover",
        "additionally",
        "pivotal",
        "landscape",
        "tapestry",
        "underscore",
        "foster",
        "showcase",
        "intricate",
        "vibrant",
        "fundamental",
        "realm",
        "embark",
        "navigate",
        "testament",
        "unlock",
        "unleash",
        "holistic",
        "synergy",
    }
)

_AI_SLOP_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in sorted(AI_SLOP_WORDS)) + r")\b",
    re.IGNORECASE,
)

# Product-taxonomy tokens that must never appear for a given segment. Pitching a
# passenger-lube shop a heavy-duty diesel spec (or vice versa) is a hard error.
FORBIDDEN_TOKENS: dict[Segment, tuple[str, ...]] = {
    Segment.PASSENGER_LUBE: ("CK-4", "CJ-4", "15W-40", "DEF", "diesel exhaust fluid"),
    Segment.HD_DIESEL: ("0W-8", "0W-16"),
    Segment.DEALER_FLEET: (),
    Segment.OUT_OF_SCOPE: (),
}

# Role mailboxes that bounce or get ignored far more often than a named inbox.
_GENERIC_LOCAL_PARTS: frozenset[str] = frozenset({"info", "sales", "admin", "contact", "office"})

# Free providers where a generic local-part is normal and not a bounce signal.
_FREE_PROVIDERS: frozenset[str] = frozenset(
    {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com"}
)


def _result(draft: Draft, failures: tuple[CheckFailure, ...]) -> ValidationResult:
    """Build a single-check ValidationResult for ``draft``."""
    return ValidationResult(prospect_id=draft.prospect_id, wave=draft.wave, failures=failures)


class MergeFieldLeakCheck:
    """Flags any leftover ``{placeholder}`` left unrendered in subject or body."""

    @property
    def name(self) -> str:
        return "merge_field_leak"

    def check(self, draft: Draft) -> ValidationResult:
        leaked = _MERGE_FIELD_RE.findall(f"{draft.subject}\n{draft.body}")
        if not leaked:
            return _result(draft, ())
        unique = ", ".join(dict.fromkeys(leaked))
        failure = CheckFailure(
            check_name=self.name,
            severity=CheckSeverity.BLOCK,
            detail=f"unrendered merge fields: {unique}",
        )
        return _result(draft, (failure,))


class SpamMarkerCheck:
    """Flags subject-line spam markers: caps spam words, ``!!``/``??``, ``$$``, all-caps."""

    @property
    def name(self) -> str:
        return "spam_marker"

    def check(self, draft: Draft) -> ValidationResult:
        subject = draft.subject
        reason: str | None = None

        # Spam-word match is word-boundary + case-insensitive, so "react now" does
        # not hit "ACT NOW" and "free consultation" does not hit "FREE".
        match = _SPAM_WORD_RE.search(subject)
        if match is not None:
            reason = f"spam word: {match.group(0).upper()}"
        elif "!!" in subject or "??" in subject:
            reason = "repeated punctuation"
        elif "$$" in subject:
            reason = "currency spam ($$)"
        else:
            letters = [c for c in subject if c.isalpha()]
            if letters and sum(c.isupper() for c in letters) / len(letters) > 0.70:
                reason = "uppercase ratio over 0.70"

        if reason is None:
            return _result(draft, ())
        failure = CheckFailure(check_name=self.name, severity=CheckSeverity.BLOCK, detail=reason)
        return _result(draft, (failure,))


class AiSlopCheck:
    """Flags an em dash or any AI-slop vocabulary word in subject or body."""

    @property
    def name(self) -> str:
        return "ai_slop"

    def check(self, draft: Draft) -> ValidationResult:
        text = f"{draft.subject}\n{draft.body}"
        if "—" in text:
            failure = CheckFailure(
                check_name=self.name,
                severity=CheckSeverity.BLOCK,
                detail="em dash present",
            )
            return _result(draft, (failure,))
        match = _AI_SLOP_RE.search(text)
        if match is None:
            return _result(draft, ())
        failure = CheckFailure(
            check_name=self.name,
            severity=CheckSeverity.BLOCK,
            detail=f"ai-slop word: {match.group(0).lower()}",
        )
        return _result(draft, (failure,))


class ForbiddenBrandCheck:
    """Flags product tokens that belong to a different segment's taxonomy."""

    @property
    def name(self) -> str:
        return "forbidden_brand"

    def check(self, draft: Draft) -> ValidationResult:
        haystack = f"{draft.subject}\n{draft.body}".lower()
        for token in FORBIDDEN_TOKENS.get(draft.segment, ()):
            if token.lower() in haystack:
                failure = CheckFailure(
                    check_name=self.name,
                    severity=CheckSeverity.BLOCK,
                    detail=f"forbidden token for {draft.segment.value}: {token}",
                )
                return _result(draft, (failure,))
        return _result(draft, ())


class GenericAddressCheck:
    """Warns when a role mailbox at a business domain risks a high bounce rate."""

    @property
    def name(self) -> str:
        return "generic_address"

    def check(self, draft: Draft) -> ValidationResult:
        local, _, domain = draft.email.partition("@")
        local = local.lower()
        domain = domain.lower()
        if local in _GENERIC_LOCAL_PARTS and domain not in _FREE_PROVIDERS:
            failure = CheckFailure(
                check_name=self.name,
                severity=CheckSeverity.WARN,
                detail=f"generic role mailbox: {local}@{domain}",
            )
            return _result(draft, (failure,))
        return _result(draft, ())
