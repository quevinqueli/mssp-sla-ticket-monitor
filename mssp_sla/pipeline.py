"""Phase A orchestration: parse → compute → verify → render. AI is optional."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from mssp_sla.ai_brief import generate_ai_section
from mssp_sla.brief import render_brief
from mssp_sla.compute import (
    collect_data_quality,
    compute_ageing_backlog,
    compute_approaching_deadlines,
    compute_attention_list,
    compute_breached_slas,
)
from mssp_sla.models import MetricsReport, VerificationResult
from mssp_sla.parse import load_tickets
from mssp_sla.sla_rules import SLA_CATALOG_VERSION
from mssp_sla.timeutil import iso
from mssp_sla.verify import verify_report


def display_source_path(csv_path: str | Path) -> str:
    """Prefer a cwd-relative path so committed artifacts are portable."""
    source = Path(csv_path)
    try:
        return str(source.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(csv_path)


def build_report(
    csv_path: str | Path,
    as_of: datetime,
    *,
    generated_at: datetime | None = None,
) -> MetricsReport:
    tickets, file_findings = load_tickets(csv_path)
    data_quality = collect_data_quality(tickets, file_findings)
    breached = compute_breached_slas(tickets, as_of)
    approaching = compute_approaching_deadlines(tickets, as_of)
    ageing = compute_ageing_backlog(tickets, as_of)
    attention = compute_attention_list(
        tickets,
        as_of,
        breached=breached,
        approaching=approaching,
        data_quality=data_quality,
    )

    report = MetricsReport(
        as_of=iso(as_of) or "",
        source_csv=display_source_path(csv_path),
        sla_catalog_version=SLA_CATALOG_VERSION,
        row_count=len(tickets),
        eligible_for_sla=sum(1 for ticket in tickets if ticket.sla_eligible),
        counts={
            "total_tickets": len(tickets),
            "sla_eligible": sum(1 for ticket in tickets if ticket.sla_eligible),
            "open_tickets": sum(1 for ticket in tickets if ticket.is_open()),
            "breached_slas": len(breached),
            "approaching_deadlines": len(approaching),
            "ageing_backlog": len(ageing),
            "attention": len(attention),
            "data_quality_flags": len(data_quality),
        },
        data_quality_findings=data_quality,
        breached_slas=breached,
        approaching_deadlines=approaching,
        ageing_backlog=ageing,
        attention_list=attention,
        verification=VerificationResult(passed=False, checks=[]),
        generated_at=iso(generated_at or as_of) or "",
    )
    report.verification = verify_report(report, tickets, as_of)
    return report


def write_outputs(
    report: MetricsReport,
    out_dir: str | Path,
    *,
    enable_ai: bool = False,
    ai_section: str | None = None,
    ai_skip_reason: str | None = None,
) -> dict[str, Path]:
    destination = Path(out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    metrics_path = destination / "metrics.json"
    brief_path = destination / "daily_brief.md"

    section = ai_section
    skip_reason = ai_skip_reason
    if enable_ai and section is None and skip_reason is None:
        section, skip_reason = generate_ai_section(report)
    if enable_ai and skip_reason and section is None:
        if skip_reason == "verification_failed":
            section = None
        elif skip_reason == "no_api_key":
            section = None
        else:
            section = (
                "**AI section withheld.** The optional model path did not produce a "
                "grounded explanation "
                f"({skip_reason}). Phase A evidence above is unchanged.\n"
            )

    metrics_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    brief_path.write_text(render_brief(report, ai_section=section), encoding="utf-8")
    return {"metrics": metrics_path, "brief": brief_path}
