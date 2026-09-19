# Page layout spec

Single page, 1280 × 720, 16:9, fit-to-page. Machine-readable coordinates: [report/page-attention.json](report/page-attention.json).

**Not Desktop-validated.** Align to the 24px margin / 16px gutter grid; nudge if slicer chrome differs at your DPI.

## Grid

```
24px margin
┌─────────────────────────────────────────────────────────────┐
│ Title                                         SYNTHETIC     │
│ As of 19 Sep 2026 12:00 UTC                   DEMONSTRATION │
│ Client ▾          Priority ▾          Status ▾              │
│ [ Open 22 ] [ Breached 7 ] [ Approaching 3 ] [ Ageing 2 ]   │
│ Breached tickets by client (bar, single red)                │
│ Actionable tickets (table, 20 rows unfiltered)              │
└─────────────────────────────────────────────────────────────┘
```

| Band | Y | Height |
| --- | ---: | ---: |
| Title + snapshot + banner | 12 | 64 |
| Slicers | 88 | 72 |
| KPI cards | 176 | 100 |
| Bar chart | 292 | 168 |
| Table | 476 | 220 |

Horizontal: x=24, then 296px cards with 16px gutters (24, 336, 648, 960). Content width 1232.

## Colour (status only)

| Use | Hex | Where |
| --- | --- | --- |
| Neutral text / open volume | `#1D2939` / `#344054` | Title, Open card |
| Breached | `#B42318` | Breached card callout, bar, table reason |
| Approaching / wait warning | `#B54708` | Approaching card, synthetic banner text |
| Ageing | `#175CD3` | Ageing card, table reason |
| Page background | `#F8FAFC` | Canvas |
| Card/table surface | `#FFFFFF` | Visual backgrounds |
| Hairline | `#E4E7EC` | Visual borders |

Do not assign a distinct colour per client on the bar chart. Do not colour the Open card red.

## Typography

- Title: Segoe UI Semibold 16pt
- Card callout: Segoe UI Semibold 28pt
- Card category / slicer header / table header: Segoe UI Semibold 10pt
- Table body / slicer items: Segoe UI 10pt

## What stays off the page

- Line or area **trends** (single `as_of` snapshot).
- Python-aligned finding-count measures (keep in the model for reconciliation; not as a fifth KPI).
- Decorative icons, gradients, and extra KPI targets.

## Alignment checklist (do this in Desktop)

- KPI card tops and bottoms share Y=176 / Y=276.
- Slicer tops share Y=88; slicer widths 400 / 400 / 400 with 16px gaps (24, 440, 856).
- Bar and table left edges at x=24, width 1232 (same as the four cards combined).
- Snapshot remains readable at 100% zoom; banner is not cropped on the right.
