# Power BI ↔ Python reconciliation

- Snapshot: `2026-09-19T12:00:00+00:00`
- Source: `data/synthetic_tickets.csv`
- Filters: none (all clients, priorities, statuses)
- Phase A verification: **PASSED**

Report-page KPIs are ticket-row counts with a breached > approaching > ageing exclusion so a ticket is not in two of those three cards. Python list lengths are shown beside them. Intentional deltas are documented below.

| Report measure | Report value | Python analog | Python value | Match? |
| --- | ---: | --- | ---: | --- |
| Open tickets | 22 | `counts.open_tickets` | 22 | yes |
| Breached tickets | 7 | `counts.breached_slas` (findings) | 8 | intentional delta |
| Approaching tickets | 3 | `counts.approaching_deadlines` | 3 | yes |
| Ageing backlog | 2 | `counts.ageing_backlog` | 3 | intentional delta |
| Breached findings (Python-aligned) | 8 | `counts.breached_slas` | 8 | yes |
| Ageing backlog (Python-aligned) | 3 | `counts.ageing_backlog` | 3 | yes |
| Attention tickets (Python-aligned) | 18 | `counts.attention` | 18 | yes |

## Breached tickets by client (bar chart)

| Client | Breached tickets |
| --- | ---: |
| CUST-A | 4 |
| CUST-C | 3 |

Bar total: **7** (must equal Breached tickets = 7).

## Action table by primary reason

Rows: **20**

| Primary reason | Rows |
| --- | ---: |
| Ageing backlog | 2 |
| Approaching deadline | 3 |
| Data quality | 7 |
| SLA breached (closed P1/P2) | 2 |
| SLA breached (open) | 5 |
| Unassigned | 1 |

## Intentional deltas

- **Breached tickets**: report `7` vs Python `counts.breached_slas` = `8`. Python counts SLA clock findings. TCK-1021 has both a response and a resolve breach (2 findings, 1 ticket). The KPI counts unique ticket rows so the card does not double-count overlapping clocks.
- **Ageing backlog**: report `2` vs Python `counts.ageing_backlog` = `3`. TCK-1004 is ageing and resolve-breached. The ageing KPI excludes rows already in the breached KPI so the four cards do not double-count the same ticket. Use 'Ageing backlog (Python-aligned)' to match Phase A.

## Cross-KPI exclusivity

A row may contribute to **Open tickets** and at most one of Breached / Approaching / Ageing.

No row has more than one of `kpi_breached`, `kpi_approaching`, `kpi_ageing`.

## Trends

Not included. Source data is a single frozen as_of snapshot, not a time series of daily operational counts.

## Desktop validation

These numbers are computed in Python from the same flags the DAX counts. They were **not** refreshed or visually checked in Power BI Desktop.
