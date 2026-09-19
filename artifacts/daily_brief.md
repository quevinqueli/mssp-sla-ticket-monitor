# MSSP Daily SLA Operational Brief

- As of: `2026-09-19T12:00:00+00:00`
- Source CSV: `data/synthetic_tickets.csv`
- SLA catalog: `v1`
- Generated at: `2026-09-19T12:00:00+00:00`
- Verification: **PASSED — figures below were recomputed from timestamps and the SLA catalog.**

## Snapshot (verified counts only)

- Tickets in file: **27**
- SLA-eligible tickets: **19**
- Open tickets: **22**
- SLA breach findings: **8**
- Approaching-deadline findings: **3**
- Ageing backlog findings: **2**
- Attention-list rows: **18**
- Data-quality findings: **10**

These counts are list lengths from Phase A. They are not forecasts or risk scores. Attention-list rows use CSV-row grain: a repeated ticket_id is one row per matching CSV line.

## Breached SLAs

### response_sla_breach:TCK-1001:SLA-RESPONSE-P1
- Ticket: `TCK-1001`
- Rule: `SLA-RESPONSE-P1`
- Type: response_sla_breach
- Priority: P1
- Status: open
- Customer id (from CSV): `CUST-A`
- Assigned to (from CSV): `alice`
- created_at: 2026-09-19T10:00:00+00:00
- first_response_at: _(empty — still unanswered)_
- Computed deadline: 2026-09-19T10:15:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 2h
- Clock elapsed: 2h
- Hours overdue: 1.75h
- Why it qualifies: Response clock stopped at as_of (still unanswered) after the P1 response deadline (0.25h from created_at). Elapsed 2.0h, overdue 1.75h.

### resolve_sla_breach:TCK-1003:SLA-RESOLVE-P1
- Ticket: `TCK-1003`
- Rule: `SLA-RESOLVE-P1`
- Type: resolve_sla_breach
- Priority: P1
- Status: resolved
- Customer id (from CSV): `CUST-A`
- Assigned to (from CSV): `alice`
- created_at: 2026-09-18T20:00:00+00:00
- first_response_at: 2026-09-18T20:10:00+00:00
- resolved_at: 2026-09-19T01:00:00+00:00
- Computed deadline: 2026-09-19T00:00:00+00:00
- Clock stop: 2026-09-19T01:00:00+00:00
- Age at as_of: 16h
- Clock elapsed: 5h
- Hours overdue: 1h
- Why it qualifies: Resolve clock stopped at resolved_at after the P1 resolve deadline (4.0h from created_at). Elapsed 5.0h, overdue 1.0h.

### resolve_sla_breach:TCK-1004:SLA-RESOLVE-P3
- Ticket: `TCK-1004`
- Rule: `SLA-RESOLVE-P3`
- Type: resolve_sla_breach
- Priority: P3
- Status: open
- Customer id (from CSV): `CUST-C`
- Assigned to (from CSV): `cara`
- created_at: 2026-09-16T12:00:00+00:00
- first_response_at: 2026-09-16T14:00:00+00:00
- Computed deadline: 2026-09-17T12:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 72h
- Clock elapsed: 72h
- Hours overdue: 48h
- Why it qualifies: Resolve clock stopped at as_of (still open) after the P3 resolve deadline (24.0h from created_at). Elapsed 72.0h, overdue 48.0h.

### resolve_sla_breach:TCK-1009:SLA-RESOLVE-P2
- Ticket: `TCK-1009`
- Rule: `SLA-RESOLVE-P2`
- Type: resolve_sla_breach
- Priority: P2
- Status: waiting_customer
- Customer id (from CSV): `CUST-C`
- Assigned to (from CSV): `cara`
- created_at: 2026-09-18T10:00:00+00:00
- first_response_at: 2026-09-18T10:20:00+00:00
- Computed deadline: 2026-09-18T18:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 26h
- Clock elapsed: 26h
- Hours overdue: 18h
- Why it qualifies: Resolve clock stopped at as_of (still open) after the P2 resolve deadline (8.0h from created_at). Elapsed 26.0h, overdue 18.0h. waiting_customer does not pause the resolve clock under SLA catalog v1.

