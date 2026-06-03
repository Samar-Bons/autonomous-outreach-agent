# ABOUTME: A small file-backed knowledge base the responder grounds its replies on.
# ABOUTME: Pure and dependency-free, so it is unit-tested without the agent SDK or a network.
from __future__ import annotations

import re
from pathlib import Path

_CUSTOMER_LINE = re.compile(r"^-\s*(.+?)\s*\(([^)]+)\)\s*$")
_WORD = re.compile(r"[a-z0-9]+")


class KnowledgeBase:
    """Loads the markdown knowledge base and answers grounded lookups.

    Two capabilities back the responder's tools: keyword search over the docs,
    and a strict reference-customer allowlist so the agent can never invent a
    customer to name-drop.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._docs: dict[str, str] = {}
        self._customers: list[tuple[str, str]] = []
        self._load()

    def _load(self) -> None:
        for path in sorted(self._root.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self._docs[path.stem] = text
            if path.stem == "customers":
                self._parse_customers(text)

    def _parse_customers(self, text: str) -> None:
        for line in text.splitlines():
            match = _CUSTOMER_LINE.match(line.strip())
            if match:
                self._customers.append((match.group(1).strip(), match.group(2).strip()))

    def search(self, query: str, limit: int = 3) -> list[str]:
        """Return the paragraphs most relevant to the query, best first."""
        terms = set(_WORD.findall(query.lower()))
        if not terms:
            return []
        scored: list[tuple[int, str]] = []
        for text in self._docs.values():
            for para in (p.strip() for p in text.split("\n\n")):
                if not para:
                    continue
                words = set(_WORD.findall(para.lower()))
                overlap = len(terms & words)
                if overlap:
                    scored.append((overlap, para))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [para for _, para in scored[:limit]]

    def reference_customers(self, city: str | None = None) -> list[str]:
        """Approved name-drop customers, optionally filtered to one city."""
        if city is None:
            return [f"{name} ({town})" for name, town in self._customers]
        wanted = city.strip().lower()
        return [f"{name} ({town})" for name, town in self._customers if town.lower() == wanted]

    def customer_names(self) -> set[str]:
        """The bare set of approved customer names, for validating name-drops."""
        return {name for name, _ in self._customers}
