"""Phase A verification gate. Phase B must not run unless this passes."""

from __future__ import annotations

from datetime import datetime

from mssp_sla.models import Finding, MetricsReport, ParsedTicket, VerificationResult
from mssp_sla.sla_rules import SLA_BY_PRIORITY, catalog_rule_ids
from mssp_sla.timeutil import add_hours, hours_between, iso, parse_timestamp

REQUIRED_EVIDENCE_FIELDS = (
    "evidence_id",
    "ticket_id",
    "finding_type",
    "rule_id",
    "why_it_qualifies",
)

SLA_FINDING_TYPES = {
    "response_sla_breach",
    "resolve_sla_breach",
    "approaching_response",
    "approaching_resolve",
}


def _check(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "passed": passed, "detail": detail}


def _deadline_matches(finding: Finding, tickets_by_id: dict[str, ParsedTicket]) -> str | None:
    """Recompute the SLA deadline from created_at + catalog hours. Return error or None."""
    ticket = tickets_by_id.get(finding.ticket_id)
    if ticket is None or ticket.created_at is None or ticket.priority_normalized is None:
        return f"{finding.evidence_id}: ticket missing created_at/priority for recomputation"
    spec = SLA_BY_PRIORITY[ticket.priority_normalized]
    if finding.finding_type in {"response_sla_breach", "approaching_response"}:
        expected = add_hours(ticket.created_at, spec.response_hours)
        expected_rule = spec.response_rule_id
    else:
        expected = add_hours(ticket.created_at, spec.resolve_hours)
        expected_rule = spec.resolve_rule_id
    if finding.rule_id != expected_rule:
        return (
            f"{finding.evidence_id}: rule_id {finding.rule_id} does not match "
            f"catalog {expected_rule} for {ticket.priority_normalized}"
        )
    if finding.computed_deadline != iso(expected):
        return (
            f"{finding.evidence_id}: computed_deadline {finding.computed_deadline} "
            f"!= recomputed {iso(expected)}"
        )
    return None


def _overdue_matches(finding: Finding) -> str | None:
    if finding.computed_deadline is None or finding.clock_stop_at is None:
        return f"{finding.evidence_id}: missing deadline or clock_stop_at"
    deadline = parse_timestamp(finding.computed_deadline)
    stop = parse_timestamp(finding.clock_stop_at)
    if deadline is None or stop is None:
        return f"{finding.evidence_id}: could not parse deadline/stop"
    expected_overdue = hours_between(deadline, stop) if stop > deadline else 0.0
    actual = finding.hours_overdue if finding.hours_overdue is not None else 0.0
    if abs(expected_overdue - actual) > 0.0001:
        return (
            f"{finding.evidence_id}: hours_overdue {actual} != recomputed {expected_overdue}"
        )
    return None


def verify_report(
    report: MetricsReport,
    tickets: list[ParsedTicket],
    as_of: datetime,
) -> VerificationResult:
    checks: list[dict] = []
    known_rules = catalog_rule_ids()
    tickets_by_id = {ticket.ticket_id: ticket for ticket in tickets}

    missing_fields: list[str] = []
    for finding in report.all_findings():
        for field_name in REQUIRED_EVIDENCE_FIELDS:
            if not getattr(finding, field_name):
                missing_fields.append(f"{finding.evidence_id}:{field_name}")
    checks.append(
        _check(
            "evidence_fields_present",
            not missing_fields,
            "ok" if not missing_fields else f"missing {missing_fields}",
        )
    )

    unknown_rules = [
        f"{finding.evidence_id}:{finding.rule_id}"
        for finding in report.all_findings()
        if finding.rule_id not in known_rules
        and finding.rule_id not in (finding.reason_rule_ids or [])
    ]
    # Attention findings use the first reason as rule_id; all reasons must be catalogued.
    bad_reasons: list[str] = []
    for finding in report.attention_list:
        for reason in finding.reason_rule_ids or [finding.rule_id]:
            if reason not in known_rules:
                bad_reasons.append(f"{finding.evidence_id}:{reason}")
    checks.append(
        _check(
            "rule_ids_in_catalog",
            not unknown_rules and not bad_reasons,
            "ok"
            if not unknown_rules and not bad_reasons
            else f"unknown={unknown_rules} reasons={bad_reasons}",
        )
    )

    expected_counts = {
        "breached_slas": len(report.breached_slas),
        "approaching_deadlines": len(report.approaching_deadlines),
        "ageing_backlog": len(report.ageing_backlog),
        "attention": len(report.attention_list),
        "data_quality_flags": len(report.data_quality_findings),
        "total_tickets": len(tickets),
        "sla_eligible": sum(1 for ticket in tickets if ticket.sla_eligible),
    }
    count_mismatches = {
        key: {"expected": value, "reported": report.counts.get(key)}
        for key, value in expected_counts.items()
        if report.counts.get(key) != value
    }
    checks.append(
        _check(
            "counts_match_lists",
            not count_mismatches,
            "ok" if not count_mismatches else f"mismatches={count_mismatches}",
        )
    )

    duplicate_ids = []
    seen: set[str] = set()
    for finding in report.all_findings():
        if finding.evidence_id in seen:
            duplicate_ids.append(finding.evidence_id)
        seen.add(finding.evidence_id)
    checks.append(
        _check(
            "evidence_ids_unique",
            not duplicate_ids,
            "ok" if not duplicate_ids else f"duplicates={duplicate_ids}",
        )
    )

    deadline_errors: list[str] = []
    overdue_errors: list[str] = []
    for finding in report.breached_slas + report.approaching_deadlines:
        if finding.finding_type not in SLA_FINDING_TYPES:
            deadline_errors.append(f"{finding.evidence_id}: unexpected type")
            continue
        err = _deadline_matches(finding, tickets_by_id)
        if err:
            deadline_errors.append(err)
        if finding.finding_type.endswith("_breach"):
            err = _overdue_matches(finding)
            if err:
                overdue_errors.append(err)
    checks.append(
        _check(
            "deadlines_recompute",
            not deadline_errors,
            "ok" if not deadline_errors else "; ".join(deadline_errors),
        )
    )
    checks.append(
        _check(
            "overdue_recompute",
            not overdue_errors,
            "ok" if not overdue_errors else "; ".join(overdue_errors),
        )
    )

    orphan_sources: list[str] = []
    known_ids = {finding.evidence_id for finding in report.all_findings()}
    for finding in report.attention_list:
        for source_id in finding.source_evidence_ids:
            if source_id not in known_ids:
                orphan_sources.append(f"{finding.evidence_id}->{source_id}")
    checks.append(
        _check(
            "attention_sources_exist",
            not orphan_sources,
            "ok" if not orphan_sources else f"orphans={orphan_sources}",
        )
    )

    as_of_ok = report.as_of == iso(as_of)
    checks.append(
        _check(
            "as_of_matches_input",
            as_of_ok,
            "ok" if as_of_ok else f"{report.as_of} != {iso(as_of)}",
        )
    )

    passed = all(check["passed"] for check in checks)
    return VerificationResult(passed=passed, checks=checks)
