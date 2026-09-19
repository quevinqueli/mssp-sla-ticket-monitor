"""Pure SLA / backlog / attention calculations. All findings include evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from mssp_sla.models import Finding, ParsedTicket
from mssp_sla.sla_rules import (
    AGEING_BACKLOG_HOURS,
    RULE_AGEING_BACKLOG,
    RULE_ATTENTION_APPROACHING_P1P2,
    RULE_ATTENTION_CLOSED_P1P2_BREACH,
    RULE_ATTENTION_DATA_QUALITY,
    RULE_ATTENTION_OPEN_BREACH,
    RULE_ATTENTION_UNASSIGNED,
    RULE_ATTENTION_WAITING_CUSTOMER,
    WAITING_CUSTOMER_ATTENTION_HOURS,
    is_approaching,
    sla_for_priority,
)
from mssp_sla.timeutil import add_hours, hours_between, iso


@dataclass(frozen=True)
class SlaClock:
    kind: str  # "response" or "resolve"
    rule_id: str
    sla_hours: float
    start: datetime
    stop: datetime
    deadline: datetime
    elapsed_hours: float
    remaining_hours: float
    overdue_hours: float
    breached: bool
    still_ticking: bool


def _age_hours(ticket: ParsedTicket, as_of: datetime) -> float | None:
    if ticket.created_at is None:
        return None
    return hours_between(ticket.created_at, as_of)


def _base_finding(ticket: ParsedTicket, as_of: datetime, **kwargs) -> Finding:
    return Finding(
        created_at=iso(ticket.created_at),
        first_response_at=iso(ticket.first_response_at),
        resolved_at=iso(ticket.resolved_at),
        status_updated_at=iso(ticket.status_updated_at),
        status=ticket.status_normalized or ticket.status_raw or None,
        priority=ticket.priority_normalized or ticket.priority_raw or None,
        customer_id=ticket.customer_id or None,
        assigned_to=ticket.assigned_to or None,
        computed_age_hours=_age_hours(ticket, as_of),
        **kwargs,
    )


def response_clock(ticket: ParsedTicket, as_of: datetime) -> SlaClock | None:
    if not ticket.response_sla_eligible or ticket.created_at is None:
        return None
    spec = sla_for_priority(ticket.priority_normalized)  # type: ignore[arg-type]
    still_ticking = ticket.first_response_at is None
    stop = ticket.first_response_at or as_of
    deadline = add_hours(ticket.created_at, spec.response_hours)
    elapsed = hours_between(ticket.created_at, stop)
    if stop > deadline:
        remaining = -hours_between(deadline, stop)
        overdue = hours_between(deadline, stop)
    elif stop == deadline:
        remaining = 0.0
        overdue = 0.0
    else:
        remaining = hours_between(stop, deadline)
        overdue = 0.0
    return SlaClock(
        kind="response",
        rule_id=spec.response_rule_id,
        sla_hours=spec.response_hours,
        start=ticket.created_at,
        stop=stop,
        deadline=deadline,
        elapsed_hours=elapsed,
        remaining_hours=remaining,
        overdue_hours=overdue,
        breached=stop > deadline,
        still_ticking=still_ticking,
    )


def resolve_clock(ticket: ParsedTicket, as_of: datetime) -> SlaClock | None:
    if not ticket.resolve_sla_eligible or ticket.created_at is None:
        return None
    spec = sla_for_priority(ticket.priority_normalized)  # type: ignore[arg-type]
    # waiting_customer does NOT pause the resolve clock (documented v1 rule).
    still_ticking = ticket.resolved_at is None and ticket.is_open()
    if ticket.resolved_at is not None:
        stop = ticket.resolved_at
    elif ticket.is_open():
        stop = as_of
    else:
        # Closed without resolved_at is not resolve-eligible (flagged at parse).
        return None
    deadline = add_hours(ticket.created_at, spec.resolve_hours)
    elapsed = hours_between(ticket.created_at, stop)
    if stop > deadline:
        remaining = -hours_between(deadline, stop)
        overdue = hours_between(deadline, stop)
    elif stop == deadline:
        remaining = 0.0
        overdue = 0.0
    else:
        remaining = hours_between(stop, deadline)
        overdue = 0.0
    return SlaClock(
        kind="resolve",
        rule_id=spec.resolve_rule_id,
        sla_hours=spec.resolve_hours,
        start=ticket.created_at,
        stop=stop,
        deadline=deadline,
        elapsed_hours=elapsed,
        remaining_hours=remaining,
        overdue_hours=overdue,
        breached=stop > deadline,
        still_ticking=still_ticking,
    )


def _clock_finding(
    ticket: ParsedTicket,
    as_of: datetime,
    clock: SlaClock,
    finding_type: str,
    why: str,
) -> Finding:
    return _base_finding(
        ticket,
        as_of,
        evidence_id=f"{finding_type}:{ticket.ticket_id}:{clock.rule_id}",
        ticket_id=ticket.ticket_id,
        finding_type=finding_type,
        rule_id=clock.rule_id,
        why_it_qualifies=why,
        computed_deadline=iso(clock.deadline),
        clock_elapsed_hours=clock.elapsed_hours,
        hours_overdue=clock.overdue_hours if clock.breached else 0.0,
        hours_remaining=clock.remaining_hours if not clock.breached else 0.0,
        clock_stop_at=iso(clock.stop),
    )


def compute_breached_slas(tickets: list[ParsedTicket], as_of: datetime) -> list[Finding]:
    findings: list[Finding] = []
    for ticket in tickets:
        response = response_clock(ticket, as_of)
        if response and response.breached:
            stop_label = (
                "first_response_at"
                if ticket.first_response_at is not None
                else "as_of (still unanswered)"
            )
            findings.append(
                _clock_finding(
                    ticket,
                    as_of,
                    response,
                    "response_sla_breach",
                    (
                        f"Response clock stopped at {stop_label} after the "
                        f"{ticket.priority_normalized} response deadline "
                        f"({response.sla_hours}h from created_at). "
                        f"Elapsed {response.elapsed_hours}h, overdue {response.overdue_hours}h."
                    ),
                )
            )
        resolve = resolve_clock(ticket, as_of)
        if resolve and resolve.breached:
            stop_label = (
                "resolved_at" if ticket.resolved_at is not None else "as_of (still open)"
            )
            pause_note = ""
            if ticket.status_normalized == "waiting_customer":
                pause_note = (
                    " waiting_customer does not pause the resolve clock under SLA catalog v1."
                )
            findings.append(
                _clock_finding(
                    ticket,
                    as_of,
                    resolve,
                    "resolve_sla_breach",
                    (
                        f"Resolve clock stopped at {stop_label} after the "
                        f"{ticket.priority_normalized} resolve deadline "
                        f"({resolve.sla_hours}h from created_at). "
                        f"Elapsed {resolve.elapsed_hours}h, overdue {resolve.overdue_hours}h."
                        f"{pause_note}"
                    ),
                )
            )
    return findings


def compute_approaching_deadlines(tickets: list[ParsedTicket], as_of: datetime) -> list[Finding]:
    findings: list[Finding] = []
    for ticket in tickets:
        response = response_clock(ticket, as_of)
        if (
            response
            and response.still_ticking
            and not response.breached
            and is_approaching(response.remaining_hours, response.sla_hours)
        ):
            findings.append(
                _clock_finding(
                    ticket,
                    as_of,
                    response,
                    "approaching_response",
                    (
                        f"Still unanswered and {response.remaining_hours}h remain before the "
                        f"{ticket.priority_normalized} response deadline "
                        f"({response.sla_hours}h window)."
                    ),
                )
            )
        resolve = resolve_clock(ticket, as_of)
        if (
            resolve
            and resolve.still_ticking
            and not resolve.breached
            and is_approaching(resolve.remaining_hours, resolve.sla_hours)
        ):
            findings.append(
                _clock_finding(
                    ticket,
                    as_of,
                    resolve,
                    "approaching_resolve",
                    (
                        f"Still open and {resolve.remaining_hours}h remain before the "
                        f"{ticket.priority_normalized} resolve deadline "
                        f"({resolve.sla_hours}h window)."
                    ),
                )
            )
    return findings


def compute_ageing_backlog(tickets: list[ParsedTicket], as_of: datetime) -> list[Finding]:
    findings: list[Finding] = []
    for ticket in tickets:
        if not ticket.is_open() or ticket.created_at is None:
            continue
        age = hours_between(ticket.created_at, as_of)
        if age < AGEING_BACKLOG_HOURS:
            continue
        findings.append(
            _base_finding(
                ticket,
                as_of,
                evidence_id=f"ageing_backlog:{ticket.ticket_id}:{RULE_AGEING_BACKLOG}",
                ticket_id=ticket.ticket_id,
                finding_type="ageing_backlog",
                rule_id=RULE_AGEING_BACKLOG,
                why_it_qualifies=(
                    f"Ticket is still open and age {age}h meets or exceeds the "
                    f"{AGEING_BACKLOG_HOURS}h ageing-backlog threshold. "
                    "This rule is independent of priority SLA clocks."
                ),
                computed_deadline=None,
                clock_elapsed_hours=age,
                hours_overdue=round(age - AGEING_BACKLOG_HOURS, 4),
                hours_remaining=None,
                clock_stop_at=iso(as_of),
            )
        )
    return findings


def _waiting_hours(ticket: ParsedTicket, as_of: datetime) -> float | None:
    if ticket.status_normalized != "waiting_customer":
        return None
    if ticket.status_updated_at is None:
        return None
    return hours_between(ticket.status_updated_at, as_of)


def compute_attention_list(
    tickets: list[ParsedTicket],
    as_of: datetime,
    *,
    breached: list[Finding],
    approaching: list[Finding],
    data_quality: list[Finding],
) -> list[Finding]:
    """Unique tickets that match at least one explicit attention rule."""
    breached_by_ticket: dict[str, list[Finding]] = {}
    for finding in breached:
        breached_by_ticket.setdefault(finding.ticket_id, []).append(finding)
    approaching_by_ticket: dict[str, list[Finding]] = {}
    for finding in approaching:
        approaching_by_ticket.setdefault(finding.ticket_id, []).append(finding)
    dq_by_ticket: dict[str, list[Finding]] = {}
    for finding in data_quality:
        dq_by_ticket.setdefault(finding.ticket_id, []).append(finding)

    findings: list[Finding] = []
    for ticket in tickets:
        reasons: list[str] = []
        source_ids: list[str] = []
        notes: list[str] = []

        ticket_breaches = breached_by_ticket.get(ticket.ticket_id, [])
        if ticket.is_open() and ticket_breaches:
            reasons.append(RULE_ATTENTION_OPEN_BREACH)
            source_ids.extend(item.evidence_id for item in ticket_breaches)
            notes.append("open ticket has at least one SLA breach")

        if (
            ticket.is_closed()
            and ticket.priority_normalized in {"P1", "P2"}
            and ticket_breaches
        ):
            reasons.append(RULE_ATTENTION_CLOSED_P1P2_BREACH)
            source_ids.extend(item.evidence_id for item in ticket_breaches)
            notes.append("closed/resolved P1/P2 ticket breached an SLA (historical)")

        ticket_approaching = approaching_by_ticket.get(ticket.ticket_id, [])
        if ticket.priority_normalized in {"P1", "P2"} and ticket_approaching:
            reasons.append(RULE_ATTENTION_APPROACHING_P1P2)
            source_ids.extend(item.evidence_id for item in ticket_approaching)
            notes.append("P1/P2 deadline is approaching")

        if ticket.is_open() and not ticket.assigned_to:
            reasons.append(RULE_ATTENTION_UNASSIGNED)
            notes.append("open ticket has an empty assigned_to field")

        ticket_dq = [
            item
            for item in dq_by_ticket.get(ticket.ticket_id, [])
            if item.ticket_id != "FILE"
        ]
        blocks_sla = (not ticket.sla_eligible) and bool(ticket_dq)
        if ticket.is_open() and blocks_sla:
            reasons.append(RULE_ATTENTION_DATA_QUALITY)
            source_ids.extend(item.evidence_id for item in ticket_dq)
            notes.append("open ticket has data-quality flags that block SLA calculation")

        waiting = _waiting_hours(ticket, as_of)
        if waiting is not None and waiting >= WAITING_CUSTOMER_ATTENTION_HOURS:
            reasons.append(RULE_ATTENTION_WAITING_CUSTOMER)
            notes.append(
                f"waiting_customer for {waiting}h "
                f"(threshold {WAITING_CUSTOMER_ATTENTION_HOURS}h from status_updated_at)"
            )

        if not reasons:
            continue

        unique_reasons = list(dict.fromkeys(reasons))
        unique_sources = list(dict.fromkeys(source_ids))
        evidence_id = f"attention:{ticket.ticket_id}"
        if any(item.ticket_id == ticket.ticket_id for item in findings):
            evidence_id = f"attention:{ticket.ticket_id}:row-{ticket.row_number}"
        findings.append(
            _base_finding(
                ticket,
                as_of,
                evidence_id=evidence_id,
                ticket_id=ticket.ticket_id,
                finding_type="attention",
                rule_id=unique_reasons[0],
                why_it_qualifies="; ".join(notes) + ".",
                reason_rule_ids=unique_reasons,
                source_evidence_ids=unique_sources,
                clock_stop_at=iso(as_of),
            )
        )
    return findings


def collect_data_quality(
    tickets: list[ParsedTicket],
    file_findings: list[Finding],
) -> list[Finding]:
    findings = list(file_findings)
    for ticket in tickets:
        findings.extend(ticket.flags)
    return findings
