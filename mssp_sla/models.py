"""Dataclasses for parsed tickets, evidence-bearing findings, and reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Finding:
    """One deterministic finding with the evidence needed to re-check it."""

    evidence_id: str
    ticket_id: str
    finding_type: str
    rule_id: str
    why_it_qualifies: str
    created_at: str | None = None
    first_response_at: str | None = None
    resolved_at: str | None = None
    status_updated_at: str | None = None
    status: str | None = None
    priority: str | None = None
    customer_id: str | None = None
    assigned_to: str | None = None
    computed_deadline: str | None = None
    computed_age_hours: float | None = None
    clock_elapsed_hours: float | None = None
    hours_overdue: float | None = None
    hours_remaining: float | None = None
    clock_stop_at: str | None = None
    reason_rule_ids: list[str] = field(default_factory=list)
    source_evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParsedTicket:
    """A CSV row after validation. Flags hold data-quality findings only."""

    ticket_id: str
    row_number: int
    raw: dict[str, str]
    created_at: datetime | None
    first_response_at: datetime | None
    resolved_at: datetime | None
    status_updated_at: datetime | None
    priority_raw: str
    priority_normalized: str | None
    status_raw: str
    status_normalized: str | None
    customer_id: str
    assigned_to: str
    ticket_type: str
    category: str
    summary: str
    flags: list[Finding] = field(default_factory=list)
    sla_eligible: bool = False
    response_sla_eligible: bool = False
    resolve_sla_eligible: bool = False

    def is_open(self) -> bool:
        return self.status_normalized in {
            "open",
            "in_progress",
            "waiting_customer",
            "pending",
            "investigating",
        }

    def is_closed(self) -> bool:
        return self.status_normalized in {"resolved", "closed"}


@dataclass
class VerificationResult:
    passed: bool
    checks: list[dict[str, Any]]

    @property
    def failed_checks(self) -> list[dict[str, Any]]:
        return [check for check in self.checks if not check.get("passed")]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "failed_checks": self.failed_checks,
        }


@dataclass
class MetricsReport:
    """Verified (or verification-failed) Phase A output. This is the only
    structured object Phase B is allowed to read.
    """

    as_of: str
    source_csv: str
    sla_catalog_version: str
    row_count: int
    eligible_for_sla: int
    counts: dict[str, int]
    data_quality_findings: list[Finding]
    breached_slas: list[Finding]
    approaching_deadlines: list[Finding]
    ageing_backlog: list[Finding]
    attention_list: list[Finding]
    verification: VerificationResult
    generated_at: str

    def all_findings(self) -> list[Finding]:
        return (
            list(self.data_quality_findings)
            + list(self.breached_slas)
            + list(self.approaching_deadlines)
            + list(self.ageing_backlog)
            + list(self.attention_list)
        )

    def evidence_ids(self) -> set[str]:
        return {finding.evidence_id for finding in self.all_findings()}

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": {
                "as_of": self.as_of,
                "source_csv": self.source_csv,
                "sla_catalog_version": self.sla_catalog_version,
                "row_count": self.row_count,
                "eligible_for_sla": self.eligible_for_sla,
                "generated_at": self.generated_at,
                "verification": self.verification.to_dict(),
            },
            "counts": self.counts,
            "data_quality_findings": [item.to_dict() for item in self.data_quality_findings],
            "breached_slas": [item.to_dict() for item in self.breached_slas],
            "approaching_deadlines": [item.to_dict() for item in self.approaching_deadlines],
            "ageing_backlog": [item.to_dict() for item in self.ageing_backlog],
            "attention_list": [item.to_dict() for item in self.attention_list],
        }
