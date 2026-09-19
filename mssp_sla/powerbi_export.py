"""Export a Power BI star schema from Phase A (same clocks as the daily brief).

The coordinating environment cannot open Power BI Desktop. This module is the
reproducible source of truth for the report grain, KPI flags, and expected
measure values. DAX in powerbi/model/ counts the columns written here.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from mssp_sla.compute import (
    resolve_clock,
    response_clock,
)
from mssp_sla.models import Finding, MetricsReport, ParsedTicket
from mssp_sla.pipeline import build_report, display_source_path
from mssp_sla.sla_rules import (
    AGEING_BACKLOG_HOURS,
    SLA_CATALOG_VERSION,
    WAITING_CUSTOMER_ATTENTION_HOURS,
    is_approaching,
)
from mssp_sla.timeutil import hours_between, iso

SNAPSHOT_ID = "demo-2026-09-19T12-00-00Z"
DATA_DISCLAIMER = "Synthetic demonstration data"

# Mutually exclusive primary reason for the action table (first match wins).
REASON_BREACHED_OPEN = "BREACHED_OPEN"
REASON_BREACHED_CLOSED = "BREACHED_CLOSED"
REASON_APPROACHING = "APPROACHING"
REASON_AGEING = "AGEING"
REASON_WAITING = "WAITING"
REASON_UNASSIGNED = "UNASSIGNED"
REASON_DATA_QUALITY = "DATA_QUALITY"
REASON_NONE = "NONE"

REASON_LABELS = {
    REASON_BREACHED_OPEN: "SLA breached (open)",
    REASON_BREACHED_CLOSED: "SLA breached (closed P1/P2)",
    REASON_APPROACHING: "Approaching deadline",
    REASON_AGEING: "Ageing backlog",
    REASON_WAITING: "Waiting on customer",
    REASON_UNASSIGNED: "Unassigned",
    REASON_DATA_QUALITY: "Data quality",
    REASON_NONE: "(none)",
}

REASON_SORT = {
    REASON_BREACHED_OPEN: 1,
    REASON_BREACHED_CLOSED: 2,
    REASON_APPROACHING: 3,
    REASON_AGEING: 4,
    REASON_WAITING: 5,
    REASON_UNASSIGNED: 6,
    REASON_DATA_QUALITY: 7,
    REASON_NONE: 99,
}

REASON_COLOR = {
    REASON_BREACHED_OPEN: "#B42318",
    REASON_BREACHED_CLOSED: "#B42318",
    REASON_APPROACHING: "#B54708",
    REASON_AGEING: "#175CD3",
    REASON_WAITING: "#B54708",
    REASON_UNASSIGNED: "#344054",
    REASON_DATA_QUALITY: "#667085",
    REASON_NONE: "#D0D5DD",
}

PRIORITY_SORT = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
OPEN_GROUP = "Open"
CLOSED_GROUP = "Closed"
UNKNOWN_GROUP = "Unknown"

_ROW_IN_EVIDENCE = re.compile(r":row-(\d+)$")


def ticket_row_key(ticket: ParsedTicket) -> str:
    return f"{ticket.row_number}:{ticket.ticket_id}"


def _flag(value: bool) -> int:
    return 1 if value else 0


def _num(value: float | None) -> str:
    if value is None:
        return ""
    text = f"{round(float(value), 4):.4f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _text(value: str | None) -> str:
    return "" if value is None else value


def _priority_key(ticket: ParsedTicket) -> str:
    return ticket.priority_normalized or "UNKNOWN"


def _status_key(ticket: ParsedTicket) -> str:
    return ticket.status_normalized or "UNKNOWN"


def _client_key(ticket: ParsedTicket) -> str:
    return ticket.customer_id or "(blank)"


def _status_group(status_normalized: str | None) -> str:
    if status_normalized is None:
        return UNKNOWN_GROUP
    if status_normalized in {"resolved", "closed"}:
        return CLOSED_GROUP
    if status_normalized in {
        "open",
        "in_progress",
        "waiting_customer",
        "pending",
        "investigating",
    }:
        return OPEN_GROUP
    return UNKNOWN_GROUP


def _index_attention(report: MetricsReport) -> dict[str, list[Finding]]:
    by_ticket: dict[str, list[Finding]] = {}
    for finding in report.attention_list:
        by_ticket.setdefault(finding.ticket_id, []).append(finding)
    return by_ticket


def _match_ticket(
    finding: Finding,
    tickets: list[ParsedTicket],
) -> ParsedTicket | None:
    match = _ROW_IN_EVIDENCE.search(finding.evidence_id)
    if match:
        row_number = int(match.group(1))
        for ticket in tickets:
            if ticket.row_number == row_number:
                return ticket
    matches = [ticket for ticket in tickets if ticket.ticket_id == finding.ticket_id]
    if not matches:
        return None
    return matches[0]


def _clock_choice_for_breach(response, resolve):
    """Prefer the response clock when both are breached (shorter window)."""
    if response is not None and response.breached:
        return response
    if resolve is not None and resolve.breached:
        return resolve
    return None


def _clock_choice_for_approaching(response, resolve):
    if (
        response is not None
        and response.still_ticking
        and not response.breached
        and is_approaching(response.remaining_hours, response.sla_hours)
    ):
        return response
    if (
        resolve is not None
        and resolve.still_ticking
        and not resolve.breached
        and is_approaching(resolve.remaining_hours, resolve.sla_hours)
    ):
        return resolve
    return None


def _ageing_hours(ticket: ParsedTicket, as_of: datetime) -> float | None:
    if not ticket.is_open() or ticket.created_at is None:
        return None
    age = hours_between(ticket.created_at, as_of)
    if age < AGEING_BACKLOG_HOURS:
        return None
    return age


def classify_ticket(
    ticket: ParsedTicket,
    as_of: datetime,
    *,
    attention_by_ticket: dict[str, list[Finding]],
    ageing_why: str | None,
    approaching_why: str | None,
    breach_why: str | None,
) -> dict[str, Any]:
    """Row-level flags used by DAX. Clocks reuse compute.response/resolve_clock."""
    response = response_clock(ticket, as_of)
    resolve = resolve_clock(ticket, as_of)
    age = hours_between(ticket.created_at, as_of) if ticket.created_at else None
    waiting = None
    if ticket.status_normalized == "waiting_customer" and ticket.status_updated_at:
        waiting = hours_between(ticket.status_updated_at, as_of)

    has_response_breach = bool(response and response.breached)
    has_resolve_breach = bool(resolve and resolve.breached)
    has_any_breach = has_response_breach or has_resolve_breach
    approaching_response = bool(
        response
        and response.still_ticking
        and not response.breached
        and is_approaching(response.remaining_hours, response.sla_hours)
    )
    approaching_resolve = bool(
        resolve
        and resolve.still_ticking
        and not resolve.breached
        and is_approaching(resolve.remaining_hours, resolve.sla_hours)
    )
    has_approaching = approaching_response or approaching_resolve
    is_ageing = _ageing_hours(ticket, as_of) is not None
    is_waiting_attention = waiting is not None and waiting >= WAITING_CUSTOMER_ATTENTION_HOURS
    is_unassigned = ticket.is_open() and not ticket.assigned_to
    is_dq_blocking = ticket.is_open() and (not ticket.sla_eligible) and bool(ticket.flags)
    python_attention = ticket.ticket_id in attention_by_ticket

    # KPI cards: unique rows, mutually exclusive across breached / approaching / ageing.
    kpi_breached = has_any_breach
    kpi_approaching = has_approaching and not has_any_breach
    kpi_ageing = is_ageing and not has_any_breach and not has_approaching

    primary = REASON_NONE
    deadline = None
    overdue = None
    remaining = None
    clock_kind = ""
    why_parts: list[str] = []

    if ticket.is_open() and has_any_breach:
        primary = REASON_BREACHED_OPEN
        clock = _clock_choice_for_breach(response, resolve)
        if clock:
            deadline = iso(clock.deadline)
            overdue = clock.overdue_hours
            remaining = 0.0
            clock_kind = clock.kind
        if breach_why:
            why_parts.append(breach_why)
        if has_response_breach and has_resolve_breach:
            why_parts.append(
                "Both response and resolve clocks are breached; the table "
                "deadline/overdue use the response clock (shorter window)."
            )
    elif ticket.is_closed() and has_any_breach:
        primary = REASON_BREACHED_CLOSED
        clock = _clock_choice_for_breach(response, resolve)
        if clock:
            deadline = iso(clock.deadline)
            overdue = clock.overdue_hours
            remaining = 0.0
            clock_kind = clock.kind
        if breach_why:
            why_parts.append(breach_why)
    elif has_approaching:
        primary = REASON_APPROACHING
        clock = _clock_choice_for_approaching(response, resolve)
        if clock:
            deadline = iso(clock.deadline)
            overdue = 0.0
            remaining = clock.remaining_hours
            clock_kind = clock.kind
        if approaching_why:
            why_parts.append(approaching_why)
    elif is_ageing:
        primary = REASON_AGEING
        overdue = round((age or 0.0) - AGEING_BACKLOG_HOURS, 4)
        remaining = None
        if resolve is not None:
            deadline = iso(resolve.deadline)
            remaining = resolve.remaining_hours if not resolve.breached else 0.0
            clock_kind = "ageing"
        if ageing_why:
            why_parts.append(ageing_why)
        else:
            why_parts.append(
                f"Still open and age {age}h meets or exceeds the "
                f"{AGEING_BACKLOG_HOURS}h ageing-backlog threshold."
            )
    elif is_waiting_attention:
        primary = REASON_WAITING
        overdue = round((waiting or 0.0) - WAITING_CUSTOMER_ATTENTION_HOURS, 4)
        why_parts.append(
            f"waiting_customer for {waiting}h "
            f"(threshold {WAITING_CUSTOMER_ATTENTION_HOURS}h from status_updated_at)."
        )
    elif is_unassigned:
        primary = REASON_UNASSIGNED
        why_parts.append("Open ticket has an empty assigned_to field.")
    elif is_dq_blocking:
        primary = REASON_DATA_QUALITY
        dq_ids = ", ".join(flag.rule_id for flag in ticket.flags)
        why_parts.append(
            "Open ticket has data-quality flags that block SLA calculation"
            + (f" ({dq_ids})." if dq_ids else ".")
        )

    attention_findings = attention_by_ticket.get(ticket.ticket_id, [])
    python_reason_ids: list[str] = []
    for finding in attention_findings:
        for rule_id in finding.reason_rule_ids or [finding.rule_id]:
            if rule_id not in python_reason_ids:
                python_reason_ids.append(rule_id)
        if finding.why_it_qualifies and finding.why_it_qualifies not in why_parts:
            # Prefer Phase A attention prose when present, without duplicating.
            if primary in {REASON_UNASSIGNED, REASON_DATA_QUALITY, REASON_WAITING, REASON_BREACHED_OPEN, REASON_BREACHED_CLOSED}:
                why_parts = [finding.why_it_qualifies]

    in_action_table = primary != REASON_NONE
    exclusive_bucket = ""
    if kpi_breached:
        exclusive_bucket = "breached"
    elif kpi_approaching:
        exclusive_bucket = "approaching"
    elif kpi_ageing:
        exclusive_bucket = "ageing"

    return {
        "ticket_row_key": ticket_row_key(ticket),
        "snapshot_id": SNAPSHOT_ID,
        "row_number": ticket.row_number,
        "ticket_id": ticket.ticket_id,
        "client_key": _client_key(ticket),
        "priority_key": _priority_key(ticket),
        "priority_raw": ticket.priority_raw,
        "priority_display": ticket.priority_normalized
        or (f"{ticket.priority_raw} (unknown)" if ticket.priority_raw else "Unknown"),
        "status_key": _status_key(ticket),
        "status_raw": ticket.status_raw,
        "status_display": ticket.status_normalized or ticket.status_raw or "Unknown",
        "status_group": _status_group(ticket.status_normalized),
        "assigned_to": ticket.assigned_to,
        "ticket_type": ticket.ticket_type,
        "category": ticket.category,
        "summary": ticket.summary,
        "created_at": iso(ticket.created_at) or "",
        "first_response_at": iso(ticket.first_response_at) or "",
        "resolved_at": iso(ticket.resolved_at) or "",
        "status_updated_at": iso(ticket.status_updated_at) or "",
        "sla_eligible": _flag(ticket.sla_eligible),
        "response_sla_eligible": _flag(ticket.response_sla_eligible),
        "resolve_sla_eligible": _flag(ticket.resolve_sla_eligible),
        "is_open": _flag(ticket.is_open()),
        "is_closed": _flag(ticket.is_closed()),
        "age_hours": _num(age),
        "waiting_hours": _num(waiting),
        "response_deadline": iso(response.deadline) if response else "",
        "response_elapsed_hours": _num(response.elapsed_hours if response else None),
        "response_remaining_hours": _num(response.remaining_hours if response else None),
        "response_overdue_hours": _num(response.overdue_hours if response else None),
        "response_breached": _flag(has_response_breach),
        "resolve_deadline": iso(resolve.deadline) if resolve else "",
        "resolve_elapsed_hours": _num(resolve.elapsed_hours if resolve else None),
        "resolve_remaining_hours": _num(resolve.remaining_hours if resolve else None),
        "resolve_overdue_hours": _num(resolve.overdue_hours if resolve else None),
        "resolve_breached": _flag(has_resolve_breach),
        "has_any_breach": _flag(has_any_breach),
        "has_approaching": _flag(has_approaching),
        "approaching_response": _flag(approaching_response),
        "approaching_resolve": _flag(approaching_resolve),
        "is_ageing": _flag(is_ageing),
        "is_waiting_attention": _flag(is_waiting_attention),
        "is_unassigned": _flag(is_unassigned),
        "is_dq_blocking_sla": _flag(is_dq_blocking),
        "is_python_attention": _flag(python_attention),
        "python_reason_rule_ids": "|".join(python_reason_ids),
        "dq_rule_ids": "|".join(flag.rule_id for flag in ticket.flags),
        "kpi_open": _flag(ticket.is_open()),
        "kpi_breached": _flag(kpi_breached),
        "kpi_approaching": _flag(kpi_approaching),
        "kpi_ageing": _flag(kpi_ageing),
        "kpi_ageing_python": _flag(is_ageing),
        "exclusive_kpi_bucket": exclusive_bucket,
        "in_action_table": _flag(in_action_table),
        "primary_reason_key": primary,
        "primary_reason_label": REASON_LABELS[primary],
        "reason_sort": REASON_SORT[primary],
        "deadline": deadline or "",
        "overdue_hours": _num(overdue),
        "remaining_hours": _num(remaining),
        "primary_clock_kind": clock_kind,
        "why_for_attention": " ".join(why_parts).strip(),
        "data_disclaimer": DATA_DISCLAIMER,
    }


def _why_for_ticket(findings: Iterable[Finding]) -> str | None:
    texts = [item.why_it_qualifies for item in findings if item.why_it_qualifies]
    return " ".join(texts) if texts else None


def _load_with_report(
    csv_path: str | Path,
    as_of: datetime,
) -> tuple[list[ParsedTicket], MetricsReport]:
    from mssp_sla.parse import load_tickets

    tickets, _file_findings = load_tickets(csv_path)
    report = build_report(csv_path, as_of)
    return tickets, report


def build_model(
    csv_path: str | Path,
    as_of: datetime,
) -> dict[str, Any]:
    tickets, report = _load_with_report(csv_path, as_of)
    attention_by_ticket = _index_attention(report)

    breach_by_ticket: dict[str, list[Finding]] = {}
    for finding in report.breached_slas:
        breach_by_ticket.setdefault(finding.ticket_id, []).append(finding)
    approaching_by_ticket: dict[str, list[Finding]] = {}
    for finding in report.approaching_deadlines:
        approaching_by_ticket.setdefault(finding.ticket_id, []).append(finding)
    ageing_by_ticket: dict[str, list[Finding]] = {}
    for finding in report.ageing_backlog:
        ageing_by_ticket.setdefault(finding.ticket_id, []).append(finding)

    fact_ticket = [
        classify_ticket(
            ticket,
            as_of,
            attention_by_ticket=attention_by_ticket,
            ageing_why=_why_for_ticket(ageing_by_ticket.get(ticket.ticket_id, [])),
            approaching_why=_why_for_ticket(
                approaching_by_ticket.get(ticket.ticket_id, [])
            ),
            breach_why=_why_for_ticket(breach_by_ticket.get(ticket.ticket_id, [])),
        )
        for ticket in tickets
    ]

    fact_finding = [_finding_row(finding, tickets, as_of) for finding in report.all_findings()]

    clients = sorted({row["client_key"] for row in fact_ticket})
    dim_client = [{"client_key": key, "client_id": key, "client_label": key} for key in clients]

    dim_priority = _dim_priority(tickets)
    dim_status = _dim_status(tickets)
    dim_attention_reason = [
        {
            "reason_key": key,
            "reason_label": REASON_LABELS[key],
            "reason_sort": REASON_SORT[key],
            "status_color": REASON_COLOR[key],
            "is_kpi_bucket": _flag(key in {REASON_BREACHED_OPEN, REASON_BREACHED_CLOSED, REASON_APPROACHING, REASON_AGEING}),
        }
        for key in REASON_SORT
    ]

    dim_snapshot = [
        {
            "snapshot_id": SNAPSHOT_ID,
            "as_of_utc": iso(as_of) or "",
            "as_of_label": "19 Sep 2026 12:00 UTC",
            "data_disclaimer": DATA_DISCLAIMER,
            "sla_catalog_version": SLA_CATALOG_VERSION,
            "source_csv": display_source_path(csv_path),
            "row_count": report.counts["total_tickets"],
            "notes": (
                "Frozen demo snapshot. Trends are omitted: the source is a single "
                "as_of instant, not a history of daily snapshots."
            ),
        }
    ]

    expected = expected_measures(fact_ticket, fact_finding, report)
    return {
        "fact_ticket": fact_ticket,
        "fact_finding": fact_finding,
        "dim_client": dim_client,
        "dim_priority": dim_priority,
        "dim_status": dim_status,
        "dim_attention_reason": dim_attention_reason,
        "dim_snapshot": dim_snapshot,
        "expected_measures": expected,
        "report_counts": dict(report.counts),
        "verification_passed": report.verification.passed,
        "as_of": iso(as_of),
    }


def _finding_row(finding: Finding, tickets: list[ParsedTicket], as_of: datetime) -> dict[str, Any]:
    ticket = _match_ticket(finding, tickets)
    return {
        "evidence_id": finding.evidence_id,
        "snapshot_id": SNAPSHOT_ID,
        "ticket_row_key": ticket_row_key(ticket) if ticket else "",
        "ticket_id": finding.ticket_id,
        "finding_type": finding.finding_type,
        "rule_id": finding.rule_id,
        "client_key": _client_key(ticket) if ticket else "",
        "priority_key": _priority_key(ticket) if ticket else "UNKNOWN",
        "status_key": _status_key(ticket) if ticket else "UNKNOWN",
        "computed_deadline": finding.computed_deadline or "",
        "hours_overdue": _num(finding.hours_overdue),
        "hours_remaining": _num(finding.hours_remaining),
        "clock_elapsed_hours": _num(finding.clock_elapsed_hours),
        "why_it_qualifies": finding.why_it_qualifies,
        "reason_rule_ids": "|".join(finding.reason_rule_ids or []),
        "as_of_utc": iso(as_of) or "",
    }


def _dim_priority(tickets: list[ParsedTicket]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for ticket in tickets:
        key = _priority_key(ticket)
        if key in seen:
            aliases = set(filter(None, seen[key]["aliases"].split("|")))
            if ticket.priority_raw:
                aliases.add(ticket.priority_raw)
            seen[key]["aliases"] = "|".join(sorted(aliases))
            continue
        aliases = {ticket.priority_raw} if ticket.priority_raw else set()
        seen[key] = {
            "priority_key": key,
            "priority_label": ticket.priority_normalized or "Unknown",
            "priority_sort": PRIORITY_SORT.get(ticket.priority_normalized or "", 99),
            "response_hours": { "P1": 0.25, "P2": 1.0, "P3": 4.0, "P4": 8.0 }.get(
                ticket.priority_normalized or "", ""
            ),
            "resolve_hours": { "P1": 4.0, "P2": 8.0, "P3": 24.0, "P4": 72.0 }.get(
                ticket.priority_normalized or "", ""
            ),
            "aliases": "|".join(sorted(aliases)),
            "in_catalog": _flag(ticket.priority_normalized is not None),
        }
    return sorted(seen.values(), key=lambda row: (row["priority_sort"], row["priority_key"]))


def _dim_status(tickets: list[ParsedTicket]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for ticket in tickets:
        key = _status_key(ticket)
        if key in seen:
            continue
        seen[key] = {
            "status_key": key,
            "status_label": ticket.status_normalized or ticket.status_raw or "Unknown",
            "status_group": _status_group(ticket.status_normalized),
            "is_open_status": _flag(ticket.is_open()),
            "is_closed_status": _flag(ticket.is_closed()),
        }
    order = {"Open": 1, "Closed": 2, "Unknown": 3}
    return sorted(
        seen.values(),
        key=lambda row: (order.get(row["status_group"], 9), row["status_key"]),
    )


def expected_measures(
    fact_ticket: list[dict[str, Any]],
    fact_finding: list[dict[str, Any]],
    report: MetricsReport,
) -> dict[str, Any]:
    """Values DAX COUNTROWS filters must return for the unfiltered demo snapshot."""

    def count_flag(name: str) -> int:
        return sum(int(row[name]) for row in fact_ticket)

    breached_by_client: dict[str, int] = {}
    for row in fact_ticket:
        if int(row["kpi_breached"]):
            breached_by_client[row["client_key"]] = breached_by_client.get(row["client_key"], 0) + 1

    action_rows = [row for row in fact_ticket if int(row["in_action_table"])]
    action_reasons: dict[str, int] = {}
    for row in action_rows:
        label = row["primary_reason_label"]
        action_reasons[label] = action_reasons.get(label, 0) + 1

    python_breach_findings = sum(
        1
        for row in fact_finding
        if row["finding_type"] in {"response_sla_breach", "resolve_sla_breach"}
    )
    python_approaching_findings = sum(
        1
        for row in fact_finding
        if row["finding_type"] in {"approaching_response", "approaching_resolve"}
    )
    python_ageing_findings = sum(1 for row in fact_finding if row["finding_type"] == "ageing_backlog")
    python_attention_findings = sum(1 for row in fact_finding if row["finding_type"] == "attention")

    exclusive_overlap_violations = [
        row["ticket_row_key"]
        for row in fact_ticket
        if int(row["kpi_breached"]) + int(row["kpi_approaching"]) + int(row["kpi_ageing"]) > 1
    ]

    return {
        "snapshot_id": SNAPSHOT_ID,
        "as_of": report.as_of,
        "source_csv": report.source_csv,
        "filters": "none (all clients, priorities, statuses)",
        "python_counts": dict(report.counts),
        "report_page_measures": {
            "Open tickets": count_flag("kpi_open"),
            "Breached tickets": count_flag("kpi_breached"),
            "Approaching tickets": count_flag("kpi_approaching"),
            "Ageing backlog": count_flag("kpi_ageing"),
        },
        "python_aligned_measures": {
            "Breached findings (Python-aligned)": python_breach_findings,
            "Approaching findings (Python-aligned)": python_approaching_findings,
            "Ageing backlog (Python-aligned)": python_ageing_findings,
            "Attention tickets (Python-aligned)": python_attention_findings,
            "Open tickets (Python-aligned)": report.counts["open_tickets"],
        },
        "breached_tickets_by_client": dict(sorted(breached_by_client.items())),
        "action_table_rows": len(action_rows),
        "action_table_by_primary_reason": dict(sorted(action_reasons.items())),
        "exclusive_kpi_overlap_violations": exclusive_overlap_violations,
        "intentional_deltas": [
            {
                "measure": "Breached tickets",
                "report_value": count_flag("kpi_breached"),
                "python_name": "counts.breached_slas",
                "python_value": report.counts["breached_slas"],
                "reason": (
                    "Python counts SLA clock findings. TCK-1021 has both a response "
                    "and a resolve breach (2 findings, 1 ticket). The KPI counts unique "
                    "ticket rows so the card does not double-count overlapping clocks."
                ),
            },
            {
                "measure": "Ageing backlog",
                "report_value": count_flag("kpi_ageing"),
                "python_name": "counts.ageing_backlog",
                "python_value": report.counts["ageing_backlog"],
                "reason": (
                    "TCK-1004 is ageing and resolve-breached. The ageing KPI excludes "
                    "rows already in the breached KPI so the four cards do not double-count "
                    "the same ticket. Use 'Ageing backlog (Python-aligned)' to match Phase A."
                ),
            },
        ],
        "trends_included": False,
        "trends_reason": (
            "Source data is a single frozen as_of snapshot, not a time series of "
            "daily operational counts."
        ),
    }


FACT_TICKET_FIELDS = [
    "ticket_row_key",
    "snapshot_id",
    "row_number",
    "ticket_id",
    "client_key",
    "priority_key",
    "priority_raw",
    "priority_display",
    "status_key",
    "status_raw",
    "status_display",
    "status_group",
    "assigned_to",
    "ticket_type",
    "category",
    "summary",
    "created_at",
    "first_response_at",
    "resolved_at",
    "status_updated_at",
    "sla_eligible",
    "response_sla_eligible",
    "resolve_sla_eligible",
    "is_open",
    "is_closed",
    "age_hours",
    "waiting_hours",
    "response_deadline",
    "response_elapsed_hours",
    "response_remaining_hours",
    "response_overdue_hours",
    "response_breached",
    "resolve_deadline",
    "resolve_elapsed_hours",
    "resolve_remaining_hours",
    "resolve_overdue_hours",
    "resolve_breached",
    "has_any_breach",
    "has_approaching",
    "approaching_response",
    "approaching_resolve",
    "is_ageing",
    "is_waiting_attention",
    "is_unassigned",
    "is_dq_blocking_sla",
    "is_python_attention",
    "python_reason_rule_ids",
    "dq_rule_ids",
    "kpi_open",
    "kpi_breached",
    "kpi_approaching",
    "kpi_ageing",
    "kpi_ageing_python",
    "exclusive_kpi_bucket",
    "in_action_table",
    "primary_reason_key",
    "primary_reason_label",
    "reason_sort",
    "deadline",
    "overdue_hours",
    "remaining_hours",
    "primary_clock_kind",
    "why_for_attention",
    "data_disclaimer",
]

FACT_FINDING_FIELDS = [
    "evidence_id",
    "snapshot_id",
    "ticket_row_key",
    "ticket_id",
    "finding_type",
    "rule_id",
    "client_key",
    "priority_key",
    "status_key",
    "computed_deadline",
    "hours_overdue",
    "hours_remaining",
    "clock_elapsed_hours",
    "why_it_qualifies",
    "reason_rule_ids",
    "as_of_utc",
]

TABLE_SCHEMAS = {
    "fact_ticket": FACT_TICKET_FIELDS,
    "fact_finding": FACT_FINDING_FIELDS,
    "dim_client": ["client_key", "client_id", "client_label"],
    "dim_priority": [
        "priority_key",
        "priority_label",
        "priority_sort",
        "response_hours",
        "resolve_hours",
        "aliases",
        "in_catalog",
    ],
    "dim_status": [
        "status_key",
        "status_label",
        "status_group",
        "is_open_status",
        "is_closed_status",
    ],
    "dim_attention_reason": [
        "reason_key",
        "reason_label",
        "reason_sort",
        "status_color",
        "is_kpi_bucket",
    ],
    "dim_snapshot": [
        "snapshot_id",
        "as_of_utc",
        "as_of_label",
        "data_disclaimer",
        "sla_catalog_version",
        "source_csv",
        "row_count",
        "notes",
    ],
}


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_star(model: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for table_name, fields in TABLE_SCHEMAS.items():
        path = destination / f"{table_name}.csv"
        _write_csv(path, fields, model[table_name])
        written[table_name] = path
    expected_path = destination / "expected_measures.json"
    expected_path.write_text(
        json.dumps(model["expected_measures"], indent=2) + "\n",
        encoding="utf-8",
    )
    written["expected_measures"] = expected_path
    return written


def export_demo_star(root: str | Path | None = None) -> dict[str, Path]:
    base = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    as_of_text = (base / "data" / "DEMO_AS_OF.txt").read_text(encoding="utf-8").strip()
    from mssp_sla.timeutil import parse_timestamp

    as_of = parse_timestamp(as_of_text)
    if as_of is None:
        raise ValueError("data/DEMO_AS_OF.txt is empty")
    model = build_model(base / "data" / "synthetic_tickets.csv", as_of)
    return write_star(model, base / "powerbi" / "data")


# --- DAX (paste into Desktop). Expressions count precomputed flags. ---

DAX_MEASURES: list[dict[str, str]] = [
    {
        "name": "Open tickets",
        "folder": "KPIs",
        "format": "#,0",
        "dax": (
            "CALCULATE ( COUNTROWS ( 'fact_ticket' ), 'fact_ticket'[kpi_open] = 1 )"
        ),
        "comment": (
            "Open volume at row grain. Matches Python counts.open_tickets "
            "(open/in_progress/waiting_customer/pending/investigating). "
            "Not exclusive versus the other KPI cards."
        ),
    },
    {
        "name": "Breached tickets",
        "folder": "KPIs",
        "format": "#,0",
        "dax": (
            "CALCULATE ( COUNTROWS ( 'fact_ticket' ), 'fact_ticket'[kpi_breached] = 1 )"
        ),
        "comment": (
            "Unique ticket rows with ≥1 SLA clock breach. Excludes double-counting "
            "response+resolve on the same row. Includes closed historical breaches."
        ),
    },
    {
        "name": "Approaching tickets",
        "folder": "KPIs",
        "format": "#,0",
        "dax": (
            "CALCULATE ( COUNTROWS ( 'fact_ticket' ), 'fact_ticket'[kpi_approaching] = 1 )"
        ),
        "comment": (
            "Still-ticking, not-yet-breached clocks inside the warn band. "
            "Mutually exclusive versus breached (Python already excludes breached clocks; "
            "the flag also excludes any row that has a different-clock breach)."
        ),
    },
    {
        "name": "Ageing backlog",
        "folder": "KPIs",
        "format": "#,0",
        "dax": (
            "CALCULATE ( COUNTROWS ( 'fact_ticket' ), 'fact_ticket'[kpi_ageing] = 1 )"
        ),
        "comment": (
            "Open rows aged ≥48h that are not already in the breached or approaching KPIs. "
            "Intentional delta versus Python ageing_backlog (TCK-1004 is counted only as breached)."
        ),
    },
    {
        "name": "Breached findings (Python-aligned)",
        "folder": "Python-aligned",
        "format": "#,0",
        "dax": (
            "CALCULATE ( COUNTROWS ( 'fact_finding' ), "
            "'fact_finding'[finding_type] IN { \"response_sla_breach\", \"resolve_sla_breach\" } )"
        ),
        "comment": "List length of Phase A breached_slas (8 on the demo snapshot).",
    },
    {
        "name": "Approaching findings (Python-aligned)",
        "folder": "Python-aligned",
        "format": "#,0",
        "dax": (
            "CALCULATE ( COUNTROWS ( 'fact_finding' ), "
            "'fact_finding'[finding_type] IN { \"approaching_response\", \"approaching_resolve\" } )"
        ),
        "comment": "List length of Phase A approaching_deadlines.",
    },
    {
        "name": "Ageing backlog (Python-aligned)",
        "folder": "Python-aligned",
        "format": "#,0",
        "dax": (
            "CALCULATE ( COUNTROWS ( 'fact_ticket' ), 'fact_ticket'[kpi_ageing_python] = 1 )"
        ),
        "comment": "Open age ≥48h with no exclusion. Matches Python counts.ageing_backlog.",
    },
    {
        "name": "Attention tickets (Python-aligned)",
        "folder": "Python-aligned",
        "format": "#,0",
        "dax": (
            "CALCULATE ( COUNTROWS ( 'fact_ticket' ), 'fact_ticket'[is_python_attention] = 1 )"
        ),
        "comment": (
            "Rows that appear on Phase A attention_list. Ageing-only and P3/P4 approaching "
            "tickets can be on the report table without this flag."
        ),
    },
    {
        "name": "Actionable tickets",
        "folder": "Table",
        "format": "#,0",
        "dax": (
            "CALCULATE ( COUNTROWS ( 'fact_ticket' ), 'fact_ticket'[in_action_table] = 1 )"
        ),
        "comment": "Rows with a primary reason (KPI buckets plus remaining Python attention rules).",
    },
    {
        "name": "Snapshot timestamp",
        "folder": "Header",
        "format": "@",
        "dax": 'SELECTEDVALUE ( \'dim_snapshot\'[as_of_label], BLANK () )',
        "comment": "Visible as-of label for the frozen demo snapshot.",
    },
    {
        "name": "Synthetic demonstration data",
        "folder": "Header",
        "format": "@",
        "dax": f'SELECTEDVALUE ( \'dim_snapshot\'[data_disclaimer], "{DATA_DISCLAIMER}" )',
        "comment": "Classification banner. Demo tickets are synthetic.",
    },
]


def render_measures_dax() -> str:
    lines = [
        "// MSSP SLA attention measures",
        "// Paste each block as a new measure on fact_ticket (or the model).",
        "// Flags are precomputed by mssp_sla.powerbi_export to match Phase A clocks.",
        "",
    ]
    for measure in DAX_MEASURES:
        lines.append(f"// {measure['folder']}: {measure['comment']}")
        lines.append(f"{measure['name']} = {measure['dax']}")
        lines.append("")
    return "\n".join(lines)


def render_measures_tmdl() -> str:
    lines = [
        "/// MSSP SLA attention measures (TMDL fragment).",
        "/// Not Desktop-validated. Import CSVs, then recreate these measures.",
        "",
    ]
    for measure in DAX_MEASURES:
        expr = measure["dax"]
        lines.append(f"measure '{measure['name']}' = {expr}")
        lines.append(f"\tformatString: {measure['format']}")
        lines.append(f"\tdisplayFolder: {measure['folder']}")
        comment = measure["comment"].replace("\n", " ")
        lines.append(f"\t\t/// {comment}")
        lines.append("")
    return "\n".join(lines)


@dataclass(frozen=True)
class Relationship:
    name: str
    from_table: str
    from_column: str
    to_table: str
    to_column: str


RELATIONSHIPS = (
    Relationship("fact_ticket_to_client", "fact_ticket", "client_key", "dim_client", "client_key"),
    Relationship("fact_ticket_to_priority", "fact_ticket", "priority_key", "dim_priority", "priority_key"),
    Relationship("fact_ticket_to_status", "fact_ticket", "status_key", "dim_status", "status_key"),
    Relationship("fact_ticket_to_reason", "fact_ticket", "primary_reason_key", "dim_attention_reason", "reason_key"),
    Relationship("fact_ticket_to_snapshot", "fact_ticket", "snapshot_id", "dim_snapshot", "snapshot_id"),
    # Findings filter through tickets so client/priority/status slicers stay a single path.
    Relationship("fact_finding_to_ticket", "fact_finding", "ticket_row_key", "fact_ticket", "ticket_row_key"),
)


def render_model_bim() -> str:
    """Tabular Editor compatible TMSL subset. No data partitions (import CSVs in Desktop)."""

    def col(name: str, data_type: str, source: str | None = None) -> dict[str, Any]:
        item: dict[str, Any] = {
            "name": name,
            "dataType": data_type,
            "sourceColumn": source or name,
            "summarizeBy": "none",
        }
        return item

    int_flags = {
        "sla_eligible",
        "response_sla_eligible",
        "resolve_sla_eligible",
        "is_open",
        "is_closed",
        "response_breached",
        "resolve_breached",
        "has_any_breach",
        "has_approaching",
        "approaching_response",
        "approaching_resolve",
        "is_ageing",
        "is_waiting_attention",
        "is_unassigned",
        "is_dq_blocking_sla",
        "is_python_attention",
        "kpi_open",
        "kpi_breached",
        "kpi_approaching",
        "kpi_ageing",
        "kpi_ageing_python",
        "in_action_table",
        "row_number",
        "reason_sort",
        "in_catalog",
        "is_open_status",
        "is_closed_status",
        "is_kpi_bucket",
        "priority_sort",
        "row_count",
    }

    def columns_for(table: str, fields: list[str]) -> list[dict[str, Any]]:
        out = []
        for field in fields:
            data_type = "int64" if field in int_flags else "string"
            out.append(col(field, data_type))
        return out

    tables = []
    for table_name, fields in TABLE_SCHEMAS.items():
        tables.append(
            {
                "name": table_name,
                "columns": columns_for(table_name, fields),
                "measures": [
                    {
                        "name": measure["name"],
                        "expression": measure["dax"],
                        "formatString": measure["format"],
                        "displayFolder": measure["folder"],
                        "description": measure["comment"],
                    }
                    for measure in DAX_MEASURES
                    if table_name == "fact_ticket"
                ],
            }
        )

    relationships = [
        {
            "name": rel.name,
            "fromTable": rel.from_table,
            "fromColumn": rel.from_column,
            "toTable": rel.to_table,
            "toColumn": rel.to_column,
            "crossFilteringBehavior": "oneDirection",
        }
        for rel in RELATIONSHIPS
    ]

    payload = {
        "name": "MSSP_SLA_Attention",
        "compatibilityLevel": 1550,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "tables": tables,
            "relationships": relationships,
            "annotations": [
                {"name": "PBI_QueryOrder", "value": json.dumps(list(TABLE_SCHEMAS))},
                {
                    "name": "MSSP_Note",
                    "value": "Logical model only. Import powerbi/data/*.csv in Desktop; this file was not opened in Power BI Desktop.",
                },
            ],
        },
    }
    return json.dumps(payload, indent=2) + "\n"
