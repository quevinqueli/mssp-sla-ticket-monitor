from mssp_sla.parse import parse_row
from mssp_sla.sla_rules import (
    RULE_DQ_AMBIGUOUS_TIMESTAMP,
    RULE_DQ_AMBIGUOUS_WAIT_CLOCK,
    RULE_DQ_MISSING_CREATED_AT,
    RULE_DQ_MISSING_RESOLVED_AT,
    RULE_DQ_TIMELINE_INCONSISTENT,
    RULE_DQ_UNKNOWN_PRIORITY,
)


def _row(**overrides):
    base = {
        "ticket_id": "TCK-TEST",
        "created_at": "2026-09-19T10:00:00Z",
        "first_response_at": "",
        "resolved_at": "",
        "status_updated_at": "",
        "priority": "P1",
        "status": "open",
        "customer_id": "CUST-X",
        "assigned_to": "alex",
        "ticket_type": "incident",
        "category": "malware",
        "summary": "synthetic",
    }
    base.update(overrides)
    return base


def test_unknown_priority_is_flagged_and_not_sla_eligible():
    ticket = parse_row(_row(priority="Urgent"), 2)
    assert ticket.priority_normalized is None
    assert ticket.sla_eligible is False
    assert any(flag.rule_id == RULE_DQ_UNKNOWN_PRIORITY for flag in ticket.flags)


def test_missing_created_at_is_flagged():
    ticket = parse_row(_row(created_at=""), 2)
    assert ticket.created_at is None
    assert ticket.sla_eligible is False
    assert any(flag.rule_id == RULE_DQ_MISSING_CREATED_AT for flag in ticket.flags)


def test_naive_timestamp_is_ambiguous_not_assumed_utc():
    ticket = parse_row(_row(created_at="2026-09-19T10:00:00"), 2)
    assert ticket.created_at is None
    assert any(flag.rule_id == RULE_DQ_AMBIGUOUS_TIMESTAMP for flag in ticket.flags)
    assert ticket.sla_eligible is False


def test_closed_without_resolved_at_skips_resolve_clock_only():
    ticket = parse_row(
        _row(
            first_response_at="2026-09-19T10:05:00Z",
            status="closed",
            resolved_at="",
        ),
        2,
    )
    assert ticket.response_sla_eligible is True
    assert ticket.resolve_sla_eligible is False
    assert any(flag.rule_id == RULE_DQ_MISSING_RESOLVED_AT for flag in ticket.flags)


def test_waiting_without_status_updated_at_is_ambiguous_but_resolve_still_eligible():
    ticket = parse_row(_row(status="waiting_customer"), 2)
    assert any(flag.rule_id == RULE_DQ_AMBIGUOUS_WAIT_CLOCK for flag in ticket.flags)
    assert ticket.resolve_sla_eligible is True


def test_inverted_timeline_skips_sla():
    ticket = parse_row(
        _row(first_response_at="2026-09-19T09:00:00Z"),
        2,
    )
    assert ticket.response_sla_eligible is False
    assert ticket.resolve_sla_eligible is False
    assert any(flag.rule_id == RULE_DQ_TIMELINE_INCONSISTENT for flag in ticket.flags)
