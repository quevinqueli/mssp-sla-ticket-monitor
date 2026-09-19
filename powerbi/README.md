# Power BI SLA attention package

One report page that answers: **which tickets and clients need attention, and why?**

This folder is designed to be pasted and imported into **Power BI Desktop on Windows**. It was assembled on Linux **without Power BI Desktop**, so visuals, alignment, and theme rendering have **not** been checked in Desktop. Treat the CSVs, DAX, theme, and layout spec as the deliverable; complete the page locally using [DESKTOP_SETUP.md](DESKTOP_SETUP.md).

## Snapshot

| Item | Value |
| --- | --- |
| Source CSV | `data/synthetic_tickets.csv` |
| As of | `2026-09-19T12:00:00Z` (`19 Sep 2026 12:00 UTC`) |
| Classification | Synthetic demonstration data |
| SLA catalog | v1 |

Unfiltered report-page KPIs for that snapshot:

| Card | Value |
| --- | ---: |
| Open tickets | 22 |
| Breached tickets | 7 |
| Approaching tickets | 3 |
| Ageing backlog | 1 |

Python Phase A list lengths, and the two intentional deltas, are in [RECONCILIATION.md](RECONCILIATION.md).

## What is in this folder

| Path | Role |
| --- | --- |
| `data/*.csv` | Star schema ready for Get Data → Text/CSV |
| `data/expected_measures.json` | Frozen KPI values used by tests |
| `model/measures.dax` | Paste-ready DAX |
| `model/measures.tmdl` | Same measures as a TMDL fragment (reviewable) |
| `model/Model.bim` | Logical tabular model (no import partitions) |
| `model/relationships.md` | Relationship diagram and cardinality |
| `theme/mssp-sla-theme.json` | Restrained report theme |
| `report/page-attention.json` | Page coordinates and visual spec |
| `DESKTOP_SETUP.md` | Click-by-click Desktop build |
| `PAGE_LAYOUT.md` | Layout, spacing, colour rules |
| `MEASURES.md` | What each measure means |
| `SLA_FINDINGS.md` | SLA ambiguities found in Python before writing DAX |
| `RECONCILIATION.md` | Report numbers vs `artifacts/metrics.json` |

A full `.pbip` / PBIR visual tree is **not** shipped. Without Desktop it cannot be validated, and a fabricated `report.json` would likely fail to open.

## Refresh the CSVs after ticket data changes

From the repo root (stdlib only):

```bash
python3 scripts/export_powerbi_star.py
python3 scripts/reconcile_powerbi.py --write
pytest tests/test_powerbi_export.py
```

The exporter calls the same Phase A clocks as `scripts/run_demo.py`. Do not hand-edit the KPI flag columns.

## Trends

Omitted. The demo is a single frozen `as_of` instant, not a history of daily snapshots.
