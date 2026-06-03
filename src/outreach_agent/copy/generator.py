# ABOUTME: The deterministic copy generator: fills a seed template into a typed Draft.
# ABOUTME: Pure string substitution of {shop_name} and {city}; no model call, no randomness.
from __future__ import annotations

from ..domain import AngleSelection, Classification, Draft, Prospect
from ..domain.enums import Wave
from .templates import TemplateStore


class TemplateCopyGenerator:
    """Renders a Draft by substituting prospect fields into a seed template.

    The same prospect, angle, and wave always yield the same draft, which keeps
    the safety gate and the downstream pipeline reproducible.
    """

    def __init__(self, store: TemplateStore) -> None:
        self._store = store

    def generate(
        self,
        prospect: Prospect,
        classification: Classification,
        angle: AngleSelection,
        wave: int,
    ) -> Draft:
        if prospect.email is None:
            raise ValueError(f"prospect {prospect.id!r} has no email to render a draft for")
        wave_enum = Wave(wave)
        subject_template, body_template = self._store.get(
            classification.segment, angle.angle_key, wave_enum
        )
        subject = self._render(subject_template, prospect)
        body = self._render(body_template, prospect)
        return Draft(
            prospect_id=prospect.id,
            email=prospect.email,
            wave=wave_enum,
            segment=classification.segment,
            angle_key=angle.angle_key,
            subject=subject,
            body=body,
        )

    @staticmethod
    def _render(template: str, prospect: Prospect) -> str:
        """Replace the two supported placeholders; no other tokens are touched."""
        return template.replace("{shop_name}", prospect.name).replace("{city}", prospect.city)
