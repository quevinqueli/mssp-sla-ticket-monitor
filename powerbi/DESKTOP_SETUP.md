# Power BI Desktop setup (Windows)

Audience: Quévin, building a local `.pbix` from this repo on **Windows Power BI Desktop**.

This repository **does not contain a validated `.pbix`**. The Linux cloud environment used to author the PR cannot run Power BI Desktop, cannot refresh a Desktop model, and cannot screenshot DAX results. What you build locally is the first live report.

## What this PR already completed

| Done in git | Not done (you do this in Desktop) |
| --- | --- |
| Frozen Phase A metrics (`artifacts/metrics.json`, verification PASSED) | Create a blank `.pbix` |
| Star-schema CSVs under `powerbi/data/` | Import those CSVs |
| `scripts/export_powerbi.py` to regenerate CSVs from the same pipeline / `as_of` | Click-through of Get Data / Power Query |
| Keys, cardinality, filter direction ([relationships.md](relationships.md)) | Draw the relationships in Model view |
| Paste-ready DAX ([measures.dax](measures.dax)) | Create each measure |
| One-page wireframe ([page_layout.md](page_layout.md)) | Place visuals, titles, banner, slicers |
| Expected numbers ([reconciliation.md](reconciliation.md)) | Confirm cards/chart/table match those numbers |
| pytest lockstep vs `metrics.json` | Save `MSSP SLA snapshot.pbix` on your machine |

Do **not** expect a reviewer to open a `.pbix` from this PR. Optional: add `*.pbix` to your local git excludes (already in repo `.gitignore`) so the binary stays off GitHub.

## Prerequisites

- Windows PC with Power BI Desktop (current Microsoft Store or Download Center build is fine).
- This repo cloned. You need the folder `powerbi/data/`.
- You do **not** need Python to import the committed CSVs. Python is only required if you want to regenerate them.

Optional regenerate (same frozen `as_of` as `scripts/run_demo.py`):

```bat
cd path\to\mssp-sla-ticket-monitor
python -m pip install -r requirements.txt
python scripts\export_powerbi.py
```

Leave `artifacts/` alone unless you intend to refresh the markdown brief as well (`python scripts\run_demo.py`). The Power BI export does not rewrite Phase A artifacts.

## 1. Create the file

1. Open **Power BI Desktop**.
2. File → New.
3. File → Options and settings → Options → **Current file** → Data load → **uncheck** “Autodetect new relationships after data is loaded” (the duplicate `ticket_id` will otherwise create wrong links).
4. Save as `MSSP SLA snapshot.pbix` somewhere outside the repo, or inside the repo (gitignored).

## 2. Import the CSVs

Import **seven** CSVs as **seven separate tables**. Do not use a Folder combine / append.

Files (UTF-8 with BOM):

```
powerbi\data\DimTicket.csv
powerbi\data\DimClient.csv
powerbi\data\DimPriority.csv
powerbi\data\DimStatus.csv
powerbi\data\FactFindings.csv
powerbi\data\FactAttention.csv
powerbi\data\SnapshotMeta.csv
```

For each file:

1. Home → **Get data** → **Text/CSV**.
2. Select the file → **Transform Data** (not Load yet) on the first file; for later files you can Load then Transform if you prefer one query at a time.
3. Confirm delimiter is comma and the header row is used.
4. Rename the query to the file stem if Desktop used the full filename (`DimTicket.csv` → `DimTicket`). Names must match [measures.dax](measures.dax): `DimTicket`, `DimClient`, `DimPriority`, `DimStatus`, `FactFindings`, `FactAttention`, `SnapshotMeta`.

Do **not** import `expected_kpis.json` into the model. That file is a validation aid, not a table.

## 3. Column types in Power Query

**Keep ISO-8601 timestamps as Text** (or type **Date/Time/Timezone** if you are comfortable with it). Do **not** convert them to naive **Date/Time**: Windows local offset would shift the frozen UTC snapshot (e.g. `as_of` would no longer read `2026-09-19T12:00:00+00:00`).

Set these to **Whole Number**:

- All `*_flag` columns (`synthetic_flag`, `verification_passed`, `is_open`, `is_closed`, `is_duplicate_ticket_id`, `in_sla_catalog`, `sla_eligible`, …)
- `ticket_key`, `csv_row_number`, `ticket_id_instance`, `sort_order`
- `row_count`, `eligible_for_sla` on SnapshotMeta

Set these to **Decimal Number** when they are numeric (blank cells stay null):

- `response_hours`, `resolve_hours`
- `computed_age_hours`, `clock_elapsed_hours`, `hours_overdue`, `hours_remaining`

Leave `evidence_id`, `ticket_id`, `customer_id`, `priority_key`, `status_key`, `finding_family`, `reason_for_attention`, and other labels as **Text**.

Close & Apply.

**Row counts after load (should match exactly):**

| Table | Rows |
| --- | --- |
| DimTicket | 27 |
| DimClient | 5 |
| DimPriority | 6 |
| DimStatus | 6 |
| FactFindings | 24 (8 breach + 3 approaching + 3 ageing + 10 DQ) |
| FactAttention | 18 |
| SnapshotMeta | 1 |

