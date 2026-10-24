"""Deterministic vacancy estimator (ARCHITECTURE.md §2).

Rules:
  * Base = the most recent attendant report (count, or full → 0).
  * Rider pings after the base adjust it: left +1, parked −1,
    clamped to [0, capacity]. A single ping never moves it more.
  * No attendant report yet → fall back to rider pings against a
    full-lot assumption and mark confidence low.
  * Confidence from the age of the freshest signal used:
    ≤15 min high, ≤45 min medium, else low.
"""

from __future__ import annotations

from datetime import datetime

from .models import Lot, PingEvent, VacancyEstimate


def _mins(later: str, earlier: str) -> int:
    fmt = "%Y-%m-%dT%H:%M:%S"
    return int((datetime.strptime(later, fmt) - datetime.strptime(earlier, fmt)).total_seconds() // 60)


def estimate_vacancy(lot: Lot, events: list[PingEvent], now: str) -> VacancyEstimate:
    # Future-dated events (e.g. stale demo data) never count as signals.
    ev = sorted([e for e in events if e.lot_id == lot.id and e.ts <= now], key=lambda e: e.ts)
    attendant = [e for e in ev if e.kind in ("attendant_count", "attendant_full")]
    if attendant:
        base_event = attendant[-1]
        base = 0 if base_event.kind == "attendant_full" else (base_event.value or 0)
        base_ts = base_event.ts
        basis = f"attendant report at {base_ts[11:16]}"
    else:
        base = lot.capacity_2w
        base_ts = ev[0].ts if ev else now
        basis = "no attendant report yet — rider pings only"

    spaces = base
    used = [e for e in ev if e.ts >= base_ts] if attendant else ev
    freshest = base_ts
    for e in used:
        if e.kind == "left":
            spaces += 1
        elif e.kind == "parked":
            spaces -= 1
        elif e.kind == "attendant_full" and e is not (attendant[-1] if attendant else None):
            spaces = 0
        freshest = max(freshest, e.ts)
    spaces = max(0, min(lot.capacity_2w, spaces))

    age = _mins(now, freshest)
    confidence = "high" if age <= 15 else "medium" if age <= 45 else "low"
    if not attendant:
        confidence = "low"
    return VacancyEstimate(lot_id=lot.id, spaces_left_2w=spaces,
                           confidence=confidence, signal_age_min=age,
                           basis=f"{basis}; {len(used)} signal(s) applied")
