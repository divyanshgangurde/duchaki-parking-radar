import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from server import lots, server

client = TestClient(server)


def test_lots_endpoint_lists_all():
    r = client.get("/api/lots")
    assert r.status_code == 200
    assert len(r.json()) == len(lots)
    assert "spaces_left_2w" in r.json()["fc-road-01"]


def test_ping_moves_estimate():
    # mg-road-01 has no sample pings, so this test is clock-independent:
    # set a fresh attendant baseline, then a "left" ping must add one space.
    client.post("/api/ping", json={"lot_id": "mg-road-01", "kind": "attendant_count", "value": 10})
    before = client.get("/api/lots/mg-road-01").json()["spaces_left_2w"]
    assert before == 10
    client.post("/api/ping", json={"lot_id": "mg-road-01", "kind": "left"})
    after = client.get("/api/lots/mg-road-01").json()["spaces_left_2w"]
    assert after == before + 1


def test_slip_check_with_draft():
    r = client.post("/api/slip-check",
                    json={"lot_id": "fc-road-01", "hours": 1, "charged_inr": 40})
    body = r.json()
    assert body["verdict"] == "OVERCHARGED" and body["overcharged_inr"] == 20
    assert "Pune Municipal Corporation" in body["complaint_draft"]


def test_rider_view_and_panel_render():
    assert client.get("/").status_code == 200
    assert client.get("/panel/fc-road-01").status_code == 200
    assert client.get("/api/lots/nope").status_code == 404
