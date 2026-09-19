# Reconciliation — dashboard KPIs vs Phase A

Frozen snapshot: `as_of = 2026-09-19T12:00:00+00:00`  
Source: `data/synthetic_tickets.csv`  
Python: `artifacts/metrics.json` (verification **PASSED**)  
Export: `powerbi/data/expected_kpis.json` (must match a fresh `python3 scripts/export_powerbi.py`)

Unfiltered = no client / priority / status slicer.

## Card KPIs (Python-matching big numbers)

| Dashboard visual | DAX measure | Grain | SQL-like definition | Python field | Unfiltered expected |
| --- | --- | --- | --- | --- | --- |
| Open tickets | `[Open Tickets]` | **Parsed row** (DimTicket) | `COUNT(*) FROM DimTicket WHERE is_open = 1` | `counts.open_tickets` | **22** |
| Breached SLAs | `[Breached SLAs (findings)]` | **Finding** | `COUNT(*) FROM FactFindings WHERE finding_family = 'sla_breach'` | `counts.breached_slas` | **8** |
| Approaching deadlines | `[Approaching Deadlines (findings)]` | **Finding** | `COUNT(*) FROM FactFindings WHERE finding_family = 'approaching'` | `counts.approaching_deadlines` | **3** |
| Ageing backlog | `[Ageing Backlog (findings)]` | **Finding** | `COUNT(*) FROM FactFindings WHERE finding_family = 'ageing_backlog'` | `counts.ageing_backlog` | **3** |

These four numbers are the **card values**. They exist so the page can be checked against `metrics.json` without translating grain in your head.

## Ticket-level DISTINCTCOUNT (must be shown as grain notes / bar chart)

Python finding counts **double-count a ticket that has two findings**. Ticket-level KPIs use `DISTINCTCOUNT(ticket_id)`.

| Dashboard use | DAX measure | Grain | SQL-like definition | Python analogue | Unfiltered expected |
| --- | --- | --- | --- | --- | --- |
| Note under Open tickets | `[Open Ticket IDs]` | Distinct `ticket_id` | `COUNT(DISTINCT ticket_id) FROM DimTicket WHERE is_open = 1` | *none* (Python counts rows) | **21** |
| Note under Breached SLAs; bar chart values | `[Breached Tickets]` | Distinct `ticket_id` with ≥1 breach finding | `COUNT(DISTINCT ticket_id) FROM FactFindings WHERE finding_family = 'sla_breach'` | *none* as a count field; derive from `breached_slas` list | **7** |
| Note under Approaching | `[Approaching Tickets]` | Distinct `ticket_id` | `COUNT(DISTINCT ticket_id) FROM FactFindings WHERE finding_family = 'approaching'` | derive from `approaching_deadlines` list | **3** |
| Note under Ageing | `[Ageing Tickets]` | Distinct `ticket_id` | `COUNT(DISTINCT ticket_id) FROM FactFindings WHERE finding_family = 'ageing_backlog'` | derive from `ageing_backlog` list | **3** |

### Why 8 findings ≠ 7 tickets

`TCK-1021` appears twice in `breached_slas`:

| evidence_id | finding_type |
| --- | --- |
| `response_sla_breach:TCK-1021:SLA-RESPONSE-P1` | response |
| `resolve_sla_breach:TCK-1021:SLA-RESOLVE-P1` | resolve |

A `COUNTROWS` card shows **8**. A `DISTINCTCOUNT` ticket KPI or bar chart must show **7**. Both are correct; they answer different questions.

### Why 22 open rows ≠ 21 open ticket ids

`TCK-1020` is two parsed CSV rows (duplicate `ticket_id`). Python `open_tickets` = 22 includes both. `DISTINCTCOUNT(ticket_id)` = 21. The card follows Python (22). The note discloses 21.

## Other Python counts (not required as cards; used to validate the model)