### response_sla_breach:TCK-1014:SLA-RESPONSE-P1
- Ticket: `TCK-1014`
- Rule: `SLA-RESPONSE-P1`
- Type: response_sla_breach
- Priority: P1
- Status: resolved
- Customer id (from CSV): `CUST-A`
- Assigned to (from CSV): `alice`
- created_at: 2026-09-19T06:00:00+00:00
- first_response_at: 2026-09-19T07:00:00+00:00
- resolved_at: 2026-09-19T09:00:00+00:00
- Computed deadline: 2026-09-19T06:15:00+00:00
- Clock stop: 2026-09-19T07:00:00+00:00
- Age at as_of: 6h
- Clock elapsed: 1h
- Hours overdue: 0.75h
- Why it qualifies: Response clock stopped at first_response_at after the P1 response deadline (0.25h from created_at). Elapsed 1.0h, overdue 0.75h.

### resolve_sla_breach:TCK-1017:SLA-RESOLVE-P2
- Ticket: `TCK-1017`
- Rule: `SLA-RESOLVE-P2`
- Type: resolve_sla_breach
- Priority: P2
- Status: waiting_customer
- Customer id (from CSV): `CUST-A`
- Assigned to (from CSV): `alice`
- created_at: 2026-09-18T12:00:00+00:00
- first_response_at: 2026-09-18T12:20:00+00:00
- Computed deadline: 2026-09-18T20:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 24h
- Clock elapsed: 24h
- Hours overdue: 16h
- Why it qualifies: Resolve clock stopped at as_of (still open) after the P2 resolve deadline (8.0h from created_at). Elapsed 24.0h, overdue 16.0h. waiting_customer does not pause the resolve clock under SLA catalog v1.

### response_sla_breach:TCK-1021:SLA-RESPONSE-P1
- Ticket: `TCK-1021`
- Rule: `SLA-RESPONSE-P1`
- Type: response_sla_breach
- Priority: P1
- Status: open
- Customer id (from CSV): `CUST-C`
- created_at: 2026-09-19T04:00:00+00:00
- first_response_at: _(empty — still unanswered)_
- Computed deadline: 2026-09-19T04:15:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 8h
- Clock elapsed: 8h
- Hours overdue: 7.75h
- Why it qualifies: Response clock stopped at as_of (still unanswered) after the P1 response deadline (0.25h from created_at). Elapsed 8.0h, overdue 7.75h.

### resolve_sla_breach:TCK-1021:SLA-RESOLVE-P1
- Ticket: `TCK-1021`
- Rule: `SLA-RESOLVE-P1`
- Type: resolve_sla_breach
- Priority: P1
- Status: open
- Customer id (from CSV): `CUST-C`
- created_at: 2026-09-19T04:00:00+00:00
- Computed deadline: 2026-09-19T08:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 8h
- Clock elapsed: 8h
- Hours overdue: 4h
- Why it qualifies: Resolve clock stopped at as_of (still open) after the P1 resolve deadline (4.0h from created_at). Elapsed 8.0h, overdue 4.0h.

## Approaching deadlines

### approaching_response:TCK-1005:SLA-RESPONSE-P2
- Ticket: `TCK-1005`
- Rule: `SLA-RESPONSE-P2`
- Type: approaching_response
- Priority: P2
- Status: open
- Customer id (from CSV): `CUST-B`
- Assigned to (from CSV): `bob`
- created_at: 2026-09-19T11:15:00+00:00
- first_response_at: _(empty — still unanswered)_
- Computed deadline: 2026-09-19T12:15:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 0.75h
- Clock elapsed: 0.75h
- Hours remaining: 0.25h
- Why it qualifies: Still unanswered and 0.25h remain before the P2 response deadline (1.0h window).

