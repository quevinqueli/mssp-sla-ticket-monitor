# SLA logic findings (before DAX)

Inspected: `README.md`, `data/SCHEMA.md`, `mssp_sla/sla_rules.py`, `compute.py`, `parse.py`, `pipeline.py`, `verify.py`, `constants.py`, `timeutil.py`, `artifacts/metrics.json`, hand-checked fixtures, and the synthetic CSV.

No Python SLA formula was changed. Where Phase A is explicit, the star schema **matches** it. Where Phase A grain or attention membership is easy to misread, the report documents an intentional delta instead of “fixing” the brief.

## Catalog (matched)

| Priority | Response | Resolve |
| --- | ---: | ---: |
| P1 (Critical, Crit, 1) | 0.25h | 4h |
| P2 (High, 2) | 1h | 8h |
| P3 (Medium, Med, 3) | 4h | 24h |
| P4 (Low, 4) | 8h | 72h |

Anything else (`Urgent`, `P5`, blank, …) is `DQ-UNKNOWN-PRIORITY`. **Never guessed.** Demo `TCK-1007` / `TCK-1024` have no clocks.

- Response start `created_at`; stop `first_response_at` or `as_of` if unanswered.
- Resolve start `created_at`; stop `resolved_at` or `as_of` if still open.
- `waiting_customer` **does not** pause resolve (`TCK-1009`, `TCK-1017`).
- Breach is `stop > deadline` (exact equality is **not** a breach).
- Approaching requires still ticking, not breached, remaining > 0, and remaining ≤ warn band:
  - SLA window ≤ 1h: last 50%
  - otherwise `min(2h, 25% of window)`
- Ageing: still open, `created_at` present, age ≥ 48h, **independent of SLA**.

These match `tests/test_sla_rules.py` and the hand-checked fixture.

## Ambiguities (flagged, not “fixed”)

### 1. `counts.breached_slas` is findings, not tickets

`pipeline.build_report` sets `breached_slas=len(breached)` where `compute_breached_slas` emits **one finding per breached clock**. Demo: 8 findings, 7 tickets, because `TCK-1021` has response **and** resolve breaches.

The attention report question is about tickets. KPI **Breached tickets** = 7. Python-aligned finding count = 8.

### 2. Overlapping ageing and breach

`TCK-1004` is in both `ageing_backlog` and `breached_slas`. Python counts both lists independently. The report ageing KPI **excludes** rows already in the breached KPI so the cards do not double-count. Python-aligned ageing remains 3.

Approaching is already disjoint from the same clock being breached (`is_approaching` is false when remaining ≤ 0). Demo `breach ∩ approaching = ∅`.

### 3. Ageing is not an attention-list rule

`RULE_AGEING_BACKLOG` exists, and the brief has an ageing section, but `compute_attention_list` never appends it. `TCK-1006` is ageing, assigned, on-track for P4 resolve, and **absent** from `attention_list`.

That looks like a product gap relative to the brief’s four headlines, but it is consistent with the explicit attention rule set (open breach, closed P1/P2 breach, approaching P1/P2, unassigned, DQ blocking SLA, waiting ≥ 24h). **Not changed.** The Power BI table still includes ageing-only rows so the Ageing card has supporting tickets.

### 4. Approaching P3/P4 is a finding, not attention

`ATTENTION-APPROACHING-P1P2` is named and implemented as P1/P2 only. `TCK-1010` (P3, 2h remaining on a 24h resolve window — exactly the 2h cap) is in `approaching_deadlines` and **not** in `attention_list`.

The Approaching KPI follows the **finding** list (includes P3), not the attention rule. The table uses the same broader set.

### 5. Duplicate `ticket_id` vs ageing

Duplicates are not SLA-eligible (canonical row is not guessed). Ageing does **not** consult `sla_eligible`. First `TCK-1020` row is 96h open → ageing; second row is 2h open → not ageing. Both rows are on the attention list for `DQ-DUPLICATE-TICKET-ID`. Grain for the model is **CSV row**, matching Python’s `row_count` / `open_tickets`.

### 6. Exact deadline is a hole

`stop == deadline` → `breached=False`, `remaining=0`, `is_approaching(0, sla)=False`. The ticket is neither breached nor approaching. No demo row hits this; DAX inherits it because it uses Python clocks.

### 7. Closed without `resolved_at`

`TCK-1018`: response clock may run; resolve is skipped (`DQ-MISSING-RESOLVED-AT`). Status is closed, so it is not open volume. Matched.

### 8. Closed P1/P2 historical breaches are “attention”

`TCK-1003` (resolve 1h late) and `TCK-1014` (response 0.75h late) are resolved/closed and still on `attention_list`. They inflate the Breached card until Status is filtered to open. Documented; not excluded by default (Python includes them in `breached_slas`).

### 9. Header `open_tickets` vs attention

Python open count includes DQ rows, unknown priority, unassigned, waiting, and both duplicate rows. Matched.

### 10. Verification map last-duplicate-wins

`verify.py` builds `tickets_by_id` with a dict comprehension, so duplicate ids keep the last row. Duplicate rows are not SLA-eligible, so deadline recomputation does not use them. Left as-is.

## What would have been treated as a bug

Examples that would have justified a Python fix plus tests: mapping `Urgent` to P1, pausing SLA on `waiting_customer`, assuming UTC for naive timestamps, or counting `stop == deadline` as breached while tests assert otherwise.

None of those are present. The exporter therefore **copies** Phase A clocks and only changes **aggregation** for the report page (unique ticket rows; exclusive ageing KPI).
