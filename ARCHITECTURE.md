# Duchaki Parking Radar — Architecture

Inputs: the Pune-problems research (Round 2, Oct 2026) + the five
research-radar findings, mapped in §3 with honest fit assessments.
Core loop: attendants and riders produce pings → a deterministic
estimator publishes vacancy with confidence → the rate layer checks
slips against official tariffs → complaints are drafted from evidence.

## 1. Shape

```
  Attendant QR panel ──┐
  (count / full / freed)│
                        ├──► PING INGEST ──► ESTIMATOR (code) ──► vacancy + confidence
  Rider app pings ─────┘        │                  │
  (left / parked)               │                  └──► estimate log (for §3.5 tuning)
                                │
  Lot dataset (curated) ────────┴──► RATE LAYER (code): official tariff per lot
                                │
  Slip photo ──► VISION READER (model, behind interface) ──► charged amount
                                │
                                └──► COMPLAINT GENERATOR (templates + Raw-RAG evidence)
```

Clients: a thin mobile web app (riders) + a printable QR panel per lot
(attendants — no install, no login; the panel URL carries the lot id and
a rotating token so randoms can't spam counts).

## 2. The estimator (deterministic core)

- State per lot = last attendant report (spaces-left count + timestamp).
- Rider pings after that report adjust it: `left` +1, `parked` −1,
  clamped to [0, capacity].
- Confidence is a function of report age and ping volume: attendant
  report ≤15 min old → high; ≤45 min → medium; older → low, and the UI
  shows the age ("attendant reported 32 min ago") instead of hiding it.
- A `full` flag from either source pins the estimate to 0 until a
  `left`/attendant update arrives.
- **Why code, not ML:** the inputs are tiny, the rule is auditable, and a
  wrong-but-confident ML number is worse than an honest range. Estimation
  quality is improved by better signals (more attendants), not a bigger
  model — see the Phase-2 loop (§3.5) for the one place learning enters.

## 3. How the five radar findings fit

### 3.1 Raw-RAG — the evidence store (used directly)
PMC tariff circulars, past slips and past complaints are stored RAW and
retrieved by the complaint generator and the rate layer ("what is the
official rate at JM Road lot, per which circular?"). Justification: the
paper shows raw retrieval beats transformed memory stores — and here the
exact wording of a circular *is* the evidence in a complaint. A summary
that paraphrases the tariff away would be useless at the PMC office.

### 3.2 DiffResearch / dFast — streaming estimates (the trick, stolen)
dFast extracts sub-queries before generation finishes; our equivalent:
the estimator publishes an estimate the moment ANY signal exists (even
one attendant tap) and refines it as pings stream in, always showing
confidence. Justification: a rider deciding *now* needs "≈12 spaces,
low confidence" immediately, not a perfect number in 10 minutes. A
parking answer has a shelf life of minutes.

### 3.3 OpenDS-World — no live-web dependence (design constraint)
Best frontier model: 39% on live-web multi-step tasks. So nothing core
depends on scraping PMC pages or Google for lot data. Tiers: (1) the
curated lot dataset, (2) attendant/rider pings, (3) web-sourced updates
accepted only as *suggestions* into the dataset, human-verified, flagged
until confirmed. Justification: vacancy and tariff data presented as
fact must come from sources we control.

### 3.4 Kimi K3.1 Pro — the slip reader (behind an interface)
The slip photo is read by a vision model: extract lot, duration, amount
charged, in whatever mix of English/Marathi the slip uses. K3.1 Pro is
the default candidate (multimodal, cheap at $2/$10 per M tokens).
Justification for the interface, not blind trust: its benchmark claims
are vendor-reported, and slip extraction is a narrow job a smaller VLM
may do as well — the rate comparison after extraction is code, so a
misread shows up as a wrong amount the *user confirms* before any
complaint is generated. The model proposes; the human and the code
dispose.

### 3.5 Self-HPO — Phase-2 estimator tuning (deferred, deliberately)
Every estimate is logged with its inputs; when a rider reaches a lot,
one tap reports ground truth ("was the estimate right?"). That log is
the failure set for a tuning loop: alternate estimator-parameter
adjustments (ping weights, decay windows, per-lot attendant trust)
with signal changes (panel placement, prompt wording), gated on
estimate accuracy. Justification: Self-HPO shows harness and policy
gains compound — but the loop needs a live system producing failures.
MVP first.

## 4. Software improvements over a naive build

- **Confidence as a first-class output.** Every estimate carries level +
  signal age; the UI is designed around showing uncertainty, not hiding
  it. Most parking apps fake precision; ours is honest by construction.
- **Anti-spam by design:** attendant panels use rotating tokens; rider
  pings are geo-fenced to the lot and rate-limited per device; a single
  ping can never move an estimate by more than ±1.
- **Complaint evidence pack:** slip photo + official tariff (with the
  circular reference from the Raw-RAG store) + generated draft in one
  PDF — the artefact a PMC complaint actually needs.
- **Offline-first dataset:** the lot dataset ships inside the app;
  vacancy needs network, but rates, lot info and complaint drafting
  work offline — built for basement parking and patchy signals.
- **Golden-scenario evals:** fixed ping sequences with known-correct
  estimates (decay, clamping, full-flag, overcharge math) run in CI —
  the estimator can't silently regress when someone "improves" it.

## 5. The finite demo dataset

`src/parking_radar/data/lots.json` — 12 locations, schema:
`{id, name, area, kind (pmc_lot | street_bay), capacity_2w, capacity_4w,
rate_2w_per_hour_inr, rate_4w_per_hour_inr, hours, source}`.
Values are sample data for the demo (source: "sample-demo"); the
production step is a ground survey of PMC's 31 lots + the official
tariff circular, dropped into the same schema. Sample pings and slips
in the same folder drive the demo end-to-end with no network.

## 6. MVP scope

Dataset + estimator + attendant panel (web page) + rider view (mobile
web) + slip check with complaint draft. Pilot: Deccan / FC Road lots.
Not in MVP: payments, reservations, car routing, ML estimation.
