# Page layout — one professional report page

Page name: **MSSP SLA snapshot**  
Canvas: 16:9 (e.g. 1280 × 720). Light background, dense-but-readable ops style.  
This is a **single snapshot**. No trend charts, no sparklines, no “vs last week.”

Every visual title below is the title to type in Desktop. Grain notes are part of the title or a line of text under the card — not a second invented metric.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ [BANNER full width]  SYNTHETIC DATA                                          │
│ Demo tickets only · do not treat customer_id as a real org                   │
├───────────────────────────────────────────────┬──────────────────────────────┤
│ [CARD] Snapshot as_of                         │ [CARD] Verification          │
│ as_of 2026-09-19T12:00:00+00:00               │ Phase A verification: PASSED │
│ measure: As Of Label                          │ measure: Verification Label  │
├────────────┬────────────┬────────────┬────────┴─────────────────────────────┤
│ Open       │ Breached   │ Approaching│ Ageing backlog                       │
│ tickets    │ SLAs       │ deadlines  │                                      │
│ **22**     │ **8**      │ **3**      │ **3**                                │
│ parsed rows│ findings   │ findings   │ findings                             │
│ distinct   │ distinct   │ distinct   │ distinct                             │
│ ticket_id  │ tickets 7  │ tickets 3  │ tickets 3                            │
│ 21         │            │            │                                      │
│            │            │            │                                      │
│ Open Tickets              Breached SLAs (findings)                          │
│ + Open Tickets Grain Note + Breached SLAs Grain Note                        │
│                           Approaching Deadlines (findings)                  │
│                           Ageing Backlog (findings)                         │
├────────────┴────────────┴────────────┴──────────────────────────────────────┤
│ SLICERS (left, stacked)     CHART (center)          (right, optional notes) │
│                             Breached tickets by client                      │
│ Client                      (distinct ticket_id with ≥1 sla_breach)         │
│  DimClient[customer_id]     clustered bar, axis = DimClient[customer_id]    │
│                             value = [Breached Tickets]                      │
│ Priority                    sort by value descending                        │
│  DimPriority[priority_key]  data labels on                                  │
│  sort by sort_order                                                         │
│                                                                             │
│ Status                                                                      │
│  DimStatus[status_key]                                                      │
│  sort by sort_order                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ TABLE — Tickets needing attention (FactAttention grain)                     │
│ ticket_id | customer_id | priority_key | status_key | linked_deadline |     │
│ reason_for_attention | assigned_to | computed_age_hours | evidence_id       │
│ Sort: linked_deadline ascending (blanks last), then priority P1→P4          │
└─────────────────────────────────────────────────────────────────────────────┘
│ Footer text box: SLA catalog v1 · source data/synthetic_tickets.csv ·       │
│ generated from Phase A pipeline · no historical trend                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Visual inventory

| # | Visual | Position | Fields / measures | Title |
| --- | --- | --- | --- | --- |
| 1 | Text box or card | Top full width, high-contrast (e.g. dark bar, white bold text) | `[Synthetic Banner]` | *(no extra title — the banner **is** the label)* |
| 2 | Card | Top-left under banner | `[As Of Label]` | Snapshot |
| 3 | Card | Top-right under banner | `[Verification Label]` | Verification |
| 4 | Card | Row of four, col 1 | `[Open Tickets]` | Open tickets |
| 5 | Card | Row of four, col 2 | `[Breached SLAs (findings)]` | Breached SLAs |
| 6 | Card | Row of four, col 3 | `[Approaching Deadlines (findings)]` | Approaching deadlines |
| 7 | Card | Row of four, col 4 | `[Ageing Backlog (findings)]` | Ageing backlog |
| 8 | Text boxes or new-card reference labels | Directly under cards 4–7 | Grain note measures | *(none)* |
| 9 | Slicer | Left column | `DimClient[customer_id]` | Client |
| 10 | Slicer | Left column | `DimPriority[priority_key]` | Priority |
| 11 | Slicer | Left column | `DimStatus[status_key]` | Status |
| 12 | Clustered bar | Center | Axis `DimClient[customer_id]`; value `[Breached Tickets]` | Breached tickets by client (distinct ticket_id) |
| 13 | Table | Bottom, full width | See columns below | Tickets needing attention |
| 14 | Text box | Footer | Catalog + source + synthetic reminder | *(none)* |

## KPI cards — what the big number is

