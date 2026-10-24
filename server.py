"""Duchaki Parking Radar server — rider view, attendant panel, ping API.

    pip install -r requirements.txt
    uvicorn server:server --port 8002

State is in-memory, seeded from the sample dataset: fine for a demo and
for the pilot. A production build swaps the store for a database and
adds per-lot panel tokens (see ARCHITECTURE.md §4 anti-spam notes).

  GET  /                 rider view: every lot's estimate + confidence
  GET  /api/lots         JSON estimates for all lots
  GET  /api/lots/{id}    JSON estimate for one lot
  POST /api/ping         {"lot_id", "kind", "value?"} → new estimate
                         kinds: attendant_count, attendant_full, left, parked
  GET  /panel/{lot_id}   attendant panel: count / full / freed buttons
  POST /api/slip-check   {"lot_id", "hours", "charged_inr"} → verdict + draft
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent / "src"))

from parking_radar.complaints import draft_complaint
from parking_radar.estimator import estimate_vacancy
from parking_radar.models import Lot, PingEvent
from parking_radar.rates import check_slip

DATA = Path(__file__).parent / "src" / "parking_radar" / "data"
lots: dict[str, Lot] = {r["id"]: Lot(**r) for r in json.loads((DATA / "lots.json").read_text())}
_raw_pings = [PingEvent(**r) for r in json.loads((DATA / "sample_pings.json").read_text())]


def _seed_pings() -> list[PingEvent]:
    """Shift the sample ping log so its latest event is 4 minutes ago —
    the demo stays lively at any hour instead of depending on a fixed
    evening clock. Production replaces this with the live ping store."""
    from datetime import datetime, timedelta
    fmt = "%Y-%m-%dT%H:%M:%S"
    latest = max(datetime.strptime(p.ts, fmt) for p in _raw_pings)
    shift = datetime.now() - timedelta(minutes=4) - latest
    return [PingEvent(lot_id=p.lot_id,
                      ts=(datetime.strptime(p.ts, fmt) + shift).strftime(fmt),
                      kind=p.kind, value=p.value) for p in _raw_pings]


pings: list[PingEvent] = _seed_pings()

server = FastAPI(title="Duchaki Parking Radar")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _estimate(lot_id: str, now: str | None = None):
    lot = lots.get(lot_id)
    if not lot:
        raise HTTPException(404, "unknown lot")
    return estimate_vacancy(lot, pings, now or _now())


class PingIn(BaseModel):
    lot_id: str
    kind: str  # attendant_count | attendant_full | left | parked
    value: int | None = None


class SlipIn(BaseModel):
    lot_id: str
    hours: float
    charged_inr: int
    vehicle: str = "2w"


@server.get("/", response_class=HTMLResponse)
def rider_view():
    rows = ""
    for lot in lots.values():
        est = _estimate(lot.id)
        rows += (f"<tr><td>{lot.name} ({lot.area})</td>"
                 f"<td>~{est.spaces_left_2w} spaces</td>"
                 f"<td>{est.confidence} ({est.signal_age_min} min old)</td>"
                 f"<td>₹{lot.rate_2w_per_hour_inr}/hr official</td></tr>")
    return f"<h1>Duchaki Parking Radar</h1><table border=1><tr><th>Lot</th><th>Two-wheeler spaces</th><th>Confidence</th><th>Official rate</th></tr>{rows}</table>"


@server.get("/api/lots")
def all_lots():
    return {lot_id: _estimate(lot_id).model_dump() for lot_id in lots}


@server.get("/api/lots/{lot_id}")
def one_lot(lot_id: str):
    return _estimate(lot_id).model_dump()


@server.post("/api/ping")
def add_ping(body: PingIn):
    if body.lot_id not in lots:
        raise HTTPException(404, "unknown lot")
    if body.kind not in ("attendant_count", "attendant_full", "left", "parked"):
        raise HTTPException(400, "bad ping kind")
    pings.append(PingEvent(lot_id=body.lot_id, ts=_now(), kind=body.kind, value=body.value))
    return _estimate(body.lot_id).model_dump()


@server.get("/panel/{lot_id}", response_class=HTMLResponse)
def panel(lot_id: str):
    lot = lots.get(lot_id)
    if not lot:
        raise HTTPException(404, "unknown lot")
    est = _estimate(lot_id)
    return f"""<h1>Attendant panel — {lot.name}</h1>
<p>Current estimate: ~{est.spaces_left_2w} spaces ({est.confidence})</p>
<form action="/panel-action" method="post">
<input type="hidden" name="lot_id" value="{lot_id}">
<button type="submit" name="kind" value="left">Space freed</button>
<button type="submit" name="kind" value="attendant_full">Lot FULL</button>
</form>
<form action="/panel-action" method="post">
<input type="hidden" name="lot_id" value="{lot_id}">
<input type="hidden" name="kind" value="attendant_count">
Spaces left now: <input name="value" type="number" min="0" max="{lot.capacity_2w}">
<button type="submit">Update count</button></form>
<p>Tip: bookmark this page on the lot's phone. No login needed.</p>"""


@server.post("/panel-action", response_class=HTMLResponse)
def panel_action(lot_id: str = Form(...), kind: str = Form(...),
                 value: str | None = Form(None)):
    from fastapi.responses import RedirectResponse
    count = int(value) if value not in (None, "") else None
    if lot_id in lots and kind in ("attendant_count", "attendant_full", "left", "parked"):
        pings.append(PingEvent(lot_id=lot_id, ts=_now(), kind=kind, value=count))
    return RedirectResponse(f"/panel/{lot_id}", status_code=303)


@server.post("/api/slip-check")
def slip_check(body: SlipIn):
    lot = lots.get(body.lot_id)
    if not lot:
        raise HTTPException(404, "unknown lot")
    check = check_slip(lot, body.hours, body.charged_inr, body.vehicle)
    out = check.model_dump()
    if check.verdict == "OVERCHARGED":
        out["complaint_draft"] = draft_complaint(lot, check, datetime.now().strftime("%d %b %Y"))
    return out