### approaching_resolve:TCK-1010:SLA-RESOLVE-P3
- Ticket: `TCK-1010`
- Rule: `SLA-RESOLVE-P3`
- Type: approaching_resolve
- Priority: P3
- Status: in_progress
- Customer id (from CSV): `CUST-D`
- Assigned to (from CSV): `dana`
- created_at: 2026-09-18T14:00:00+00:00
- first_response_at: 2026-09-18T16:00:00+00:00
- Computed deadline: 2026-09-19T14:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 22h
- Clock elapsed: 22h
- Hours remaining: 2h
- Why it qualifies: Still open and 2.0h remain before the P3 resolve deadline (24.0h window).

### approaching_resolve:TCK-1015:SLA-RESOLVE-P1
- Ticket: `TCK-1015`
- Rule: `SLA-RESOLVE-P1`
- Type: approaching_resolve
- Priority: P1
- Status: in_progress
- Customer id (from CSV): `CUST-C`
- Assigned to (from CSV): `cara`
- created_at: 2026-09-19T08:30:00+00:00
- first_response_at: 2026-09-19T08:35:00+00:00
- Computed deadline: 2026-09-19T12:30:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 3.5h
- Clock elapsed: 3.5h
- Hours remaining: 0.5h
- Why it qualifies: Still open and 0.5h remain before the P1 resolve deadline (4.0h window).

## Ageing backlog

### ageing_backlog:TCK-1004:AGEING-BACKLOG-48H
- Ticket: `TCK-1004`
- Rule: `AGEING-BACKLOG-48H`
- Type: ageing_backlog
- Priority: P3
- Status: open
- Customer id (from CSV): `CUST-C`
- Assigned to (from CSV): `cara`
- created_at: 2026-09-16T12:00:00+00:00
- first_response_at: 2026-09-16T14:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 72h
- Clock elapsed: 72h
- Why it qualifies: Ticket is still open and age 72.0h meets or exceeds the 48.0h ageing-backlog threshold. This rule is independent of priority SLA clocks.

### ageing_backlog:TCK-1006:AGEING-BACKLOG-48H
- Ticket: `TCK-1006`
- Rule: `AGEING-BACKLOG-48H`
- Type: ageing_backlog
- Priority: P4
- Status: open
- Customer id (from CSV): `CUST-D`
- Assigned to (from CSV): `dana`
- created_at: 2026-09-17T12:00:00+00:00
- first_response_at: 2026-09-17T16:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 48h
- Clock elapsed: 48h
- Why it qualifies: Ticket is still open and age 48.0h meets or exceeds the 48.0h ageing-backlog threshold. This rule is independent of priority SLA clocks.

## Rows requiring attention

### attention:TCK-1001
- Ticket: `TCK-1001`
- Rule: `ATTENTION-OPEN-BREACH`
- Type: attention
- Priority: P1
- Status: open
- Customer id (from CSV): `CUST-A`
- Assigned to (from CSV): `alice`
- created_at: 2026-09-19T10:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 2h
- Attention reasons: `ATTENTION-OPEN-BREACH`
- Cites evidence: `response_sla_breach:TCK-1001:SLA-RESPONSE-P1`
- Why it qualifies: open ticket has at least one SLA breach.

### attention:TCK-1003
- Ticket: `TCK-1003`
- Rule: `ATTENTION-P1P2-CLOSED-BREACH`
- Type: attention
- Priority: P1
- Status: resolved
- Customer id (from CSV): `CUST-A`
- Assigned to (from CSV): `alice`
- created_at: 2026-09-18T20:00:00+00:00
- first_response_at: 2026-09-18T20:10:00+00:00
- resolved_at: 2026-09-19T01:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 16h
- Attention reasons: `ATTENTION-P1P2-CLOSED-BREACH`
- Cites evidence: `resolve_sla_breach:TCK-1003:SLA-RESOLVE-P1`
- Why it qualifies: closed/resolved P1/P2 ticket breached an SLA (historical).

