# Power BI demo (spec + data)

This folder is an **additive** Power BI demo for the frozen Phase A snapshot. It does not replace `scripts/run_demo.py`, `mssp_sla/`, `tests/`, or `artifacts/`.

There is **no validated `.pbix` in this repository**. This Linux environment cannot author or refresh Power BI Desktop. Quévin builds the `.pbix` locally on Windows by following [DESKTOP_SETUP.md](DESKTOP_SETUP.md).

All exported rows are **synthetic**. `SnapshotMeta.synthetic_flag = 1` and the report page must show a first-class **SYNTHETIC DATA** label.

## Frozen snapshot

| Item | Value |
| --- | --- |
| `as_of` | `2026-09-19T12:00:00Z` (`data/DEMO_AS_OF.txt`) |
| Source CSV | `data/synthetic_tickets.csv` |
| Phase A metrics | `artifacts/metrics.json` (verification PASSED) |
| Export command | `python3 scripts/export_powerbi.py` |
| Output | `powerbi/data/*.csv` plus `expected_kpis.json` |

Re-run the export after changing the Python pipeline or demo CSV. `tests/test_powerbi_export.py` requires the committed CSVs to match a fresh pipeline build and to reconcile with `artifacts/metrics.json`.

## What to read

| File | Purpose |
| --- | --- |
| [data/](data/) | Star-schema CSVs + `expected_kpis.json` |
| [relationships.md](relationships.md) | Keys, cardinality, filter direction |
| [measures.dax](measures.dax) | Paste-ready DAX (DISTINCTCOUNT for ticket KPIs) |
| [page_layout.md](page_layout.md) | One-page wireframe |
| [reconciliation.md](reconciliation.md) | Dashboard KPI → Python field, frozen numbers |
| [DESKTOP_SETUP.md](DESKTOP_SETUP.md) | Exact Desktop steps vs what this PR already did |

## Grain (read before building visuals)

Python `counts` are **not** all the same grain:

- `open_tickets` / `total_tickets` / `sla_eligible` / `attention` count **parsed rows** (or attention evidence rows). Duplicate `ticket_id` **TCK-1020** is two DimTicket rows and two FactAttention rows.
- `breached_slas`, `approaching_deadlines`, `ageing_backlog`, `data_quality_flags` count **findings**. **TCK-1021** has both a response breach and a resolve breach → 2 findings, 1 distinct ticket.

Ticket-level dashboard KPIs that sit on findings **must** use `DISTINCTCOUNT` of `ticket_id`. Do not `COUNTROWS` findings for “how many tickets breached.”

Do not add time intelligence, prior-day comparisons, or invented customer attributes. This model is a **single snapshot**.

## Tables

| Table | Grain | Primary key |
| --- | --- | --- |
| DimTicket | One row per parsed CSV row | `ticket_key` (= `csv_row_number`) |
| DimClient | One row per `customer_id` | `customer_id` |
| DimPriority | One row per `priority_key` | `priority_key` |
| DimStatus | One row per `status_key` | `status_key` |
| FactFindings | One row per Phase A finding (breach, approaching, ageing, DQ) | `evidence_id` |
| FactAttention | One row per attention `evidence_id` | `evidence_id` |
| SnapshotMeta | One row for this snapshot | `snapshot_id` |
