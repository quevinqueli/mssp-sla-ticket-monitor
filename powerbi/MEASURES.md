# Measure explanations

DAX lives in [model/measures.dax](model/measures.dax) and [model/measures.tmdl](model/measures.tmdl). Every KPI counts **precomputed 0/1 flags** on `fact_ticket` (or finding types on `fact_finding`). The flags are produced by `mssp_sla.powerbi_export.classify_ticket`, which calls the same `response_clock` / `resolve_clock` / `is_approaching` functions as the daily brief.

Clocks are **not** re-implemented in DAX. Reproducing parse eligibility, naive-timestamp handling, and duplicate suppression in DAX would drift from Python.

## Report-page KPIs

| Measure | Filter | Grain | Unfiltered demo | Python analog |
| --- | --- | --- | ---: | --- |
| **Open tickets** | `kpi_open = 1` | CSV row | 22 | `counts.open_tickets` (match) |
| **Breached tickets** | `kpi_breached = 1` | CSV row with ≥1 clock breach | 7 | `counts.breached_slas` = 8 findings |
| **Approaching tickets** | `kpi_approaching = 1` | CSV row | 3 | `counts.approaching_deadlines` (match) |
| **Ageing backlog** | `kpi_ageing = 1` | CSV row, exclusive remainder | 2 | `counts.ageing_backlog` = 3 |

### Open tickets

Status in the documented open set (`open`, `in_progress`, `waiting_customer`, `pending`, `investigating`). Independent of SLA eligibility. Duplicate `TCK-1020` rows both count. This card is **not** mutually exclusive with the other three.

### Breached tickets

`kpi_breached` is 1 when the response clock and/or the resolve clock is breached. Two clocks on one row (demo: `TCK-1021`) still count as **one**. Closed tickets with a historical breach are included (`TCK-1003`, `TCK-1014`); use the Status slicer to hide them.

Python `breached_slas` is the **finding list length** (8). The extra finding is the second clock on `TCK-1021`.

### Approaching tickets

Still ticking, not breached on that clock, remaining hours inside the catalog warn band (see SLA_FINDINGS.md). `kpi_approaching` is also 0 if the **row** already has any breach, so a hypothetical response-approaching + resolve-breached ticket would appear only under Breached. The demo snapshot has no such overlap (`breach ∩ approaching = ∅`).

Includes P3 `TCK-1010`. Python approaching findings also include P3; Python **attention** does not (P1/P2 only).

### Ageing backlog

Open and age ≥ 48h **and** not already counted as breached or approaching.

| Ticket | Ageing in Python? | Ageing KPI? |
| --- | --- | --- |
| TCK-1004 | yes (also resolve-breached) | **no** — shown as breached |
| TCK-1006 | yes | yes |
| TCK-1020 (96h row) | yes | yes |

Use **Ageing backlog (Python-aligned)** if you need the Phase A list length of 3.

## Mutual exclusivity

A row may contribute to **Open tickets** and **at most one** of {Breached, Approaching, Ageing}.

Priority for those three cards: **breached > approaching > ageing**.

Primary **reason for attention** on the table uses a longer ladder (first match wins):

1. SLA breached (open)
2. SLA breached (closed P1/P2) — any closed breach on this snapshot is P1/P2
3. Approaching deadline (any catalog priority, including P3/P4)
4. Ageing backlog
5. Waiting on customer ≥ 24h from `status_updated_at`
6. Unassigned
7. Data quality blocking SLA

Secondary Python reasons (for example waiting + open breach on `TCK-1009`) stay in `python_reason_rule_ids` and in `why_for_attention`; they do not get a second table row.

If both clocks are breached, the table deadline and overdue hours use the **response** clock (shorter window). Demo: `TCK-1021` deadline `2026-09-19T04:15:00+00:00`, overdue 7.75h.

## Python-aligned (keep off the page unless reconciling)

| Measure | Definition | Demo |
| --- | --- | ---: |
| Breached findings (Python-aligned) | `fact_finding` rows whose type is `response_sla_breach` or `resolve_sla_breach` | 8 |
| Approaching findings (Python-aligned) | `approaching_response` or `approaching_resolve` | 3 |
| Ageing backlog (Python-aligned) | `kpi_ageing_python = 1` (no exclusivity) | 3 |
| Attention tickets (Python-aligned) | `is_python_attention = 1` | 18 |

Phase A `attention_list` **does not** include ageing-only tickets (`TCK-1006`) or P3/P4 approaching (`TCK-1010`). The action table **does**, so KPI drill-through is not empty.

## Header and table helpers

| Measure | Role |
| --- | --- |
| Snapshot timestamp | `SELECTEDVALUE(dim_snapshot[as_of_label])` → `19 Sep 2026 12:00 UTC` |
| Synthetic demonstration data | Banner text from `dim_snapshot` |
| Actionable tickets | `in_action_table = 1` → 20 unfiltered rows |

## Bar chart

Same measure as the Breached card, grouped by `dim_client[client_label]`. Unfiltered: CUST-A 4, CUST-C 3, total 7.

## Filter behaviour

Client / priority / status slicers sit on the dimensions. All ticket KPIs are `CALCULATE(COUNTROWS(fact_ticket), flag = 1)` and therefore respect those relationships. Finding-count measures filter through `fact_finding → fact_ticket → dims`.