### attention:TCK-1004
- Ticket: `TCK-1004`
- Rule: `ATTENTION-OPEN-BREACH`
- Type: attention
- Priority: P3
- Status: open
- Customer id (from CSV): `CUST-C`
- Assigned to (from CSV): `cara`
- created_at: 2026-09-16T12:00:00+00:00
- first_response_at: 2026-09-16T14:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 72h
- Attention reasons: `ATTENTION-OPEN-BREACH`
- Cites evidence: `resolve_sla_breach:TCK-1004:SLA-RESOLVE-P3`
- Why it qualifies: open ticket has at least one SLA breach.

### attention:TCK-1005
- Ticket: `TCK-1005`
- Rule: `ATTENTION-APPROACHING-P1P2`
- Type: attention
- Priority: P2
- Status: open
- Customer id (from CSV): `CUST-B`
- Assigned to (from CSV): `bob`
- created_at: 2026-09-19T11:15:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 0.75h
- Attention reasons: `ATTENTION-APPROACHING-P1P2`
- Cites evidence: `approaching_response:TCK-1005:SLA-RESPONSE-P2`
- Why it qualifies: P1/P2 deadline is approaching.

### attention:TCK-1007
- Ticket: `TCK-1007`
- Rule: `ATTENTION-DATA-QUALITY`
- Type: attention
- Priority: Urgent
- Status: open
- Customer id (from CSV): `CUST-A`
- Assigned to (from CSV): `alice`
- created_at: 2026-09-19T08:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 4h
- Attention reasons: `ATTENTION-DATA-QUALITY`
- Cites evidence: `dq:TCK-1007:DQ-UNKNOWN-PRIORITY`
- Why it qualifies: open ticket has data-quality flags that block SLA calculation.

### attention:TCK-1008
- Ticket: `TCK-1008`
- Rule: `ATTENTION-DATA-QUALITY`
- Type: attention
- Priority: P1
- Status: open
- Customer id (from CSV): `CUST-B`
- Assigned to (from CSV): `bob`
- first_response_at: 2026-09-19T11:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Attention reasons: `ATTENTION-DATA-QUALITY`
- Cites evidence: `dq:TCK-1008:DQ-MISSING-CREATED-AT`
- Why it qualifies: open ticket has data-quality flags that block SLA calculation.

### attention:TCK-1009
- Ticket: `TCK-1009`
- Rule: `ATTENTION-OPEN-BREACH`
- Type: attention
- Priority: P2
- Status: waiting_customer
- Customer id (from CSV): `CUST-C`
- Assigned to (from CSV): `cara`
- created_at: 2026-09-18T10:00:00+00:00
- first_response_at: 2026-09-18T10:20:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 26h
- Attention reasons: `ATTENTION-OPEN-BREACH`, `ATTENTION-WAITING-CUSTOMER`
- Cites evidence: `resolve_sla_breach:TCK-1009:SLA-RESOLVE-P2`
- Why it qualifies: open ticket has at least one SLA breach; waiting_customer for 25.0h (threshold 24.0h from status_updated_at).

### attention:TCK-1012
- Ticket: `TCK-1012`
- Rule: `ATTENTION-UNASSIGNED`
- Type: attention
- Priority: P3
- Status: open
- Customer id (from CSV): `CUST-E`
- created_at: 2026-09-19T09:00:00+00:00
- first_response_at: 2026-09-19T11:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 3h
- Attention reasons: `ATTENTION-UNASSIGNED`
- Why it qualifies: open ticket has an empty assigned_to field.

