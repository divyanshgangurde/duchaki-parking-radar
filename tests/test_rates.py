import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parking_radar.complaints import draft_complaint
from parking_radar.models import Lot
from parking_radar.rates import check_slip

LOT = Lot(id="fc-road-01", name="FC Road PMC Parking Lot", area="Fergusson College Road",
          kind="pmc_lot", capacity_2w=120, rate_2w_per_hour_inr=20)


def test_overcharge_detected():
    c = check_slip(LOT, hours=1, charged_inr=40)
    assert c.verdict == "OVERCHARGED" and c.official_inr == 20 and c.overcharged_inr == 20


def test_fair_slip_passes():
    c = check_slip(LOT, hours=2, charged_inr=40)
    assert c.verdict == "FAIR" and c.overcharged_inr == 0


def test_complaint_quotes_the_numbers():
    c = check_slip(LOT, hours=1, charged_inr=40)
    text = draft_complaint(LOT, c, "24 Oct 2026")
    assert "FC Road PMC Parking Lot" in text and "₹20" in text and "₹40" in text


def test_no_complaint_for_fair_slip():
    c = check_slip(LOT, hours=2, charged_inr=40)
    assert draft_complaint(LOT, c, "24 Oct 2026").startswith("No complaint needed")
