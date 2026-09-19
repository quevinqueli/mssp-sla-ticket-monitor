"""Render a daily operational brief from verified Phase A metrics only."""

from __future__ import annotations

from mssp_sla.models import Finding, MetricsReport


def _fmt_hours(value: float | None) -> str:
    if value is None:
        return "n/a"
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return f"{text}h"


def _finding_block(finding: Finding) -> list[str]:
    lines = [
        f"### {finding.evidence_id}",
        f"- Ticket: `{finding.ticket_id}`",
        f"- Rule: `{finding.rule_id}`",
        f"- Type: {finding.finding_type}",
    ]
    if finding.priority:
        lines.append(f"- Priority: {finding.priority}")
    if finding.status:
        lines.append(f"- Status: {finding.status}")
    if finding.customer_id:
        lines.append(f"- Customer id (from CSV): `{finding.customer_id}`")
    if finding.assigned_to:
        lines.append(f"- Assigned to (from CSV): `{finding.assigned_to}`")
    if finding.created_at:
        lines.append(f"- created_at: {finding.created_at}")
    if finding.first_response_at:
        lines.append(f"- first_response_at: {finding.first_response_at}")
    elif finding.finding_type in {"response_sla_breach", "approaching_response"}:
        lines.append("- first_response_at: _(empty — still unanswered)_")
    if finding.resolved_at:
        lines.append(f"- resolved_at: {finding.resolved_at}")
    if finding.computed_deadline:
        lines.append(f"- Computed deadline: {finding.computed_deadline}")
    if finding.clock_stop_at:
        lines.append(f"- Clock stop: {finding.clock_stop_at}")
    if finding.computed_age_hours is not None:
        lines.append(f"- Age at as_of: {_fmt_hours(finding.computed_age_hours)}")
    if finding.clock_elapsed_hours is not None:
        lines.append(f"- Clock elapsed: {_fmt_hours(finding.clock_elapsed_hours)}")
    if finding.hours_overdue is not None and finding.finding_type.endswith("breach"):
        lines.append(f"- Hours overdue: {_fmt_hours(finding.hours_overdue)}")
    if finding.hours_remaining is not None and finding.finding_type.startswith("approaching"):
        lines.append(f"- Hours remaining: {_fmt_hours(finding.hours_remaining)}")
    if finding.reason_rule_ids:
        lines.append("- Attention reasons: " + ", ".join(f"`{r}`" for r in finding.reason_rule_ids))
    if finding.source_evidence_ids:
        lines.append(
            "- Cites evidence: " + ", ".join(f"`{eid}`" for eid in finding.source_evidence_ids)
        )
    lines.append(f"- Why it qualifies: {finding.why_it_qualifies}")
    lines.append("")
    return lines


def _section(title: str, findings: list[Finding], empty: str) -> list[str]:
    lines = [f"## {title}", ""]
    if not findings:
        lines.extend([empty, ""])
        return lines
    for finding in findings:
        lines.extend(_finding_block(finding))
    return lines


def render_brief(report: MetricsReport, ai_section: str | None = None) -> str:
    """Markdown brief. Numbers come only from the Phase A report object."""
    verification = report.verification
    banner = (
        "PASSED — figures below were recomputed from timestamps and the SLA catalog."
        if verification.passed
        else "FAILED — AI section is withheld. Treat figures as unverified until checks pass."
    )
    lines = [
        "# MSSP Daily SLA Operational Brief",
        "",
        f"- As of: `{report.as_of}`",
        f"- Source CSV: `{report.source_csv}`",
        f"- SLA catalog: `{report.sla_catalog_version}`",
        f"- Generated at: `{report.generated_at}`",
        f"- Verification: **{banner}**",
        "",
        "## Snapshot (verified counts only)",
        "",
        f"- Tickets in file: **{report.counts.get('total_tickets', 0)}**",
        f"- SLA-eligible tickets: **{report.counts.get('sla_eligible', 0)}**",
        f"- Open tickets: **{report.counts.get('open_tickets', 0)}**",
        f"- SLA breach findings: **{report.counts.get('breached_slas', 0)}**",
        f"- Approaching-deadline findings: **{report.counts.get('approaching_deadlines', 0)}**",
        f"- Ageing backlog findings: **{report.counts.get('ageing_backlog', 0)}**",
        f"- Attention-list tickets: **{report.counts.get('attention', 0)}**",
        f"- Data-quality findings: **{report.counts.get('data_quality_flags', 0)}**",
        "",
        "These counts are list lengths from Phase A. They are not forecasts or risk scores.",
        "",
    ]

    if not verification.passed:
        lines.extend(
            [
                "## Verification failures",
                "",
            ]
        )
        for check in verification.failed_checks:
            lines.append(f"- `{check['name']}`: {check['detail']}")
        lines.append("")

    lines.extend(
        _section(
            "Breached SLAs",
            report.breached_slas,
            "_No breached SLAs in the SLA-eligible set._",
        )
    )
    lines.extend(
        _section(
            "Approaching deadlines",
            report.approaching_deadlines,
            "_No approaching deadlines in the SLA-eligible set._",
        )
    )
    lines.extend(
        _section(
            "Ageing backlog",
            report.ageing_backlog,
            "_No open tickets meet the 48h ageing threshold._",
        )
    )
    lines.extend(
        _section(
            "Tickets requiring attention",
            report.attention_list,
            "_No tickets matched an explicit attention rule._",
        )
    )
    lines.extend(
        _section(
            "Data quality (missing or ambiguous — not guessed)",
            report.data_quality_findings,
            "_No missing-field or ambiguous-definition flags._",
        )
    )

    lines.extend(["## AI recommended actions", ""])
    if ai_section:
        lines.append(ai_section)
        lines.append("")
    elif not verification.passed:
        lines.extend(
            [
                (
                    "**Verification failed — AI section omitted.** "
                    "The brief ships with Phase A evidence only. "
                    "No model was asked to invent metrics."
                ),
                "",
            ]
        )
    else:
        lines.extend(
            [
                (
                    "_AI section omitted (optional path not enabled, or no API key). "
                    "The Phase A numbers and evidence above are complete without a model._"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            "This brief does not invent customer impact, financial loss, or unstated outcomes. "
            "Customer identifiers are copied from the source CSV when present.",
            "",
        ]
    )
    return "\n".join(lines)