If DimTicket ≠ 27, the CSV was not the frozen export.

## 4. Create a measures table (optional but cleaner)

1. Home → **Enter data**.
2. One column named `dummy`, one row `0`.
3. Name the table `_Measures`. Load it.
4. Hide the `dummy` column. Create all measures on `_Measures` (or on FactFindings if you skip this step).

## 5. Relationships

Model view. Create **exactly five** relationships, **single** cross-filter from the “one” side:

| From (1) | To (*) | Columns | Cardinality | Filter |
| --- | --- | --- | --- | --- |
| DimClient | DimTicket | `customer_id` | 1:* | Single |
| DimPriority | DimTicket | `priority_key` | 1:* | Single |
| DimStatus | DimTicket | `status_key` | 1:* | Single |
| DimTicket | FactFindings | `ticket_key` | 1:* | Single |
| DimTicket | FactAttention | `ticket_key` | 1:* | Single |

Assume referential integrity may be left **off**.

**Delete** any auto-detected relationship on `ticket_id`, or from DimClient/DimPriority/DimStatus directly to a fact table. Full rationale: [relationships.md](relationships.md).

SnapshotMeta and `_Measures` stay **disconnected**.

On DimPriority and DimStatus: in Data view, select `priority_key` / `status_key` → Column tools → **Sort by column** → `sort_order`.

## 6. Paste measures

New measure → paste **one measure at a time** from [measures.dax](measures.dax) (skip the comment blocks). Names must match, including punctuation:

- `Breached SLAs (findings)`
- `Approaching Deadlines (findings)`
- `Ageing Backlog (findings)`

If a measure errors with “Cannot find table”, the query name does not match.

Do **not** add `DATEADD`, `TOTALYTD`, `SAMEPERIODLASTYEAR`, or any date table. There is no second snapshot to compare.

## 7. Build the page

Follow [page_layout.md](page_layout.md) literally. Minimum that must exist:

1. Full-width **SYNTHETIC DATA** banner (`[Synthetic Banner]` or a text box with that exact phrase).
2. Snapshot card (`[As Of Label]`) and verification card (`[Verification Label]`).
3. Four KPI cards: Open tickets, Breached SLAs, Approaching deadlines, Ageing backlog — Python-matching measures as the **big number**, grain notes underneath.
4. Slicers: `DimClient[customer_id]`, `DimPriority[priority_key]`, `DimStatus[status_key]`.
5. Clustered bar: axis `DimClient[customer_id]`, value `[Breached Tickets]` (not the findings count).
6. Table bound to **FactAttention** with `ticket_id`, `priority_key`, `linked_deadline`, `reason_for_attention` (plus the other columns in the layout doc).

Edit interactions: client/priority/status slicers must **not** filter the SYNTHETIC DATA banner, as_of card, or verification card.

Rename the page tab to `MSSP SLA snapshot`.

## 8. Validate against reconciliation.md

With **no slicers selected**, you must see:

| Check | Value |
| --- | --- |
| Open tickets card | **22** |
| Distinct open ticket_id note | **21** |
| Breached SLAs card | **8** |
| Distinct breached tickets / bar total | **7** |
| Bar CUST-A | **4** |
| Bar CUST-C | **3** |
| CUST-C is not 4 | If it is 4, the bar is counting findings |
| Approaching deadlines card | **3** |
| Ageing backlog card | **3** |
| Attention table rows | **18** |
| Banner | **SYNTHETIC DATA** |
| as_of | `2026-09-19T12:00:00+00:00` |
| Verification | **PASSED** |

Spot-check the table:

- `TCK-1021` appears **once**, deadline `2026-09-19T04:15:00+00:00`, reason mentions SLA breach **and** empty `assigned_to`.
- `TCK-1020` appears **twice**.
- `TCK-1007` has a blank deadline.

Filter slicer **Client = CUST-C** (clear other slicers):

| Check | Value |
| --- | --- |
| Open tickets | **5** |
| Breached SLAs (findings) | **4** |
| Breached Tickets / CUST-C bar | **3** |
| Attention table rows | **5** |

If findings stay at 8 while the bar filters, the slicer is not on `DimClient` or relationships are missing.

Clear slicers. Save the `.pbix`.

## 9. If numbers disagree

1. Confirm you imported `powerbi/data/` from this commit, not an older copy.
2. Confirm relationships use `ticket_key`, not `ticket_id`.
3. Confirm the bar uses `[Breached Tickets]`.
4. Re-run `python scripts\export_powerbi.py` and `python -m pytest tests\test_powerbi_export.py` — if pytest fails, the CSVs are out of date vs Phase A.
5. Do not “fix” 22 → 21 on the Open tickets card. 22 is the Python row grain.

## 10. What you can ignore

- `powerbi/data/expected_kpis.json` is for pytest and for reading; not a Desktop source.
- Phase B (`--ai`) is unrelated to this report.
- There is no second page in the spec.
