"""Load a ticket CSV and flag missing/ambiguous values. Never fill them in."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from mssp_sla.constants import (
    ALL_COLUMNS,
    CLOSED_STATUSES,
    OPEN_STATUSES,
    REQUIRED_COLUMNS,
)
from mssp_sla.models import Finding, ParsedTicket
from mssp_sla.sla_rules import (
    RULE_DQ_AMBIGUOUS_TIMESTAMP,
    RULE_DQ_AMBIGUOUS_WAIT_CLOCK,
    RULE_DQ_DUPLICATE_TICKET_ID,
    RULE_DQ_MISSING_COLUMN,
    RULE_DQ_MISSING_CREATED_AT,
    RULE_DQ_MISSING_PRIORITY,
    RULE_DQ_MISSING_RESOLVED_AT,
    RULE_DQ_MISSING_STATUS,
    RULE_DQ_MISSING_TICKET_ID,
    RULE_DQ_TIMELINE_INCONSISTENT,
    RULE_DQ_UNKNOWN_PRIORITY,
    RULE_DQ_UNKNOWN_STATUS,
    normalize_priority,
)
from mssp_sla.timeutil import iso, parse_timestamp


def _cell(row: dict[str, str | None], name: str) -> str:
    value = row.get(name)
    if value is None:
        return ""
    return str(value).strip()


def _dq_finding(
    *,
    ticket_id: str,
    rule_id: str,
    why: str,
    row: dict[str, str],
    created_at: str | None = None,
    first_response_at: str | None = None,
    resolved_at: str | None = None,
    status_updated_at: str | None = None,
) -> Finding:
    return Finding(
        evidence_id=f"dq:{ticket_id}:{rule_id}",
        ticket_id=ticket_id,
        finding_type="data_quality",
        rule_id=rule_id,
        why_it_qualifies=why,
        created_at=created_at,
        first_response_at=first_response_at,
        resolved_at=resolved_at,
        status_updated_at=status_updated_at,
        status=_cell(row, "status") or None,
        priority=_cell(row, "priority") or None,
        customer_id=_cell(row, "customer_id") or None,
        assigned_to=_cell(row, "assigned_to") or None,
    )


def parse_row(row: dict[str, str], row_number: int) -> ParsedTicket:
    raw = {key: _cell(row, key) for key in ALL_COLUMNS if key in row or key in ALL_COLUMNS}
    # Preserve extra columns for evidence/debug without treating them as facts we invented.
    for key, value in row.items():
        if key not in raw:
            raw[key] = "" if value is None else str(value).strip()

    ticket_id = _cell(row, "ticket_id")
    display_id = ticket_id if ticket_id else f"ROW-{row_number}"
    flags: list[Finding] = []

    if not ticket_id:
        flags.append(
            _dq_finding(
                ticket_id=display_id,
                rule_id=RULE_DQ_MISSING_TICKET_ID,
                why="ticket_id is empty; row is not SLA-eligible and is labeled by row number only.",
                row=raw,
            )
        )

    created_raw = _cell(row, "created_at")
    first_raw = _cell(row, "first_response_at")
    resolved_raw = _cell(row, "resolved_at")
    status_updated_raw = _cell(row, "status_updated_at")

    created_at = first_response_at = resolved_at = status_updated_at = None
    created_iso = first_iso = resolved_iso = status_updated_iso = None

    for field_name, raw_value, setter in (
        ("created_at", created_raw, "created"),
        ("first_response_at", first_raw, "first"),
        ("resolved_at", resolved_raw, "resolved"),
        ("status_updated_at", status_updated_raw, "status_updated"),
    ):
        if not raw_value:
            continue
        try:
            parsed = parse_timestamp(raw_value)
        except ValueError as exc:
            flags.append(
                _dq_finding(
                    ticket_id=display_id,
                    rule_id=RULE_DQ_AMBIGUOUS_TIMESTAMP,
                    why=(
                        f"{field_name}={raw_value!r} is not a timezone-aware ISO-8601 "
                        f"timestamp ({exc}). SLA clocks that need this field are skipped."
                    ),
                    row=raw,
                )
            )
            continue
        stamp = iso(parsed)
        if field_name == "created_at":
            created_at, created_iso = parsed, stamp
        elif field_name == "first_response_at":
            first_response_at, first_iso = parsed, stamp
        elif field_name == "resolved_at":
            resolved_at, resolved_iso = parsed, stamp
        else:
            status_updated_at, status_updated_iso = parsed, stamp

    if not created_raw:
        flags.append(
            _dq_finding(
                ticket_id=display_id,
                rule_id=RULE_DQ_MISSING_CREATED_AT,
                why="created_at is missing; response and resolve clocks cannot start.",
                row=raw,
                first_response_at=first_iso,
                resolved_at=resolved_iso,
            )
        )

    priority_raw = _cell(row, "priority")
    if not priority_raw:
        flags.append(
            _dq_finding(
                ticket_id=display_id,
                rule_id=RULE_DQ_MISSING_PRIORITY,
                why="priority is missing; no SLA target is applied (not guessed).",
                row=raw,
                created_at=created_iso,
            )
        )
        priority_normalized = None
    else:
        priority_normalized = normalize_priority(priority_raw)
        if priority_normalized is None:
            flags.append(
                _dq_finding(
                    ticket_id=display_id,
                    rule_id=RULE_DQ_UNKNOWN_PRIORITY,
                    why=(
                        f"priority={priority_raw!r} is not in the documented catalog "
                        "(P1/Critical, P2/High, P3/Medium, P4/Low). SLA is not guessed."
                    ),
                    row=raw,
                    created_at=created_iso,
                )
            )

    status_raw = _cell(row, "status")
    status_normalized = status_raw.lower() if status_raw else None
    if not status_raw:
        flags.append(
            _dq_finding(
                ticket_id=display_id,
                rule_id=RULE_DQ_MISSING_STATUS,
                why="status is missing; open vs closed cannot be determined.",
                row=raw,
                created_at=created_iso,
            )
        )
    elif status_normalized not in OPEN_STATUSES | CLOSED_STATUSES:
        flags.append(
            _dq_finding(
                ticket_id=display_id,
                rule_id=RULE_DQ_UNKNOWN_STATUS,
                why=(
                    f"status={status_raw!r} is not in the documented open/closed sets. "
                    "Resolve-clock open/closed behavior is not guessed."
                ),
                row=raw,
                created_at=created_iso,
            )
        )
        status_normalized = None

    # Timeline consistency: never invert or swap timestamps.
    if created_at and first_response_at and first_response_at < created_at:
        flags.append(
            _dq_finding(
                ticket_id=display_id,
                rule_id=RULE_DQ_TIMELINE_INCONSISTENT,
                why="first_response_at is earlier than created_at; response SLA is skipped.",
                row=raw,
                created_at=created_iso,
                first_response_at=first_iso,
                resolved_at=resolved_iso,
            )
        )
    if created_at and resolved_at and resolved_at < created_at:
        flags.append(
            _dq_finding(
                ticket_id=display_id,
                rule_id=RULE_DQ_TIMELINE_INCONSISTENT,
                why="resolved_at is earlier than created_at; resolve SLA is skipped.",
                row=raw,
                created_at=created_iso,
                first_response_at=first_iso,
                resolved_at=resolved_iso,
            )
        )
    if first_response_at and resolved_at and resolved_at < first_response_at:
        flags.append(
            _dq_finding(
                ticket_id=display_id,
                rule_id=RULE_DQ_TIMELINE_INCONSISTENT,
                why="resolved_at is earlier than first_response_at; both SLA clocks are skipped.",
                row=raw,
                created_at=created_iso,
                first_response_at=first_iso,
                resolved_at=resolved_iso,
            )
        )

    if status_normalized in CLOSED_STATUSES and not resolved_at:
        flags.append(
            _dq_finding(
                ticket_id=display_id,
                rule_id=RULE_DQ_MISSING_RESOLVED_AT,
                why=(
                    "status is resolved/closed but resolved_at is missing; "
                    "resolve SLA is not guessed from as_of."
                ),
                row=raw,
                created_at=created_iso,
                first_response_at=first_iso,
            )
        )

    if status_normalized == "waiting_customer" and status_updated_at is None:
        flags.append(
            _dq_finding(
                ticket_id=display_id,
                rule_id=RULE_DQ_AMBIGUOUS_WAIT_CLOCK,
                why=(
                    "status is waiting_customer but status_updated_at is missing; "
                    "wait-time attention is not guessed from created_at."
                ),
                row=raw,
                created_at=created_iso,
            )
        )

    timeline_flag_ids = {flag.rule_id for flag in flags}
    has_timeline_issue = RULE_DQ_TIMELINE_INCONSISTENT in timeline_flag_ids
    has_identity = bool(ticket_id)
    has_priority = priority_normalized is not None
    has_status = status_normalized is not None
    has_created = created_at is not None

    response_ok = (
        has_identity
        and has_created
        and has_priority
        and has_status
        and not has_timeline_issue
        and not any(
            flag.rule_id == RULE_DQ_AMBIGUOUS_TIMESTAMP
            and "created_at=" in flag.why_it_qualifies
            for flag in flags
        )
        and not any(
            flag.rule_id == RULE_DQ_AMBIGUOUS_TIMESTAMP
            and "first_response_at=" in flag.why_it_qualifies
            for flag in flags
        )
    )
    resolve_ok = (
        has_identity
        and has_created
        and has_priority
        and has_status
        and not has_timeline_issue
        and RULE_DQ_MISSING_RESOLVED_AT not in timeline_flag_ids
        and not any(
            flag.rule_id == RULE_DQ_AMBIGUOUS_TIMESTAMP
            and "created_at=" in flag.why_it_qualifies
            for flag in flags
        )
        and not any(
            flag.rule_id == RULE_DQ_AMBIGUOUS_TIMESTAMP
            and "resolved_at=" in flag.why_it_qualifies
            for flag in flags
        )
    )

    ticket = ParsedTicket(
        ticket_id=display_id,
        row_number=row_number,
        raw=raw,
        created_at=created_at,
        first_response_at=first_response_at,
        resolved_at=resolved_at,
        status_updated_at=status_updated_at,
        priority_raw=priority_raw,
        priority_normalized=priority_normalized,
        status_raw=status_raw,
        status_normalized=status_normalized,
        customer_id=_cell(row, "customer_id"),
        assigned_to=_cell(row, "assigned_to"),
        ticket_type=_cell(row, "ticket_type"),
        category=_cell(row, "category"),
        summary=_cell(row, "summary"),
        flags=flags,
        sla_eligible=response_ok or resolve_ok,
        response_sla_eligible=response_ok,
        resolve_sla_eligible=resolve_ok,
    )
    return ticket


def _mark_duplicates(tickets: list[ParsedTicket]) -> None:
    counts = Counter(ticket.ticket_id for ticket in tickets if not ticket.ticket_id.startswith("ROW-"))
    duplicates = {ticket_id for ticket_id, count in counts.items() if count > 1}
    for ticket in tickets:
        if ticket.ticket_id not in duplicates:
            continue
        flag = _dq_finding(
            ticket_id=ticket.ticket_id,
            rule_id=RULE_DQ_DUPLICATE_TICKET_ID,
            why=(
                "ticket_id appears more than once; SLA is skipped because "
                "the canonical row cannot be chosen without guessing."
            ),
            row=ticket.raw,
        )
        # Row number keeps evidence_id unique when the same ticket_id is repeated.
        flag.evidence_id = (
            f"dq:{ticket.ticket_id}:{RULE_DQ_DUPLICATE_TICKET_ID}:row-{ticket.row_number}"
        )
        ticket.flags.append(flag)
        ticket.sla_eligible = False
        ticket.response_sla_eligible = False
        ticket.resolve_sla_eligible = False


def load_tickets(csv_path: str | Path) -> tuple[list[ParsedTicket], list[Finding]]:
    """Parse every data row. Returns tickets plus file-level data-quality findings."""
    path = Path(csv_path)
    file_findings: list[Finding] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        headers = [name.strip() for name in reader.fieldnames]
        missing = [name for name in REQUIRED_COLUMNS if name not in headers]
        for name in missing:
            file_findings.append(
                Finding(
                    evidence_id=f"dq:FILE:{RULE_DQ_MISSING_COLUMN}:{name}",
                    ticket_id="FILE",
                    finding_type="data_quality",
                    rule_id=RULE_DQ_MISSING_COLUMN,
                    why_it_qualifies=f"Required column {name!r} is missing from the CSV header.",
                )
            )

        tickets: list[ParsedTicket] = []
        for index, row in enumerate(reader, start=2):
            if row is None:
                continue
            if all(not (value or "").strip() for value in row.values()):
                continue
            tickets.append(parse_row(row, index))

    _mark_duplicates(tickets)
    return tickets, file_findings
