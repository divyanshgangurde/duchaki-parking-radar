"""Duchaki Parking Radar demo — sample dataset, fixed clock, no network.

    python main.py

Scene: Saturday 18:30, FC Road. The attendant reported 14 two-wheeler
spaces at 18:10; since then 3 riders parked and 1 left. JM Road's
attendant flagged FULL at 18:05. Then: two contractor slips get checked
against the official tariff — one is a ₹20 overcharge.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from parking_radar.complaints import draft_complaint
from parking_radar.estimator import estimate_vacancy
from parking_radar.models import Lot, PingEvent
from parking_radar.rates import check_slip

DATA = Path(__file__).parent / "src" / "parking_radar" / "data"
NOW = "2026-10-24T18:30:00"


def main() -> None:
    lots = {row["id"]: Lot(**row) for row in json.loads((DATA / "lots.json").read_text())}
    pings = [PingEvent(**row) for row in json.loads((DATA / "sample_pings.json").read_text())]

    print("=== Vacancy, Sat 18:30 ===")
    for lot_id in ("fc-road-01", "jm-road-01"):
        lot = lots[lot_id]
        est = estimate_vacancy(lot, pings, NOW)
        print(f"{lot.name}: ~{est.spaces_left_2w} two-wheeler spaces "
              f"(confidence: {est.confidence}, freshest signal {est.signal_age_min} min old)")
        print(f"   basis: {est.basis}")

    print("\n=== Slip checks ===")
    for slip in json.loads((DATA / "sample_slips.json").read_text()):
        lot = lots[slip["lot_id"]]
        check = check_slip(lot, slip["hours"], slip["charged_inr"], slip["vehicle"])
        print(f"{lot.name}: charged ₹{check.charged_inr} for {check.hours:g}h, "
              f"official ₹{check.official_inr} → {check.verdict}"
              + (f" (overcharged ₹{check.overcharged_inr})" if check.overcharged_inr else ""))
        if check.verdict == "OVERCHARGED":
            print("\n--- Complaint draft ---")
            print(draft_complaint(lot, check, "24 Oct 2026"))


if __name__ == "__main__":
    main()
