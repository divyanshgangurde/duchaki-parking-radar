"""PMC complaint draft generator — templated, evidence-first.

In production the draft attaches the slip photo and the tariff circular
reference retrieved from the Raw-RAG evidence store (ARCHITECTURE.md
§3.1). The user reviews everything before anything is submitted.
"""

from __future__ import annotations

from .models import Lot, SlipCheck


def draft_complaint(lot: Lot, check: SlipCheck, date: str) -> str:
    if check.verdict != "OVERCHARGED":
        return "No complaint needed — the slip matches the official tariff."
    return (
        f"To: The Commissioner, Pune Municipal Corporation\n"
        f"Subject: Overcharging at PMC parking — {lot.name} ({lot.area})\n\n"
        f"On {date} I parked a two-wheeler at {lot.name}, {lot.area} for "
        f"{check.hours:g} hour(s). The official PMC tariff for this lot is "
        f"₹{lot.rate_2w_per_hour_inr} per hour, so the payable amount was "
        f"₹{check.official_inr}. I was charged ₹{check.charged_inr} — an "
        f"overcharge of ₹{check.overcharged_inr}.\n\n"
        f"The contractor's slip is attached as evidence. I request a refund "
        f"of ₹{check.overcharged_inr} and action against the contractor as "
        f"per the parking contract terms.\n\n"
        f"— Drafted by Duchaki Parking Radar (review before submitting)"
    )
