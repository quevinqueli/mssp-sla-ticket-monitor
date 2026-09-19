"""Explicit SLA catalog.

Ambiguous or unknown priorities are never mapped by guesswork. Callers must
flag those rows and skip SLA clocks instead of inventing a target.
"""

from __future__ import annotations

from dataclasses import dataclass

# Ageing backlog: still-open tickets whose age meets or exceeds this threshold.
AGEING_BACKLOG_HOURS = 48.0

# waiting_customer attention only applies when status_updated_at is known.
WAITING_CUSTOMER_ATTENTION_HOURS = 24.0

# Short SLA windows (response targets of 1 hour or less) warn in the last 50%.
SHORT_SLA_HOURS = 1.0
SHORT_SLA_APPROACHING_FRACTION = 0.5

# Longer windows warn in the last 25% of the window, capped at 2 hours.
LONG_SLA_APPROACHING_FRACTION = 0.25
LONG_SLA_APPROACHING_CAP_HOURS = 2.0

SLA_CATALOG_VERSION = "v1"


@dataclass(frozen=True)
class PrioritySla:
    """Response and resolve targets for one normalized priority."""

    priority: str
    response_hours: float
    resolve_hours: float
    response_rule_id: str
    resolve_rule_id: str


# Only these tokens map to an SLA. Anything else is DQ-UNKNOWN-PRIORITY.
PRIORITY_ALIASES: dict[str, str] = {
    "p1": "P1",
    "critical": "P1",
    "crit": "P1",
    "1": "P1",
    "p2": "P2",
    "high": "P2",
    "2": "P2",
    "p3": "P3",
    "medium": "P3",
    "med": "P3",
    "3": "P3",
    "p4": "P4",
    "low": "P4",
    "4": "P4",
}

SLA_BY_PRIORITY: dict[str, PrioritySla] = {
    "P1": PrioritySla(
        priority="P1",
        response_hours=0.25,  # 15 minutes
        resolve_hours=4.0,
        response_rule_id="SLA-RESPONSE-P1",
        resolve_rule_id="SLA-RESOLVE-P1",
    ),
    "P2": PrioritySla(
        priority="P2",
        response_hours=1.0,
        resolve_hours=8.0,
        response_rule_id="SLA-RESPONSE-P2",
        resolve_rule_id="SLA-RESOLVE-P2",
    ),
    "P3": PrioritySla(
        priority="P3",
        response_hours=4.0,
        resolve_hours=24.0,
        response_rule_id="SLA-RESPONSE-P3",
        resolve_rule_id="SLA-RESOLVE-P3",
    ),
    "P4": PrioritySla(
        priority="P4",
        response_hours=8.0,
        resolve_hours=72.0,
        response_rule_id="SLA-RESPONSE-P4",
        resolve_rule_id="SLA-RESOLVE-P4",
    ),
}

# Attention list rules (deterministic; one ticket may match several).
RULE_AGEING_BACKLOG = "AGEING-BACKLOG-48H"
RULE_ATTENTION_OPEN_BREACH = "ATTENTION-OPEN-BREACH"
RULE_ATTENTION_CLOSED_P1P2_BREACH = "ATTENTION-P1P2-CLOSED-BREACH"
RULE_ATTENTION_APPROACHING_P1P2 = "ATTENTION-APPROACHING-P1P2"
RULE_ATTENTION_UNASSIGNED = "ATTENTION-UNASSIGNED"
RULE_ATTENTION_DATA_QUALITY = "ATTENTION-DATA-QUALITY"
RULE_ATTENTION_WAITING_CUSTOMER = "ATTENTION-WAITING-CUSTOMER"

