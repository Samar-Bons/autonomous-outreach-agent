# ABOUTME: Deterministic opt-out detection that runs ahead of any LLM triage of a reply.
# ABOUTME: Two-path (short keyword / long phrase) design tuned for perfect recall on real opt-outs.
from __future__ import annotations

import re

from ..domain import Reply

# A reply at or below this length is treated as a terse keyword-style message
# (e.g. "stop", "unsubscribe", "remove me"). Above it, we require a full opt-out
# phrase and never honor a bare "stop", which is overwhelmingly conversational
# in longer text ("stop by anytime").
_SHORT_THRESHOLD = 30

# Single stop keywords that, when a short message reduces to one of them (modulo
# benign filler), unambiguously mean "do not email me again".
_SHORT_KEYWORDS: frozenset[str] = frozenset(
    {"stop", "unsubscribe", "remove", "cancel", "opt out", "no thanks"}
)

# Filler words allowed to surround a short keyword without changing its meaning.
# "remove me", "stop please", "no thanks", "opt me out" all still mean opt-out.
_FILLER_WORDS: frozenset[str] = frozenset(
    {"please", "thanks", "thank", "you", "me", "now", "the", "this", "emails", "email"}
)

# Full opt-out phrases matched anywhere in a longer body. Each is a word-boundary
# regex. Critically, "stop" only ever appears here bound to an action verb
# (emailing/sending/contacting); a bare "stop" never matches in the long path.
_LONG_PHRASES: tuple[str, ...] = (
    r"unsubscribe",
    r"opt\s+me\s+out",
    r"opt\s+out",
    r"take\s+me\s+off",
    r"remove\s+me",
    r"stop\s+emailing",
    r"stop\s+sending",
    r"stop\s+contacting",
    r"do\s+not\s+contact",
    r"don'?t\s+contact",
    r"no\s+longer\s+interested",
    r"please\s+remove",
)

_LONG_PATTERN = re.compile(r"\b(?:" + "|".join(_LONG_PHRASES) + r")\b")

# Strips surrounding punctuation/whitespace so "Stop!" and "stop." reduce cleanly.
_NON_WORD_EDGES = re.compile(r"^\W+|\W+$")


class RegexOptOutDetector:
    """Conservative, deterministic opt-out detector implementing ``OptOutDetector``.

    Two complementary paths:

    * PHRASE path (any length): a full opt-out *phrase* matches anywhere
      ("unsubscribe", "remove me", "stop emailing", "do not contact", ...). A
      bare "stop" never matches here, because in prose "stop" is almost always
      conversational ("feel free to stop by"); "stop" only triggers when bound
      to an action verb (stop emailing/sending/contacting).
    * SHORT-KEYWORD path (body <= 30 chars only): the terse message must reduce
      to a single bare stop keyword once benign filler is removed. This is the
      only way a bare "stop" / "remove" / "cancel" can fire, and it is gated on
      shortness so that "stop by anytime" never trips it.

    The design is intentionally conservative on precision and biased toward
    recall: missing a true opt-out is a CAN-SPAM violation, so this runs ahead of
    any model and the model is never given a chance to override a positive here.
    """

    def is_opt_out(self, reply: Reply) -> bool:
        body = reply.body.strip().lower()
        if not body:
            return False
        # A full opt-out phrase is unambiguous at any length; check it first.
        if self._long_path(body):
            return True
        # A bare stop keyword only counts in a terse, short message.
        if len(body) <= _SHORT_THRESHOLD:
            return self._short_path(body)
        return False

    def _short_path(self, body: str) -> bool:
        """True if the short body reduces to a single stop keyword plus filler.

        Multi-word keywords ("opt out", "no thanks") are consumed from the token
        stream first; what remains must be exactly one single-word keyword with
        every other token being benign filler.
        """
        tokens = [_NON_WORD_EDGES.sub("", tok) for tok in body.split()]
        tokens = [tok for tok in tokens if tok]
        if not tokens:
            return False

        keyword_count = 0
        remaining: list[str] = []
        i = 0
        while i < len(tokens):
            pair = f"{tokens[i]} {tokens[i + 1]}" if i + 1 < len(tokens) else ""
            if pair in _SHORT_KEYWORDS:
                keyword_count += 1
                i += 2
                continue
            if tokens[i] in _SHORT_KEYWORDS:
                keyword_count += 1
            else:
                remaining.append(tokens[i])
            i += 1

        if keyword_count != 1:
            return False
        return all(tok in _FILLER_WORDS for tok in remaining)

    def _long_path(self, body: str) -> bool:
        """True only if a full opt-out phrase appears in the longer body."""
        return _LONG_PATTERN.search(body) is not None
