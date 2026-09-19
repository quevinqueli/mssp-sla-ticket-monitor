# MSSP SLA ticket monitor

Turn a support-ticket CSV into a **daily operational brief**: breached SLAs, approaching deadlines, ageing backlog, and tickets that need attention. Every finding carries evidence (ticket id, timestamps, rule id, computed deadline/age, and why it qualifies).

This repo is a v1 greenfield implementation. Phase A is deterministic and does not call a model. Phase B is optional and may run only after verification passes.

## Setup

Python 3.11+ recommended (developed on 3.12).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` pins **pytest only**. The brief itself uses the Python standard library (`csv`, `json`, `argparse`, `urllib`).

## One-command demo (no API key)

From the repo root:

```bash
python3 scripts/run_demo.py
```

Equivalent:

```bash
python3 -m mssp_sla \
  --csv data/synthetic_tickets.csv \
  --as-of "$(cat data/DEMO_AS_OF.txt)" \
  --out artifacts
```

This writes:

- `artifacts/metrics.json` — counts + every finding with evidence
- `artifacts/daily_brief.md` — markdown brief rendered from those verified numbers

The demo CSV is synthetic. The frozen `as_of` instant is `2026-09-19T12:00:00Z` so the sample brief is reproducible.

## Tests

```bash
pytest
```

`tests/fixtures/hand_checked_tickets.csv` plus `tests/fixtures/hand_checked_expected.json` are a **hand-checked** pair. The expected numbers were computed from the SLA catalog and the fixture timestamps; the tests require the code to match them (they are not generated from program output).

## SLA rules (catalog v1)

Documented in code (`mssp_sla/sla_rules.py`) and in `data/SCHEMA.md`.

| Priority | Aliases | First response | Resolve |
| --- | --- | --- | --- |
| P1 | Critical, Crit, 1 | 15 minutes | 4 hours |
| P2 | High, 2 | 1 hour | 8 hours |
| P3 | Medium, Med, 3 | 4 hours | 24 hours |
| P4 | Low, 4 | 8 hours | 72 hours |

Anything else (`Urgent`, `P5`, `Sev1`, blank, …) is flagged as unknown. **It is never mapped by guesswork.**

Clock rules:

- Response starts at `created_at` and stops at `first_response_at`, or at `as_of` if still unanswered.
- Resolve starts at `created_at` and stops at `resolved_at`, or at `as_of` if the ticket is still open.
- `waiting_customer` does **not** pause the resolve clock in v1. Findings say so.
- Approaching: still ticking, not yet breached, and remaining time is in the last 50% of a ≤1h window, or otherwise in `min(2h, 25% of the window)`.
- Ageing backlog: still open and age ≥ 48 hours, independent of priority SLA.

Missing required fields and inconsistent timelines are flagged. Those rows are excluded from the clocks that need the missing/invalid value.

## Verification before AI

Phase A always:

1. Parses the CSV and flags gaps (never fills them in).
2. Computes findings with evidence.
3. Re-checks itself: evidence fields present, rule ids in the catalog, list lengths match counts, SLA deadlines and overdue hours recompute from `created_at` + catalog hours.

Phase B (`--ai`) is opt-in:

- If verification **fails**, the brief ships **without** an AI section (failed-verification banner). No model call.
- If verification **passes** but `MSSP_SLA_AI_API_KEY` / `OPENAI_API_KEY` is unset, the brief still ships; the AI section says it was omitted.
- If a model is called, it receives **only** the verified metrics JSON (not raw tickets as a free-form source of truth). Output must cite Phase A `evidence_id` values. Invented ticket ids, evidence ids, or ungrounded metrics cause the AI section to be withheld.

```bash
# Optional; does nothing useful without an API key
python3 -m mssp_sla --csv data/synthetic_tickets.csv --as-of 2026-09-19T12:00:00Z --out artifacts --ai
```

## Layout

```
mssp_sla/          Phase A compute + verification + optional Phase B
data/              Schema docs + synthetic demo CSV
tests/             Unit tests + hand-checked fixtures
scripts/run_demo.py
artifacts/         Demo output (metrics JSON + markdown brief)
```

## What this tool will not do

- Invent metrics, deadlines, customer facts, or business outcomes.
- Treat `Urgent` as P1.
- Assume UTC for timestamps that omit a timezone.
- Pause SLA for customer-wait unless a future catalog says so (v1 does not).
