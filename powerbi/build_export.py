"""Build Power BI star-schema CSVs from the same Phase A pipeline as the CLI demo.

Ticket-level KPIs that would otherwise double-count multi-finding tickets are
meant to use DISTINCTCOUNT in DAX. Python ``counts.breached_slas`` (and the
other finding lists) remain finding-grain.

Duplicate ``ticket_id`` values are **not** collapsed. DimTicket has one row per
parsed CSV row (``ticket_key`` = ``csv_row_number``). See powerbi/README.md.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from mssp_sla.models import Finding, MetricsReport, ParsedTicket
from mssp_sla.parse import load_tickets
from mssp_sla.pipeline import build_report, display_source_path
from mssp_sla.sla_rules import SLA_BY_PRIORITY
from mssp_sla.timeutil import iso

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "synthetic_tickets.csv"
DEFAULT_OUT = Path(__file__).resolve().parent / "data"

_ROW_SUFFIX = re.compile(r":row-(\d+)$")

FINDING_FAMILY_BREACH = "sla_breach"
FINDING_FAMILY_APPROACHING = "approaching"
FINDING_FAMILY_AGEING = "ageing_backlog"
FINDING_FAMILY_DQ = "data_quality"

TABLE_FILES = (
    "DimTicket.csv",
    "DimClient.csv",
    "DimPriority.csv",
    "DimStatus.csv",
    "FactFindings.csv",
    "FactAttention.csv",
    "SnapshotMeta.csv",
    "expected_kpis.json",
)


def _flag(value: bool) -> int:
    return 1 if value else 0


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _or_blank(value: str | None) -> str:
    text = _text(value).strip()
    return text if text else "(blank)"


def _hours(value: float | None) -> str:
    if value is None:
        return ""
    return str(value)


def _priority_key(ticket: ParsedTicket) -> str:
    if ticket.priority_normalized:
        return ticket.priority_normalized
    if ticket.priority_raw:
        return ticket.priority_raw
    return "(blank)"


def _status_key(ticket: ParsedTicket) -> str:
    if ticket.status_normalized:
        return ticket.status_normalized
    if ticket.status_raw:
        return ticket.status_raw
    return "(blank)"


def _status_class(status_key: str) -> str:
    if status_key in {"open", "in_progress", "waiting_customer", "pending", "investigating"}:
        return "open"
    if status_key in {"resolved", "closed"}:
        return "closed"
    if status_key == "(blank)":
        return "blank"
    return "unknown"


def _ticket_for_finding(finding: Finding, tickets: list[ParsedTicket]) -> ParsedTicket | None:
    """Map a finding to the parsed row it came from. Never invent a canonical duplicate."""
    row_match = _ROW_SUFFIX.search(finding.evidence_id)
    if row_match:
        row_number = int(row_match.group(1))
        for ticket in tickets:
            if ticket.row_number == row_number:
                return ticket
        return None

    candidates = [ticket for ticket in tickets if ticket.ticket_id == finding.ticket_id]
    if not candidates:
        if finding.ticket_id == "FILE":
            return None
        return None
    if len(candidates) == 1:
        return candidates[0]

    if finding.created_at:
        created_hits = [
            ticket for ticket in candidates if iso(ticket.created_at) == finding.created_at
        ]
        if len(created_hits) == 1:
            return created_hits[0]

    raise ValueError(
        f"Cannot uniquely map finding {finding.evidence_id!r} to a parsed row "
        f"for ticket_id={finding.ticket_id!r} without guessing a canonical duplicate."
    )


def _family_for_finding(finding: Finding) -> str:
    if finding.finding_type in {"response_sla_breach", "resolve_sla_breach"}:
        return FINDING_FAMILY_BREACH
    if finding.finding_type in {"approaching_response", "approaching_resolve"}:
        return FINDING_FAMILY_APPROACHING
    if finding.finding_type == "ageing_backlog":
        return FINDING_FAMILY_AGEING
    if finding.finding_type == "data_quality":
        return FINDING_FAMILY_DQ
    raise ValueError(f"Unknown finding_type for FactFindings: {finding.finding_type!r}")


def _linked_deadline(attention: Finding, sla_by_evidence: dict[str, Finding]) -> tuple[str, str, str]:
    """Earliest computed_deadline among linked breach/approaching evidence.

    Attention findings do not carry a deadline of their own. The dashboard table
    uses this linked value when present. If several SLA findings exist (e.g.
    TCK-1021 response + resolve), the earliest deadline is kept — not summed.
    """
    chosen_deadline = ""
    chosen_source = ""
    chosen_kind = ""
    for source_id in attention.source_evidence_ids:
        source = sla_by_evidence.get(source_id)
        if source is None or not source.computed_deadline:
            continue
        # Earliest deadline wins; ties keep the first source_evidence_ids entry.
        if not chosen_deadline or source.computed_deadline < chosen_deadline:
            chosen_deadline = source.computed_deadline
            chosen_source = source.evidence_id
            chosen_kind = source.finding_type
    return chosen_deadline, chosen_source, chosen_kind


def build_tables(
    csv_path: str | Path,
    as_of: datetime,
) -> dict[str, list[dict[str, Any]]]:
    """Return star-schema tables plus expected KPI dict (under key ``_kpis``)."""
    source = Path(csv_path)
    tickets, _file_findings = load_tickets(source)
    report = build_report(source, as_of)
    return tables_from_report(report, tickets, source)


def tables_from_report(
    report: MetricsReport,
    tickets: list[ParsedTicket],
    csv_path: str | Path,
) -> dict[str, list[dict[str, Any]]]:
    ticket_id_counts = Counter(ticket.ticket_id for ticket in tickets)
    instance_seq: dict[str, int] = defaultdict(int)

    dim_ticket: list[dict[str, Any]] = []
    for ticket in tickets:
        instance_seq[ticket.ticket_id] += 1
        dim_ticket.append(
            {
                "ticket_key": ticket.row_number,
                "ticket_id": ticket.ticket_id,
                "ticket_id_instance": instance_seq[ticket.ticket_id],
                "is_duplicate_ticket_id": _flag(ticket_id_counts[ticket.ticket_id] > 1),
                "csv_row_number": ticket.row_number,
                "created_at": _text(iso(ticket.created_at)),
                "first_response_at": _text(iso(ticket.first_response_at)),
                "resolved_at": _text(iso(ticket.resolved_at)),
                "status_updated_at": _text(iso(ticket.status_updated_at)),
                "priority_key": _priority_key(ticket),
                "priority_raw": ticket.priority_raw,
                "priority_normalized": _text(ticket.priority_normalized),
                "status_key": _status_key(ticket),
                "status_raw": ticket.status_raw,
                "status_normalized": _text(ticket.status_normalized),
                "customer_id": _or_blank(ticket.customer_id),
                "assigned_to": ticket.assigned_to,
                "ticket_type": ticket.ticket_type,
                "category": ticket.category,
                "summary": ticket.summary,
                "sla_eligible": _flag(ticket.sla_eligible),
                "response_sla_eligible": _flag(ticket.response_sla_eligible),
                "resolve_sla_eligible": _flag(ticket.resolve_sla_eligible),
                "is_open": _flag(ticket.is_open()),
                "is_closed": _flag(ticket.is_closed()),
                "synthetic_flag": 1,
            }
        )

    clients = sorted({row["customer_id"] for row in dim_ticket})
    dim_client = [
        {"customer_id": customer_id, "synthetic_flag": 1, "label": customer_id}
        for customer_id in clients
    ]

    priority_keys = sorted({row["priority_key"] for row in dim_ticket}, key=lambda key: (
        SLA_BY_PRIORITY[key].priority if key in SLA_BY_PRIORITY else "Z",
        key,
    ))
    dim_priority: list[dict[str, Any]] = []
    for index, key in enumerate(priority_keys, start=1):
        spec = SLA_BY_PRIORITY.get(key)
        dim_priority.append(
            {
                "priority_key": key,
                "priority_normalized": spec.priority if spec else "",
                "in_sla_catalog": _flag(spec is not None),
                "response_hours": spec.response_hours if spec else "",
                "resolve_hours": spec.resolve_hours if spec else "",
                "sort_order": (
                    {"P1": 1, "P2": 2, "P3": 3, "P4": 4}.get(key, 90 + index)
                ),
                "synthetic_flag": 1,
            }
        )

    status_order = [
        "open",
        "in_progress",
        "investigating",
        "pending",
        "waiting_customer",
        "resolved",
        "closed",
    ]
    status_keys = {row["status_key"] for row in dim_ticket}

    def _status_sort(key: str) -> tuple[int, str]:
        if key in status_order:
            return (status_order.index(key), key)
        return (100, key)

    dim_status = []
    for key in sorted(status_keys, key=_status_sort):
        klass = _status_class(key)
        dim_status.append(
            {
                "status_key": key,
                "status_class": klass,
                "is_open": _flag(klass == "open"),
                "sort_order": _status_sort(key)[0],
                "synthetic_flag": 1,
            }
        )

    operational = (
        list(report.breached_slas)
        + list(report.approaching_deadlines)
        + list(report.ageing_backlog)
        + list(report.data_quality_findings)
    )
    fact_findings: list[dict[str, Any]] = []
    for finding in operational:
        ticket = _ticket_for_finding(finding, tickets)
        fact_findings.append(
            {
                "evidence_id": finding.evidence_id,
                "ticket_key": ticket.row_number if ticket else "",
                "ticket_id": finding.ticket_id,
                "finding_family": _family_for_finding(finding),
                "finding_type": finding.finding_type,
                "rule_id": finding.rule_id,
                "why_it_qualifies": finding.why_it_qualifies,
                "computed_deadline": _text(finding.computed_deadline),
                "computed_age_hours": _hours(finding.computed_age_hours),
                "clock_elapsed_hours": _hours(finding.clock_elapsed_hours),
                "hours_overdue": _hours(finding.hours_overdue),
                "hours_remaining": _hours(finding.hours_remaining),
                "clock_stop_at": _text(finding.clock_stop_at),
                "customer_id": _or_blank(finding.customer_id),
                "priority": _text(finding.priority),
                "status": _text(finding.status),
                "assigned_to": _text(finding.assigned_to),
                "synthetic_flag": 1,
            }
        )

    sla_by_evidence = {
        finding.evidence_id: finding
        for finding in list(report.breached_slas) + list(report.approaching_deadlines)
    }

    fact_attention: list[dict[str, Any]] = []
    for finding in report.attention_list:
        ticket = _ticket_for_finding(finding, tickets)
        deadline, source, kind = _linked_deadline(finding, sla_by_evidence)
        fact_attention.append(
            {
                "evidence_id": finding.evidence_id,
                "ticket_key": ticket.row_number if ticket else "",
                "ticket_id": finding.ticket_id,
                "reason_for_attention": finding.why_it_qualifies,
                "reason_rule_ids": "|".join(finding.reason_rule_ids),
                "primary_rule_id": finding.rule_id,
                "source_evidence_ids": "|".join(finding.source_evidence_ids),
                "linked_deadline": deadline,
                "linked_deadline_source": source,
                "linked_deadline_kind": kind,
                "customer_id": _or_blank(
                    finding.customer_id or (ticket.customer_id if ticket else "")
                ),
                "priority_key": _priority_key(ticket) if ticket else _text(finding.priority),
                "status_key": _status_key(ticket) if ticket else _text(finding.status),
                "assigned_to": _text(
                    finding.assigned_to if finding.assigned_to is not None else (
                        ticket.assigned_to if ticket else ""
                    )
                ),
                "computed_age_hours": _hours(finding.computed_age_hours),
                "is_open": _flag(ticket.is_open()) if ticket else _flag(
                    (finding.status or "") in {
                        "open",
                        "in_progress",
                        "waiting_customer",
                        "pending",
                        "investigating",
                    }
                ),
                "synthetic_flag": 1,
            }
        )

    snapshot = [
        {
            "snapshot_id": f"DEMO-{report.as_of}",
            "as_of": report.as_of,
            "source_csv": display_source_path(csv_path),
            "sla_catalog_version": report.sla_catalog_version,
            "synthetic_flag": 1,
            "verification_passed": _flag(report.verification.passed),
            "generated_at": report.generated_at,
            "row_count": report.row_count,
            "eligible_for_sla": report.eligible_for_sla,
            "source_note": (
                "Built from the same Phase A pipeline as artifacts/metrics.json. "
                "All rows are synthetic. Do not treat customer_id values as real orgs."
            ),
        }
    ]

    kpis = _expected_kpis(report, dim_ticket, fact_findings, fact_attention)
    return {
        "DimTicket": dim_ticket,
        "DimClient": dim_client,
        "DimPriority": dim_priority,
        "DimStatus": dim_status,
        "FactFindings": fact_findings,
        "FactAttention": fact_attention,
        "SnapshotMeta": snapshot,
        "_kpis": [kpis],
    }


def _expected_kpis(
    report: MetricsReport,
    dim_ticket: list[dict[str, Any]],
    fact_findings: list[dict[str, Any]],
    fact_attention: list[dict[str, Any]],
) -> dict[str, Any]:
    open_rows = [row for row in dim_ticket if row["is_open"] == 1]
    breach = [row for row in fact_findings if row["finding_family"] == FINDING_FAMILY_BREACH]
    approaching = [row for row in fact_findings if row["finding_family"] == FINDING_FAMILY_APPROACHING]
    ageing = [row for row in fact_findings if row["finding_family"] == FINDING_FAMILY_AGEING]
    dq = [row for row in fact_findings if row["finding_family"] == FINDING_FAMILY_DQ]

    by_client: dict[str, int] = {}
    for ticket_id, customer_id in sorted({(row["ticket_id"], row["customer_id"]) for row in breach}):
        by_client[customer_id] = by_client.get(customer_id, 0) + 1

    return {
        "as_of": report.as_of,
        "source_csv": report.source_csv,
        "synthetic_flag": True,
        "verification_passed": report.verification.passed,
        "python_counts": dict(report.counts),
        "dashboard_unfiltered": {
            "open_tickets_row_grain": len(open_rows),
            "open_ticket_ids_distinct": len({row["ticket_id"] for row in open_rows}),
            "total_tickets_row_grain": len(dim_ticket),
            "sla_eligible_row_grain": sum(row["sla_eligible"] for row in dim_ticket),
            "breached_slas_finding_grain": len(breach),
            "breached_tickets_distinct": len({row["ticket_id"] for row in breach}),
            "approaching_deadlines_finding_grain": len(approaching),
            "approaching_tickets_distinct": len({row["ticket_id"] for row in approaching}),
            "ageing_backlog_finding_grain": len(ageing),
            "ageing_tickets_distinct": len({row["ticket_id"] for row in ageing}),
            "attention_row_grain": len(fact_attention),
            "attention_ticket_ids_distinct": len({row["ticket_id"] for row in fact_attention}),
            "data_quality_flags_finding_grain": len(dq),
        },
        "breached_tickets_by_client": by_client,
        "slicer_client_CUST_C": {
            "open_tickets_row_grain": sum(
                1 for row in dim_ticket if row["customer_id"] == "CUST-C" and row["is_open"] == 1
            ),
            "breached_slas_finding_grain": sum(
                1
                for row in breach
                if row["customer_id"] == "CUST-C"
            ),
            "breached_tickets_distinct": len(
                {row["ticket_id"] for row in breach if row["customer_id"] == "CUST-C"}
            ),
            "attention_row_grain": sum(
                1 for row in fact_attention if row["customer_id"] == "CUST-C"
            ),
        },
        "grain_notes": {
            "open_tickets": (
                "Python counts.open_tickets is parsed-row grain (DimTicket rows with "
                "is_open=1), not DISTINCTCOUNT of ticket_id. Duplicate ticket_id values "
                "are two DimTicket rows."
            ),
            "breached_slas": (
                "Python counts.breached_slas is finding-grain. A ticket with both a "
                "response and a resolve breach (TCK-1021) counts twice as findings and "
                "once as a distinct ticket."
            ),
            "attention": (
                "Python counts.attention is one row per attention evidence_id. "
                "Duplicate ticket_id TCK-1020 has two attention rows."
            ),
        },
    }


def write_tables(tables: dict[str, list[dict[str, Any]]], out_dir: str | Path) -> dict[str, Path]:
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, rows in tables.items():
        if name == "_kpis":
            path = destination / "expected_kpis.json"
            payload = rows[0]
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            written["expected_kpis"] = path
            continue
        path = destination / f"{name}.csv"
        if not rows:
            path.write_text("", encoding="utf-8-sig")
            written[name] = path
            continue
        fieldnames = list(rows[0].keys())
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({key: "" if row[key] is None else row[key] for key in fieldnames})
        written[name] = path
    return written


def export_powerbi(
    csv_path: str | Path,
    as_of: datetime,
    out_dir: str | Path,
) -> dict[str, Path]:
    tables = build_tables(csv_path, as_of)
    return write_tables(tables, out_dir)
