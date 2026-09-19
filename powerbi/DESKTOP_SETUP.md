# Desktop setup (Power BI Desktop on Windows)

**This page was not built or visually checked in Power BI Desktop.** The steps below are the local work. Budget one sitting: import seven CSVs, set types, create six relationships, paste twelve measures, apply the theme, place twelve visuals, then check the numbers in [RECONCILIATION.md](RECONCILIATION.md).

Use Power BI Desktop (current Windows build). Canvas: **16:9**, **1280 × 720**, fit-to-page.

## 0. Files to copy onto the Windows machine

Copy the whole `powerbi/` directory. You need at least:

- `powerbi/data/fact_ticket.csv`
- `powerbi/data/fact_finding.csv`
- `powerbi/data/dim_client.csv`
- `powerbi/data/dim_priority.csv`
- `powerbi/data/dim_status.csv`
- `powerbi/data/dim_attention_reason.csv`
- `powerbi/data/dim_snapshot.csv`
- `powerbi/model/measures.dax`
- `powerbi/theme/mssp-sla-theme.json`
- `powerbi/report/page-attention.json` (coordinates while placing visuals)

## 1. New report

1. File → New → Report (blank).
2. Rename the page tab to `Attention`.
3. View → Page view → **Fit to page**.
4. Format page → Canvas settings → Type **16:9** (1280 × 720).
5. Format page → Wallpaper / canvas background `#F8FAFC` (the theme also sets this).

## 2. Apply the theme first

1. View → Themes → Browse for themes.
2. Select `powerbi/theme/mssp-sla-theme.json`.
3. Do not pick a colourful built-in theme afterwards.

## 3. Import the seven CSVs

Repeat for each file in this order (facts last is fine; order does not matter):

`dim_client`, `dim_priority`, `dim_status`, `dim_attention_reason`, `dim_snapshot`, `fact_ticket`, `fact_finding`.

For each file:

1. Home → Get data → **Text/CSV**.
2. Select the file → **Transform data** (do not Load yet on the first file; for later files, Transform data as well so you can set types).
3. In Power Query, set types:

| Columns | Type |
| --- | --- |
| `*_key`, ids, labels, ISO timestamp text you will **not** plot on a date axis | Text |
| `created_at`, `first_response_at`, `resolved_at`, `status_updated_at`, `deadline`, `response_deadline`, `resolve_deadline`, `as_of_utc` | Date/Time (keep the `+00:00` offset; this snapshot is UTC) |
| `row_number`, `*_sort`, `row_count` | Whole number |
| All `kpi_*`, `is_*`, `has_*`, `*_breached`, `*_eligible`, `in_action_table`, `in_catalog`, `is_open_status`, `is_closed_status`, `is_kpi_bucket` | Whole number (0/1) |
| `age_hours`, `waiting_hours`, `*_hours`, `overdue_hours`, `remaining_hours`, `response_hours`, `resolve_hours` | Decimal number |

4. Home → Close & Apply.

If Power Query warns about changing types, accept. Do **not** use “Detect data type” as a substitute for the table above — several flag columns would become True/False and the DAX (`= 1`) would return blank.

Optional: in Model view, hide `ticket_row_key`, `snapshot_id`, `reason_sort`, `priority_sort`, and the raw `kpi_*` columns from Report view after measures exist.

## 4. Relationships

Open **Model view**. Create **many-to-one**, **single direction** (from fact toward dimension), cardinality `* : 1`:

| From (many) | To (one) |
| --- | --- |
| `fact_ticket[client_key]` | `dim_client[client_key]` |
| `fact_ticket[priority_key]` | `dim_priority[priority_key]` |
| `fact_ticket[status_key]` | `dim_status[status_key]` |
| `fact_ticket[primary_reason_key]` | `dim_attention_reason[reason_key]` |
| `fact_ticket[snapshot_id]` | `dim_snapshot[snapshot_id]` |
| `fact_finding[ticket_row_key]` | `fact_ticket[ticket_row_key]` |

Do **not** also relate `fact_finding` directly to the dimensions. That creates a second filter path.

Mark `dim_client[client_key]`, `dim_priority[priority_key]`, `dim_status[status_key]`, `dim_attention_reason[reason_key]`, `dim_snapshot[snapshot_id]`, and `fact_ticket[ticket_row_key]` as unique if Desktop asks.

## 5. Measures

1. Select `fact_ticket` in Data view (or Model view).
2. Open `powerbi/model/measures.dax`.
3. For each assignment, New measure → paste **one** `Name = <expression>` block.
4. Set format:

| Measure | Format |
| --- | --- |
| Open / Breached / Approaching / Ageing / Python-aligned / Actionable tickets | Whole number (`#,0`) |
| Snapshot timestamp | Text |
| Synthetic demonstration data | Text |

Display folders (optional): KPIs, Python-aligned, Table, Header — matching comments in the DAX file.

Do **not** rewrite the clocks in DAX. Eligibility, duplicate handling, and timezone rules already ran in Python.

## 6. Place visuals

Coordinates are in `report/page-attention.json`. Margin 24px, gutter 16px.

### Header

