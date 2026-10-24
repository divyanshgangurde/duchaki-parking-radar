"""Data models for Duchaki Parking Radar.

Every vacancy number the system shows is a VacancyEstimate — a value
WITH a confidence level and the age of its freshest signal. There is
no bare "spaces left" integer anywhere in this design.
"""

from __future__ import annotations

from pydantic import BaseModel


class Lot(BaseModel):
    id: str
    name: str
    area: str
    kind: str  # pmc_lot | street_bay
    capacity_2w: int
    capacity_4w: int = 0
    rate_2w_per_hour_inr: int  # official tariff (sample values in demo data)
    rate_4w_per_hour_inr: int = 0
    hours: str = "06:00-23:00"
    source: str = "sample-demo"  # production: surveyed + PMC circular ref


class PingEvent(BaseModel):
    lot_id: str
    ts: str  # ISO datetime
    kind: str  # attendant_count | attendant_full | left | parked
    value: int | None = None  # spaces-left count for attendant_count


class VacancyEstimate(BaseModel):
    lot_id: str
    spaces_left_2w: int
    confidence: str  # high | medium | low
    signal_age_min: int  # age of the freshest signal used
    basis: str  # human-readable: how this estimate was produced


class SlipCheck(BaseModel):
    lot_id: str
    hours: float
    charged_inr: int
    official_inr: int
    overcharged_inr: int  # 0 when the slip is fair
    verdict: str  # FAIR | OVERCHARGED
