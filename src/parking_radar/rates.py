"""Rate-truth layer: official tariff vs what the slip says (code only)."""

from __future__ import annotations

from .models import Lot, SlipCheck


def check_slip(lot: Lot, hours: float, charged_inr: int, vehicle: str = "2w") -> SlipCheck:
    rate = lot.rate_2w_per_hour_inr if vehicle == "2w" else lot.rate_4w_per_hour_inr
    official = int(rate * hours)
    over = max(0, charged_inr - official)
    return SlipCheck(lot_id=lot.id, hours=hours, charged_inr=charged_inr,
                     official_inr=official, overcharged_inr=over,
                     verdict="OVERCHARGED" if over > 0 else "FAIR")