These four cards **match Python `artifacts/metrics.json` `counts` unfiltered**. Put the grain in the title or in the note under the card so a viewer never confuses findings with tickets.

| Card | Big number (unfiltered) | Grain | Note under card (unfiltered) |
| --- | --- | --- | --- |
| Open tickets | 22 | Parsed CSV rows with `is_open = 1` | Distinct `ticket_id` = 21 (`TCK-1020` is two rows) |
| Breached SLAs | 8 | Finding-grain (`finding_family = sla_breach`) | Distinct tickets = 7 (`TCK-1021` has response + resolve) |
| Approaching deadlines | 3 | Finding-grain | Distinct tickets = 3 (same in this snapshot) |
| Ageing backlog | 3 | Finding-grain | Distinct tickets = 3 (same in this snapshot) |

If Desktop has the **New card** visual, put the grain-note measure in the reference label. Otherwise use a small text box under each card.

## Bar chart

- **Title:** `Breached tickets by client (distinct ticket_id)`
- **Axis:** `DimClient[customer_id]` — not the fact column (see [relationships.md](relationships.md))
- **Value:** `[Breached Tickets]` (`DISTINCTCOUNT` of `FactFindings[ticket_id]` where `finding_family = "sla_breach"`)
- **Do not** use `[Breached SLAs (findings)]` on this axis — that would draw CUST-C as 4 because of TCK-1021
- Unfiltered expected bars: CUST-A **4**, CUST-C **3** (CUST-B/D/E = 0; hide zeros if desired with a visual-level filter `[Breached Tickets] > 0`)
- No forecast, no line, no play axis

## Attention table (primary grain for the ticket list)

Use **FactAttention**, not DimTicket. Python’s attention list is one row per `evidence_id` (18 rows). `TCK-1020` appears twice on purpose.

| Column | Source | Role |
| --- | --- | --- |
| `ticket_id` | FactAttention | Identity (may repeat) |
| `customer_id` | FactAttention | Client |
| `priority_key` | FactAttention | Priority |
| `status_key` | FactAttention | Status |
| `linked_deadline` | FactAttention | Deadline from linked breach/approaching evidence; blank when none |
| `reason_for_attention` | FactAttention | Why the ticket is on the list |
| `assigned_to` | FactAttention | From CSV; blank means unassigned |
| `computed_age_hours` | FactAttention | Age at `as_of` when known |
| `evidence_id` | FactAttention | Traceability back to Phase A |

Optional tooltip / extra column: `linked_deadline_source` (which `evidence_id` supplied the deadline).

**Deadline rule (already in the CSV):** earliest `computed_deadline` among linked SLA findings. Do not average, sum, or invent a deadline for data-quality-only rows.

## Slicers

All three slicers must be **on the dimension tables**, List or Dropdown, multi-select with Select all.

| Slicer | Field | Sort |
| --- | --- | --- |
| Client | `DimClient[customer_id]` | Alphabetical |
| Priority | `DimPriority[priority_key]` | `DimPriority[sort_order]` (P1–P4, then Urgent/P5) |
| Status | `DimStatus[status_key]` | `DimStatus[sort_order]` |

Sync slicers: not applicable (one page).

## SYNTHETIC DATA + as_of (first-class)

Do not bury these in a tooltip.

1. **Banner** at the top of the page, full width, using `[Synthetic Banner]` (or the literal text `SYNTHETIC DATA` if you prefer a static text box). Font large enough to read at 100% zoom.
2. **Snapshot card** with `[As Of Label]` immediately under the banner.
3. Footer repeats that the CSV is synthetic.

`SnapshotMeta` is disconnected; these cards always show the one snapshot row and should **not** respond to client/priority/status slicers. In Desktop: Format visual → Edit interactions → slicers **do not filter** the banner, as_of card, or verification card.

## Color (optional, keep accessible)

- Banner: strong warning (e.g. dark charcoal + white, or amber + black). Not decorative pastels.
- KPI cards: default theme; do not color-code “red = bad” in a way that implies a threshold we did not compute.
- Bar chart: one series, one color.
- Table: wrap `reason_for_attention`; do not truncate the why-text to a slogan.

## Out of scope for this page

- Second page / drillthrough (optional later; not required)
- Map visuals, AI visuals, Q&A, decomposition tree
- Measures that compare to another day
- Any visual whose value cannot be checked in [reconciliation.md](reconciliation.md)
