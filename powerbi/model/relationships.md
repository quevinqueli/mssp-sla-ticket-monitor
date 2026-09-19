# Relationships

Star schema. Slicers live on dimensions; KPIs live on `fact_ticket`. All joins are **many-to-one**, **single-direction** (fact filters toward dim, or finding toward ticket).

```
dim_client              dim_priority           dim_status
     ▲                       ▲                     ▲
     │ client_key            │ priority_key        │ status_key
     │                       │                     │
     └───────────┬───────────┴──────────┬──────────┘
                 │                      │
           fact_ticket ◄──── ticket_row_key ──── fact_finding
                 │
                 ├── primary_reason_key → dim_attention_reason
                 └── snapshot_id        → dim_snapshot
```

| From | To | Notes |
| --- | --- | --- |
| `fact_ticket[client_key]` | `dim_client[client_key]` | Client slicer |
| `fact_ticket[priority_key]` | `dim_priority[priority_key]` | `UNKNOWN` holds Urgent/P5 |
| `fact_ticket[status_key]` | `dim_status[status_key]` | Open vs closed group is an attribute, not a second key |
| `fact_ticket[primary_reason_key]` | `dim_attention_reason[reason_key]` | Includes `NONE` for on-track rows |
| `fact_ticket[snapshot_id]` | `dim_snapshot[snapshot_id]` | One row in the demo |
| `fact_finding[ticket_row_key]` | `fact_ticket[ticket_row_key]` | Do not also join findings to dims |

## Grain

| Table | Grain | Demo rows |
| --- | --- | ---: |
| `fact_ticket` | One CSV data row (`row_number` + `ticket_id`) | 27 |
| `fact_finding` | One Phase A finding (`evidence_id`) | 42 |
| `dim_client` | `customer_id` as copied from the CSV | 5 |
| `dim_priority` | Normalized P1–P4 plus `UNKNOWN` | 5 |
| `dim_status` | Normalized status | 6 |
| `dim_attention_reason` | Primary-reason keys | 8 |
| `dim_snapshot` | Frozen as_of | 1 |

`ticket_id` is **not** unique (`TCK-1020` twice; empty id labeled `ROW-24`). Use `ticket_row_key` as the ticket fact primary key.

## Why findings are a second fact

Python `counts.breached_slas` is a finding list length. Relating `fact_finding` to `fact_ticket` lets the Python-aligned measures respect the same client/priority/status slicers without double-relating to dimensions (which would create two filter paths).
