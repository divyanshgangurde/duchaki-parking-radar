import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parking_radar.estimator import estimate_vacancy
from parking_radar.models import Lot, PingEvent

LOT = Lot(id="t-01", name="Test Lot", area="FC Road", kind="pmc_lot",
          capacity_2w=100, rate_2w_per_hour_inr=20)


def ev(kind, ts, value=None):
    return PingEvent(lot_id="t-01", ts=ts, kind=kind, value=value)


def test_attendant_base_plus_pings():
    events = [ev("attendant_count", "2026-10-24T18:10:00", 14),
              ev("parked", "2026-10-24T18:14:00"),
              ev("parked", "2026-10-24T18:19:00"),
              ev("left", "2026-10-24T18:26:00")]
    est = estimate_vacancy(LOT, events, "2026-10-24T18:30:00")
    assert est.spaces_left_2w == 13  # 14 - 2 parked + 1 left
    assert est.confidence == "high"  # freshest signal 4 min old


def test_full_flag_pins_zero():
    est = estimate_vacancy(LOT, [ev("attendant_full", "2026-10-24T18:05:00")],
                           "2026-10-24T18:30:00")
    assert est.spaces_left_2w == 0
    assert est.confidence == "medium"  # 25 min old


def test_estimate_never_exceeds_capacity():
    events = [ev("attendant_count", "2026-10-24T18:00:00", 98)] + \
             [ev("left", f"2026-10-24T18:0{i}:30") for i in range(1, 6)]
    est = estimate_vacancy(LOT, events, "2026-10-24T18:10:00")
    assert est.spaces_left_2w == 100


def test_stale_signal_is_low_confidence():
    est = estimate_vacancy(LOT, [ev("attendant_count", "2026-10-24T15:00:00", 40)],
                           "2026-10-24T18:30:00")
    assert est.confidence == "low"
