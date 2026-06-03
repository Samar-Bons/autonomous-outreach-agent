# ABOUTME: The angle catalog and the archetype -> candidate-angle shortlists.
# ABOUTME: Constraining angle choice to a per-archetype shortlist makes mismatches structural.
from __future__ import annotations

from ..domain.enums import Archetype, Segment

# The angles available per segment. An "angle" is a named value proposition that
# maps to one body + subject template downstream.
SEGMENT_ANGLES: dict[Segment, tuple[str, ...]] = {
    Segment.PASSENGER_LUBE: (
        "next_day_delivery",
        "net_30_terms",
        "bulk_supply",
        "full_viscosity_range",
        "specialty_euro",
        "local_proximity",
    ),
    Segment.HD_DIESEL: (
        "def_in_stock",
        "ci4_older_engines",
        "fleet_one_stop",
        "bulk_supply",
        "next_day_delivery",
    ),
    Segment.DEALER_FLEET: (
        "oem_spec_match",
        "volume_pricing",
        "net_30_terms",
        "next_day_delivery",
    ),
    Segment.OUT_OF_SCOPE: (),
}

# Each archetype maps to a shortlist of candidate angles. The picker intersects
# this with the segment's available angles. An empty intersection drops the
# prospect rather than guessing an angle.
# Illustrative routing for this reference build. The real archetype-to-angle
# shortlists are tuned per business and are not part of the public repo.
ARCHETYPE_SHORTLISTS: dict[Archetype, tuple[str, ...]] = {
    Archetype.EURO_SPECIALIST: ("specialty_euro", "full_viscosity_range", "oem_spec_match"),
    Archetype.HYBRID_SPECIALIST: ("full_viscosity_range", "specialty_euro", "next_day_delivery"),
    Archetype.LUBE_CHAIN: ("bulk_supply", "next_day_delivery", "volume_pricing"),
    Archetype.TRANSMISSION_SPECIALIST: ("full_viscosity_range", "next_day_delivery"),
    Archetype.BODY_SHOP: ("next_day_delivery", "local_proximity"),
    Archetype.HD_DIESEL: ("def_in_stock", "ci4_older_engines", "fleet_one_stop", "bulk_supply"),
    Archetype.INDEPENDENT_GENERAL: ("next_day_delivery", "net_30_terms", "full_viscosity_range"),
    # Quarantine archetypes intentionally have no candidate angles.
    Archetype.MOBILE_MECHANIC: (),
    Archetype.OUT_OF_SCOPE: (),
    Archetype.UNCLEAR: (),
    Archetype.NEEDS_RETRY: (),
}


def candidate_angles(segment: Segment, archetype: Archetype) -> tuple[str, ...]:
    """Angles allowed for this prospect: the archetype shortlist, in segment order.

    Ordering follows the segment's angle tuple so the result is deterministic and
    the "first candidate" fallback is stable.
    """
    shortlist = set(ARCHETYPE_SHORTLISTS.get(archetype, ()))
    available = SEGMENT_ANGLES.get(segment, ())
    return tuple(angle for angle in available if angle in shortlist)