### attention:TCK-1013
- Ticket: `TCK-1013`
- Rule: `ATTENTION-DATA-QUALITY`
- Type: attention
- Priority: P2
- Status: open
- Customer id (from CSV): `CUST-B`
- Assigned to (from CSV): `bob`
- Clock stop: 2026-09-19T12:00:00+00:00
- Attention reasons: `ATTENTION-DATA-QUALITY`
- Cites evidence: `dq:TCK-1013:DQ-AMBIGUOUS-TIMESTAMP`
- Why it qualifies: open ticket has data-quality flags that block SLA calculation.

### attention:TCK-1014
- Ticket: `TCK-1014`
- Rule: `ATTENTION-P1P2-CLOSED-BREACH`
- Type: attention
- Priority: P1
- Status: resolved
- Customer id (from CSV): `CUST-A`
- Assigned to (from CSV): `alice`
- created_at: 2026-09-19T06:00:00+00:00
- first_response_at: 2026-09-19T07:00:00+00:00
- resolved_at: 2026-09-19T09:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 6h
- Attention reasons: `ATTENTION-P1P2-CLOSED-BREACH`
- Cites evidence: `response_sla_breach:TCK-1014:SLA-RESPONSE-P1`
- Why it qualifies: closed/resolved P1/P2 ticket breached an SLA (historical).

### attention:TCK-1015
- Ticket: `TCK-1015`
- Rule: `ATTENTION-APPROACHING-P1P2`
- Type: attention
- Priority: P1
- Status: in_progress
- Customer id (from CSV): `CUST-C`
- Assigned to (from CSV): `cara`
- created_at: 2026-09-19T08:30:00+00:00
- first_response_at: 2026-09-19T08:35:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 3.5h
- Attention reasons: `ATTENTION-APPROACHING-P1P2`
- Cites evidence: `approaching_resolve:TCK-1015:SLA-RESOLVE-P1`
- Why it qualifies: P1/P2 deadline is approaching.

### attention:TCK-1017
- Ticket: `TCK-1017`
- Rule: `ATTENTION-OPEN-BREACH`
- Type: attention
- Priority: P2
- Status: waiting_customer
- Customer id (from CSV): `CUST-A`
- Assigned to (from CSV): `alice`
- created_at: 2026-09-18T12:00:00+00:00
- first_response_at: 2026-09-18T12:20:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 24h
- Attention reasons: `ATTENTION-OPEN-BREACH`
- Cites evidence: `resolve_sla_breach:TCK-1017:SLA-RESOLVE-P2`
- Why it qualifies: open ticket has at least one SLA breach.

### attention:TCK-1019
- Ticket: `TCK-1019`
- Rule: `ATTENTION-DATA-QUALITY`
- Type: attention
- Priority: P2
- Status: open
- Customer id (from CSV): `CUST-B`
- Assigned to (from CSV): `bob`
- created_at: 2026-09-19T09:00:00+00:00
- first_response_at: 2026-09-19T08:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 3h
- Attention reasons: `ATTENTION-DATA-QUALITY`
- Cites evidence: `dq:TCK-1019:DQ-TIMELINE-INCONSISTENT`
- Why it qualifies: open ticket has data-quality flags that block SLA calculation.

### attention:TCK-1020
- Ticket: `TCK-1020`
- Rule: `ATTENTION-DATA-QUALITY`
- Type: attention
- Priority: P4
- Status: open
- Customer id (from CSV): `CUST-E`
- Assigned to (from CSV): `erin`
- created_at: 2026-09-15T12:00:00+00:00
- first_response_at: 2026-09-15T13:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 96h
- Attention reasons: `ATTENTION-DATA-QUALITY`
- Cites evidence: `dq:TCK-1020:DQ-DUPLICATE-TICKET-ID:row-21`, `dq:TCK-1020:DQ-DUPLICATE-TICKET-ID:row-22`
- Why it qualifies: open ticket has data-quality flags that block SLA calculation.