| Check | DAX / table | Python field | Unfiltered expected |
| --- | --- | --- | --- |
| DimTicket row count | `[Total Tickets (rows)]` | `counts.total_tickets` | **27** |
| SLA-eligible rows | `[SLA Eligible (rows)]` | `counts.sla_eligible` | **19** |
| Attention table rows | `[Attention Rows]` / `COUNTROWS(FactAttention)` | `counts.attention` | **18** |
| Distinct attention ticket_id | `[Attention Ticket IDs]` | *none* (TCK-1020 has two attention rows) | **17** |
| Data-quality findings | `[Data Quality Flags (findings)]` | `counts.data_quality_flags` | **10** |

## Breached tickets by client (bar chart)

Definition: distinct `ticket_id` in `FactFindings` with `finding_family = 'sla_breach'`, grouped by `customer_id`.

SQL-like:

```sql
SELECT customer_id, COUNT(DISTINCT ticket_id) AS breached_tickets
FROM FactFindings
WHERE finding_family = 'sla_breach'
GROUP BY customer_id
```

| customer_id | Distinct tickets | Ticket ids | Findings (do not plot this) |
| --- | --- | --- | --- |
| CUST-A | **4** | TCK-1001, TCK-1003, TCK-1014, TCK-1017 | 4 |
| CUST-C | **3** | TCK-1004, TCK-1009, TCK-1021 | **4** (TCK-1021 ×2) |
| CUST-B | 0 | — | 0 |
| CUST-D | 0 | — | 0 |
| CUST-E | 0 | — | 0 |
| **Total** | **7** | | **8** |

If CUST-C shows **4** on the bar chart, the visual is using finding-grain. Switch the measure to `[Breached Tickets]`.

## Attention table

| Check | Expected |
| --- | --- |
| Row count | **18** (`counts.attention`) |
| Grain | One row per `evidence_id` (not collapsed by `ticket_id`) |
| `TCK-1020` | Two rows: `attention:TCK-1020` (`ticket_key` 21) and `attention:TCK-1020:row-22` (`ticket_key` 22) |
| `TCK-1021` deadline | `2026-09-19T04:15:00+00:00` from `response_sla_breach:TCK-1021:SLA-RESPONSE-P1` (earliest of response 04:15 and resolve 08:00) |
| `TCK-1005` deadline | `2026-09-19T12:15:00+00:00` (approaching response) |
| DQ-only rows (e.g. TCK-1007) | `linked_deadline` blank — do not invent one |

`reason_for_attention` is Phase A `why_it_qualifies` (e.g. “open ticket has at least one SLA breach”). It is not a new classification.

## SnapshotMeta

| Column | Expected |
| --- | --- |
| `as_of` | `2026-09-19T12:00:00+00:00` |
| `source_csv` | `data/synthetic_tickets.csv` |
| `sla_catalog_version` | `v1` |
| `synthetic_flag` | `1` (true) |
| `verification_passed` | `1` (true) |
| `row_count` | `27` |
| `eligible_for_sla` | `19` |

The page banner **SYNTHETIC DATA** is this flag, not optional decoration.

## What this page must not show

- Any KPI that cannot be written as a filter on these tables
- Day-over-day, week-to-date, or “trend” of breaches
- Customer names, industry, or revenue (CSV has only `customer_id`)
- Mapping `Urgent` or `P5` to P1

## Quick Desktop checklist (unfiltered)

1. Open tickets card = **22**
2. Open tickets note distinct ids = **21**
3. Breached SLAs card = **8**
4. Breached tickets note / total of bar chart = **7**
5. Bar: CUST-A **4**, CUST-C **3**
6. Approaching card = **3**
7. Ageing card = **3**
8. Attention table rows = **18**
9. Banner = **SYNTHETIC DATA**
10. as_of = **2026-09-19T12:00:00+00:00**
11. Verification = **PASSED**

## Slicer check (Client = CUST-C only)

Same grain rules as the cards. This is the client that contains TCK-1021 (two breach findings).

| Measure | Expected |
| --- | --- |
| `[Open Tickets]` | **5** |
| `[Breached SLAs (findings)]` | **4** |
| `[Breached Tickets]` | **3** |
| `[Attention Rows]` | **5** |

CUST-C findings are TCK-1004, TCK-1009, TCK-1021×2. Distinct tickets are three. If both measures show 4, DISTINCTCOUNT is not in use.