1. Insert a **text box**: “Which tickets and clients need attention, and why?” at (24, 12), 760×32. Segoe UI Semibold, 16pt, `#1D2939`.
2. Insert a **card** with measure `Snapshot timestamp` at (24, 44), 360×28. Title: `As of`. Category label on.
3. Insert a **card** with measure `Synthetic demonstration data` at (880, 16), 376×36. Callout colour `#B54708`, background `#FFFAEB`. This label must stay on the page.

### Filters (on-canvas slicers, not only the filter pane)

| Slicer | Field | Position | Style |
| --- | --- | --- | --- |
| Client | `dim_client[client_label]` | (24, 88) 400×72 | Dropdown, multi-select, Select all |
| Priority | `dim_priority[priority_label]` | (440, 88) 400×72 | Dropdown. Sort by `priority_sort` |
| Status | `dim_status[status_label]` | (856, 88) 400×72 | Dropdown |

### KPI cards

| Card | Measure | Position | Callout colour |
| --- | --- | --- | --- |
| Open | `Open tickets` | (24, 176) 296×100 | `#344054` (neutral) |
| Breached | `Breached tickets` | (336, 176) 296×100 | `#B42318` |
| Approaching | `Approaching tickets` | (648, 176) 296×100 | `#B54708` |
| Ageing | `Ageing backlog` | (960, 176) 296×100 | `#175CD3` |

Turn **category labels on** so the measure name is the caption. Do not use a rainbow of extra colours.

### Bar chart

1. Clustered **bar** chart at (24, 292), 1232×168.
2. Y-axis (category): `dim_client[client_label]`.
3. X-axis (values): measure **`Breached tickets`** — not Count of `ticket_id`.
4. Data colour: `#B42318` for every bar.
5. Title: `Breached tickets by client`. Legend off.
6. Unfiltered demo: **CUST-A = 4**, **CUST-C = 3**. Clients with zero breaches should not dominate; Desktop may still list them — if so, filter the visual to `Breached tickets > 0` or “Show items with no data” **off**.

### Action table

1. Table visual at (24, 476), 1232×220.
2. Filters on this visual: `fact_ticket[in_action_table]` **is 1**.
3. Add columns in this order:

   - `fact_ticket[ticket_id]` (header: Ticket)
   - `dim_client[client_label]` (Client)
   - `fact_ticket[priority_display]` (Priority)
   - `fact_ticket[status_display]` (Status)
   - `fact_ticket[deadline]` (Deadline)
   - `fact_ticket[overdue_hours]` (Overdue hours)
   - `fact_ticket[remaining_hours]` (Remaining hours)
   - `fact_ticket[primary_reason_label]` (Reason for attention)
   - `fact_ticket[why_for_attention]` (Why)

4. Sort by `reason_sort` ascending, then `overdue_hours` descending. If `reason_sort` should stay hidden, add it to the visual, sort, then remove it from the values well after Desktop keeps the sort (if it drops the sort, leave `reason_sort` as a narrow column or sort by `primary_reason_label`).
5. Conditional font colour on **Reason for attention** only:

   - contains `SLA breached` → `#B42318`
   - equals `Approaching deadline` → `#B54708`
   - equals `Ageing backlog` → `#175CD3`

   Leave other reasons at default body colour `#1D2939`.
6. Unfiltered demo: **20 rows**.

Do **not** add a trend/line chart.

## 7. Number check (same snapshot, no slicers)

After apply, with all slicers cleared:

| Visual | Expected |
| --- | --- |
| Open tickets | **22** |
| Breached tickets | **7** |
| Approaching tickets | **3** |
| Ageing backlog | **1** |
| Bar | CUST-A **4**, CUST-C **3** |
| Table rows | **20** |
| As of | **19 Sep 2026 12:00 UTC** |
| Banner | **Synthetic demonstration data** |

Slicer smoke tests:

| Filter | Open | Breached | Approaching | Ageing |
| --- | ---: | ---: | ---: | ---: |
| Status = `resolved` | 0 | 2 | 0 | 0 |
| Client = `CUST-A` | 4 | 4 | 0 | 0 |
| Priority = `P1` | 5 | 4 | 1 | 0 |

If Open = 22 but Breached = 8, the card is counting findings or summing a flag the wrong way — use the **measure**, not Count of `has_any_breach` added as a column (that also happens to be 7) and **not** Count of rows in `fact_finding`.

Python-aligned measures (optional, keep off the page or in a tooltip):

| Measure | Expected |
| --- | ---: |
| Breached findings (Python-aligned) | 8 |
| Ageing backlog (Python-aligned) | 2 |
| Attention tickets (Python-aligned) | 18 |

## 8. What you must still do locally

- Nudge pixels until cards, slicers, bar, and table align (the JSON is a spec, not a `.pbix`).
- Confirm dropdown slicers do not overlap the KPI row at your DPI/zoom.
- Save as `MSSP SLA Attention.pbix` (and optionally File → Save as Power BI Project if you want a `.pbip` from a Desktop-validated file).
- If you reconnect to a new ticket CSV, re-run `python3 scripts/export_powerbi_star.py` and refresh the CSVs in Desktop. Do not implement SLA clocks only in DAX unless you also extend the tests.

## 9. What was not done here

- No `.pbix` was created.
- No Desktop render, contrast, or interaction pass.
- Theme JSON follows the published theme schema but was not applied in Desktop.
- `Model.bim` has no M partitions; Desktop import of CSVs is the supported path.