### attention:TCK-1020:row-22
- Ticket: `TCK-1020`
- Rule: `ATTENTION-DATA-QUALITY`
- Type: attention
- Priority: P4
- Status: open
- Customer id (from CSV): `CUST-E`
- Assigned to (from CSV): `erin`
- created_at: 2026-09-19T10:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 2h
- Attention reasons: `ATTENTION-DATA-QUALITY`
- Cites evidence: `dq:TCK-1020:DQ-DUPLICATE-TICKET-ID:row-21`, `dq:TCK-1020:DQ-DUPLICATE-TICKET-ID:row-22`
- Why it qualifies: open ticket has data-quality flags that block SLA calculation.

### attention:TCK-1021
- Ticket: `TCK-1021`
- Rule: `ATTENTION-OPEN-BREACH`
- Type: attention
- Priority: P1
- Status: open
- Customer id (from CSV): `CUST-C`
- created_at: 2026-09-19T04:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 8h
- Attention reasons: `ATTENTION-OPEN-BREACH`, `ATTENTION-UNASSIGNED`
- Cites evidence: `response_sla_breach:TCK-1021:SLA-RESPONSE-P1`, `resolve_sla_breach:TCK-1021:SLA-RESOLVE-P1`
- Why it qualifies: open ticket has at least one SLA breach; open ticket has an empty assigned_to field.

### attention:ROW-24
- Ticket: `ROW-24`
- Rule: `ATTENTION-DATA-QUALITY`
- Type: attention
- Priority: P3
- Status: open
- Customer id (from CSV): `CUST-D`
- Assigned to (from CSV): `dana`
- created_at: 2026-09-19T10:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 2h
- Attention reasons: `ATTENTION-DATA-QUALITY`
- Cites evidence: `dq:ROW-24:DQ-MISSING-TICKET-ID`
- Why it qualifies: open ticket has data-quality flags that block SLA calculation.

### attention:TCK-1024
- Ticket: `TCK-1024`
- Rule: `ATTENTION-DATA-QUALITY`
- Type: attention
- Priority: P5
- Status: open
- Customer id (from CSV): `CUST-C`
- Assigned to (from CSV): `cara`
- created_at: 2026-09-19T06:00:00+00:00
- Clock stop: 2026-09-19T12:00:00+00:00
- Age at as_of: 6h
- Attention reasons: `ATTENTION-DATA-QUALITY`
- Cites evidence: `dq:TCK-1024:DQ-UNKNOWN-PRIORITY`
- Why it qualifies: open ticket has data-quality flags that block SLA calculation.

## Data quality (missing or ambiguous — not guessed)

### dq:TCK-1007:DQ-UNKNOWN-PRIORITY
- Ticket: `TCK-1007`
- Rule: `DQ-UNKNOWN-PRIORITY`
- Type: data_quality
- Priority: Urgent
- Status: open
- Customer id (from CSV): `CUST-A`
- Assigned to (from CSV): `alice`
- created_at: 2026-09-19T08:00:00+00:00
- Why it qualifies: priority='Urgent' is not in the documented catalog (P1/Critical, P2/High, P3/Medium, P4/Low). SLA is not guessed.

### dq:TCK-1008:DQ-MISSING-CREATED-AT
- Ticket: `TCK-1008`
- Rule: `DQ-MISSING-CREATED-AT`
- Type: data_quality
- Priority: P1
- Status: open
- Customer id (from CSV): `CUST-B`
- Assigned to (from CSV): `bob`
- first_response_at: 2026-09-19T11:00:00+00:00
- Why it qualifies: created_at is missing; response and resolve clocks cannot start.

### dq:TCK-1013:DQ-AMBIGUOUS-TIMESTAMP
- Ticket: `TCK-1013`
- Rule: `DQ-AMBIGUOUS-TIMESTAMP`
- Type: data_quality
- Priority: P2
- Status: open
- Customer id (from CSV): `CUST-B`
- Assigned to (from CSV): `bob`
- Why it qualifies: created_at='yesterday morning' is not a timezone-aware ISO-8601 timestamp (Invalid isoformat string: 'yesterday morning'). SLA clocks that need this field are skipped.

