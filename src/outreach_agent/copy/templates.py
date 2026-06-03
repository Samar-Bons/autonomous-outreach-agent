# ABOUTME: Loads the seed copy templates once and serves (subject, body) pairs by key.
# ABOUTME: A missing (segment, angle, wave) is a KeyError, never a silent empty render.
from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path

from ..domain.enums import Segment, Wave

# templates.py -> copy -> outreach_agent -> src -> repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATES_PATH = _REPO_ROOT / "data" / "seed" / "templates.json"

# Shape of the loaded JSON: segment -> angle_key -> wave-as-str -> {subject, body}.
_TemplateMap = dict[str, dict[str, dict[str, dict[str, str]]]]


class TemplateStore:
    """Holds the copy templates and resolves one (subject, body) pair per request.

    The JSON file is read once on first access and cached. Keys are validated on
    lookup so a typo surfaces as a clear KeyError rather than an empty draft.
    """

    def __init__(self, path: Path = DEFAULT_TEMPLATES_PATH) -> None:
        self._path = path

    @cached_property
    def _templates(self) -> _TemplateMap:
        raw: object = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"templates file is not a JSON object: {self._path}")
        return raw  # type: ignore[return-value]

    def get(self, segment: Segment, angle_key: str, wave: Wave) -> tuple[str, str]:
        """Return the (subject_template, body_template) for one key triple.

        Raises KeyError naming the missing level so a gap in the catalog is loud.
        """
        by_angle = self._templates.get(segment.value)
        if by_angle is None:
            raise KeyError(f"no templates for segment {segment.value!r}")
        by_wave = by_angle.get(angle_key)
        if by_wave is None:
            raise KeyError(f"no templates for angle {angle_key!r} in segment {segment.value!r}")
        entry = by_wave.get(str(wave.value))
        if entry is None:
            raise KeyError(
                f"no template for wave {wave.value} of angle {angle_key!r} "
                f"in segment {segment.value!r}"
            )
        return entry["subject"], entry["body"]