# Data-quality rule ids. These flag rows; they never fill in missing values.
RULE_DQ_MISSING_TICKET_ID = "DQ-MISSING-TICKET-ID"
RULE_DQ_MISSING_CREATED_AT = "DQ-MISSING-CREATED-AT"
RULE_DQ_MISSING_PRIORITY = "DQ-MISSING-PRIORITY"
RULE_DQ_MISSING_STATUS = "DQ-MISSING-STATUS"
RULE_DQ_UNKNOWN_PRIORITY = "DQ-UNKNOWN-PRIORITY"
RULE_DQ_UNKNOWN_STATUS = "DQ-UNKNOWN-STATUS"
RULE_DQ_AMBIGUOUS_TIMESTAMP = "DQ-AMBIGUOUS-TIMESTAMP"
RULE_DQ_TIMELINE_INCONSISTENT = "DQ-TIMELINE-INCONSISTENT"
RULE_DQ_MISSING_RESOLVED_AT = "DQ-MISSING-RESOLVED-AT"
RULE_DQ_AMBIGUOUS_WAIT_CLOCK = "DQ-AMBIGUOUS-WAIT-CLOCK"
RULE_DQ_DUPLICATE_TICKET_ID = "DQ-DUPLICATE-TICKET-ID"
RULE_DQ_MISSING_COLUMN = "DQ-MISSING-COLUMN"


def normalize_priority(raw: str | None) -> str | None:
    """Return P1–P4 or None when the value is missing/unknown (never guessed)."""
    if raw is None:
        return None
    token = raw.strip().lower()
    if not token:
        return None
    return PRIORITY_ALIASES.get(token)


def sla_for_priority(priority: str) -> PrioritySla:
    return SLA_BY_PRIORITY[priority]


def approaching_threshold_hours(sla_hours: float) -> float:
    """Hours remaining at which a still-ticking clock counts as approaching.

    Short windows (≤ 1h): last 50% of the SLA.
    Longer windows: last 25% of the SLA, but never more than 2 hours.
    """
    if sla_hours <= SHORT_SLA_HOURS:
        return sla_hours * SHORT_SLA_APPROACHING_FRACTION
    return min(
        LONG_SLA_APPROACHING_CAP_HOURS,
        sla_hours * LONG_SLA_APPROACHING_FRACTION,
    )


def is_approaching(remaining_hours: float, sla_hours: float) -> bool:
    """True when the clock is still inside the window and inside the warn band.

    remaining_hours <= 0 is never approaching. Combined with breach = stop >
    deadline, a clock that stops exactly on the deadline is neither breached
    nor approaching (intentional v1 gap; no due-now finding).
    """
    if remaining_hours <= 0:
        return False
    return remaining_hours <= approaching_threshold_hours(sla_hours)


def catalog_rule_ids() -> frozenset[str]:
    """Every rule id the pipeline is allowed to emit."""
    ids = {
        RULE_AGEING_BACKLOG,
        RULE_ATTENTION_OPEN_BREACH,
        RULE_ATTENTION_CLOSED_P1P2_BREACH,
        RULE_ATTENTION_APPROACHING_P1P2,
        RULE_ATTENTION_UNASSIGNED,
        RULE_ATTENTION_DATA_QUALITY,
        RULE_ATTENTION_WAITING_CUSTOMER,
        RULE_DQ_MISSING_TICKET_ID,
        RULE_DQ_MISSING_CREATED_AT,
        RULE_DQ_MISSING_PRIORITY,
        RULE_DQ_MISSING_STATUS,
        RULE_DQ_UNKNOWN_PRIORITY,
        RULE_DQ_UNKNOWN_STATUS,
        RULE_DQ_AMBIGUOUS_TIMESTAMP,
        RULE_DQ_TIMELINE_INCONSISTENT,
        RULE_DQ_MISSING_RESOLVED_AT,
        RULE_DQ_AMBIGUOUS_WAIT_CLOCK,
        RULE_DQ_DUPLICATE_TICKET_ID,
        RULE_DQ_MISSING_COLUMN,
    }
    for spec in SLA_BY_PRIORITY.values():
        ids.add(spec.response_rule_id)
        ids.add(spec.resolve_rule_id)
    return frozenset(ids)