### dq:TCK-1017:DQ-AMBIGUOUS-WAIT-CLOCK
- Ticket: `TCK-1017`
- Rule: `DQ-AMBIGUOUS-WAIT-CLOCK`
- Type: data_quality
- Priority: P2
- Status: waiting_customer
- Customer id (from CSV): `CUST-A`
- Assigned to (from CSV): `alice`
- created_at: 2026-09-18T12:00:00+00:00
- Why it qualifies: status is waiting_customer but status_updated_at is missing; wait-time attention is not guessed from created_at.

### dq:TCK-1018:DQ-MISSING-RESOLVED-AT
- Ticket: `TCK-1018`
- Rule: `DQ-MISSING-RESOLVED-AT`
- Type: data_quality
- Priority: P3
- Status: closed
- Customer id (from CSV): `CUST-D`
- Assigned to (from CSV): `dana`
- created_at: 2026-09-19T07:00:00+00:00
- first_response_at: 2026-09-19T07:10:00+00:00
- Why it qualifies: status is resolved/closed but resolved_at is missing; resolve SLA is not guessed from as_of.

### dq:TCK-1019:DQ-TIMELINE-INCONSISTENT
- Ticket: `TCK-1019`
- Rule: `DQ-TIMELINE-INCONSISTENT`
- Type: data_quality
- Priority: P2
- Status: open
- Customer id (from CSV): `CUST-B`
- Assigned to (from CSV): `bob`
- created_at: 2026-09-19T09:00:00+00:00
- first_response_at: 2026-09-19T08:00:00+00:00
- Why it qualifies: first_response_at is earlier than created_at; response SLA is skipped.

### dq:TCK-1020:DQ-DUPLICATE-TICKET-ID:row-21
- Ticket: `TCK-1020`
- Rule: `DQ-DUPLICATE-TICKET-ID`
- Type: data_quality
- Priority: Low
- Status: open
- Customer id (from CSV): `CUST-E`
- Assigned to (from CSV): `erin`
- Why it qualifies: ticket_id appears more than once; SLA is skipped because the canonical row cannot be chosen without guessing.

### dq:TCK-1020:DQ-DUPLICATE-TICKET-ID:row-22
- Ticket: `TCK-1020`
- Rule: `DQ-DUPLICATE-TICKET-ID`
- Type: data_quality
- Priority: P4
- Status: open
- Customer id (from CSV): `CUST-E`
- Assigned to (from CSV): `erin`
- Why it qualifies: ticket_id appears more than once; SLA is skipped because the canonical row cannot be chosen without guessing.

### dq:ROW-24:DQ-MISSING-TICKET-ID
- Ticket: `ROW-24`
- Rule: `DQ-MISSING-TICKET-ID`
- Type: data_quality
- Priority: P3
- Status: open
- Customer id (from CSV): `CUST-D`
- Assigned to (from CSV): `dana`
- Why it qualifies: ticket_id is empty; row is not SLA-eligible and is labeled by row number only.

### dq:TCK-1024:DQ-UNKNOWN-PRIORITY
- Ticket: `TCK-1024`
- Rule: `DQ-UNKNOWN-PRIORITY`
- Type: data_quality
- Priority: P5
- Status: open
- Customer id (from CSV): `CUST-C`
- Assigned to (from CSV): `cara`
- created_at: 2026-09-19T06:00:00+00:00
- Why it qualifies: priority='P5' is not in the documented catalog (P1/Critical, P2/High, P3/Medium, P4/Low). SLA is not guessed.

## AI recommended actions

_AI section omitted (optional path not enabled, or no API key). The Phase A numbers and evidence above are complete without a model._

---

This brief does not invent customer impact, financial loss, or unstated outcomes. Customer identifiers are copied from the source CSV when present.
