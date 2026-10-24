# Duchaki Parking Radar

**Live two-wheeler parking vacancy for Pune — without a single sensor — plus a rate-truth layer that catches contractors charging above the official PMC tariff.**

PMC runs just 31 paid parking lots, almost all overburdened, and 63% of parked vehicles in Pune are two-wheelers. Riders circle FC Road and JM Road for 10–15 minutes, park on footpaths, or get fleeced at the lot — and people quote avoiding the Metro itself because there's nowhere to park at the station. Google Maps shows lot *locations*, never vacancy or the real tariff. Park+ is car-centric; the monthly-parking apps don't cover PMC lots or informal two-wheeler bays at all.

## The two features

### 1. Vacancy without sensors
No hardware, no PMC contract. Two cheap signals, fused:
- **Attendant QR panel** — the lot attendant taps "space freed / lot full" (or enters a count) on a printed QR panel. One tap, no app install for them.
- **Rider pings** — "I just left a spot" / "I just parked" from riders at the lot.

A deterministic estimator turns the last attendant report + net rider pings into a spaces-left estimate **with an honest confidence level** — and it publishes an early estimate from partial data immediately, refining as pings arrive, instead of waiting for certainty that never comes.

### 2. Rate-card truth layer
Every lot card shows the **official PMC tariff**. After parking, photograph the contractor's slip: the app extracts the charged amount, compares it against the official rate for your duration, and if you were overcharged, **drafts the PMC complaint for you** with the slip as evidence.

## How it fits the bigger picture

Same engineering discipline as our other builds (see `ARCHITECTURE.md`):
deterministic core (estimation and rate math in code, never in an LLM),
tiered data (curated dataset first, crowd pings second, web data last and
flagged), and models behind interfaces (a vision model reads slips;
complaint drafting is templated). Five current research findings are
mapped onto this design in `ARCHITECTURE.md` — Raw-RAG for the tariff/
complaint evidence store, streaming estimation from DiffResearch,
OpenDS-World's warning against live-web dependence, and a Phase-2
Self-HPO tuning loop for the estimator.

## Project structure

```
duchaki-parking-radar/
├── README.md                  ← you are here
├── ARCHITECTURE.md            ← design + research mapping + improvements
├── main.py                    ← demo: vacancy estimate + slip check
├── requirements.txt
├── src/parking_radar/
│   ├── models.py              ← Lot, PingEvent, VacancyEstimate, SlipCheck
│   ├── estimator.py           ← deterministic vacancy estimator
│   ├── rates.py               ← official-rate lookup + overcharge check
│   ├── complaints.py          ← PMC complaint draft generator
│   └── data/
│       ├── lots.json          ← THE finite demo dataset (12 Pune locations)
│       ├── sample_pings.json  ← demo vacancy events
│       └── sample_slips.json  ← demo contractor slips
└── tests/                     ← estimator rules, rate checks, complaints
```

## The demo dataset

`src/parking_radar/data/lots.json` is a **finite, demo-sized dataset**:
12 well-known Pune parking locations (FC Road, JM Road, MG Road, Pune
Station, Swargate, Kothrud, Aundh, Baner, Hinjawadi, Viman Nagar,
Koregaon Park, Laxmi Road) with capacities and tariff fields.
**Rates and capacities are sample values for the demo** — before any
real launch they get replaced by a ground survey of PMC's actual 31
lots and the official tariff circular. The dataset schema is the real
deliverable; swapping the values changes nothing in the code.

## Run the demo

```bash
pip install -r requirements.txt
python main.py     # vacancy estimate for FC Road + an overcharge catch
pytest             # tests
```

## Run the web server

```bash
uvicorn server:server --port 8002
# Rider view:  http://localhost:8002        (every lot, live estimates)
# Attendant panel: http://localhost:8002/panel/fc-road-01
# API: /api/lots, /api/lots/{id}, POST /api/ping, POST /api/slip-check
```

## Status

Scaffold: models, working estimator, rate-truth layer, complaint
generator, demo dataset, tests. Pilot scope (from the research): the
31 PMC lots are a fixed, surveyable list — Deccan/FC Road first.
