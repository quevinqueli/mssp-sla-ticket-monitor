# Ticket CSV schema (v1)

All demo files are **synthetic**. Do not treat customer ids or summaries as real orgs.

## Columns

| Column | Required | Format | Meaning |
| --- | --- | --- | --- |
| `ticket_id` | yes | non-empty string | Stable ticket identifier |
| `created_at` | yes | timezone-aware ISO-8601 | Clock start for response and resolve SLAs |
| `priority` | yes | see catalog | Selects response/resolve hours |
| `status` | yes | see catalog | Open vs closed; waiting_customer does **not** pause SLA |
| `first_response_at` | no | timezone-aware ISO-8601 or empty | Stops the response clock |
| `resolved_at` | no | timezone-aware ISO-8601 or empty | Stops the resolve clock |
| `status_updated_at` | no | timezone-aware ISO-8601 or empty | Required to measure waiting_customer dwell time |
| `customer_id` | no | string | Copied into evidence; never enriched |
| `assigned_to` | no | string | Empty + open → attention (unassigned) |
| `ticket_type` | no | string | Informational only |
| `category` | no | string | Informational only |
| `summary` | no | string | Informational only; not interpreted as impact |

Naive timestamps (no offset) are **ambiguous** and flagged. The parser never assumes UTC.

## Priority catalog (only these map to an SLA)

| Normalized | Accepted aliases | First response | Resolve |
| --- | --- | --- | --- |
| P1 | `P1`, `Critical`, `Crit`, `1` | 15 minutes (0.25h) | 4 hours |
| P2 | `P2`, `High`, `2` | 1 hour | 8 hours |
| P3 | `P3`, `Medium`, `Med`, `3` | 4 hours | 24 hours |
| P4 | `P4`, `Low`, `4` | 8 hours | 72 hours |

Anything else (`Urgent`, `P0`, `Sev1`, blank, …) is `DQ-UNKNOWN-PRIORITY`. **Not guessed.**

## Status catalog

- Open (clock may still tick): `open`, `in_progress`, `waiting_customer`, `pending`, `investigating`
- Closed (resolve clock stops only when `resolved_at` is present): `resolved`, `closed`

Any other status is `DQ-UNKNOWN-STATUS`. **Not guessed.**

## Documented gaps and ambiguous cases

The synthetic files include these on purpose:

1. **Unknown priority** (`Urgent`) — no SLA hours applied.
2. **Missing `created_at`** — clocks cannot start.
3. **Unparseable / naive timestamp** — flagged; field treated as absent.
4. **`resolved`/`closed` without `resolved_at`** — resolve SLA skipped (would be guessing the stop time).
5. **`waiting_customer` without `status_updated_at`** — wait-time attention skipped (would be guessing dwell from `created_at`).
6. **`first_response_at` or `resolved_at` before `created_at`**, or `resolved_at` before `first_response_at` — timeline inconsistent; affected clocks skipped.
7. **Duplicate `ticket_id`** — both rows flagged; SLA skipped (canonical row is not guessed).
8. **Missing `ticket_id`** — labeled `ROW-{n}` for traceability only.
9. **`waiting_customer` still accrues resolve SLA** — v1 does not pause clocks. The brief says so on those findings.

## Clock rules (v1)

- Response: start `created_at`, stop `first_response_at` or `as_of` if unanswered.
- Resolve: start `created_at`, stop `resolved_at` or `as_of` if still open.
- Approaching: still ticking, not yet breached, remaining hours inside the warn band in `sla_rules.py`.
- Ageing backlog: still open and age ≥ 48 hours, independent of priority SLA.
