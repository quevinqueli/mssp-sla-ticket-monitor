from datetime import datetime, timezone

from mssp_sla.compute import (
    compute_ageing_backlog,
    compute_approaching_deadlines,
    compute_breached_slas,
    resolve_clock,
    response_clock,
)
from mssp_sla.parse import parse_row
from mssp_sla.sla_rules import AGEING_BACKLOG_HOURS

AS_OF = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)


def _ticket(**overrides):
    base = {
        "ticket_id": "TCK-UNIT",
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
    return parse_row(base, 2)


def test_p1_unanswered_response_breach_math():
    ticket = _ticket()
    clock = response_clock(ticket, AS_OF)
    assert clock is not None
    assert clock.breached is True
    assert clock.overdue_hours == 1.75
    assert clock.elapsed_hours == 2.0
    findings = compute_breached_slas([ticket], AS_OF)
    assert [item.finding_type for item in findings] == ["response_sla_breach"]
    assert findings[0].computed_deadline == "2026-09-19T10:15:00+00:00"


def test_on_time_response_is_not_a_breach():
    ticket = _ticket(first_response_at="2026-09-19T10:10:00Z")
    clock = response_clock(ticket, AS_OF)
    assert clock is not None
    assert clock.breached is False
    assert clock.elapsed_hours == 0.1667
    assert compute_breached_slas([ticket], AS_OF) == []


def test_waiting_customer_does_not_pause_resolve_clock():
    ticket = _ticket(
        created_at="2026-09-19T06:00:00Z",
        first_response_at="2026-09-19T06:05:00Z",
        status="waiting_customer",
        status_updated_at="2026-09-19T07:00:00Z",
    )
    clock = resolve_clock(ticket, AS_OF)
    assert clock is not None
    assert clock.breached is True
    assert clock.overdue_hours == 2.0  # deadline 10:00, as_of 12:00
    why = compute_breached_slas([ticket], AS_OF)[0].why_it_qualifies
    assert "does not pause" in why


def test_approaching_uses_warn_band_not_entire_window():
    # P2 created 11:15, unanswered, 15 minutes remain of a 1h SLA (band = 30m).
    ticket = _ticket(
        created_at="2026-09-19T11:15:00Z",
        priority="P2",
    )
    approaching = compute_approaching_deadlines([ticket], AS_OF)
    assert len(approaching) == 1
    assert approaching[0].finding_type == "approaching_response"
    assert approaching[0].hours_remaining == 0.25

    # Created 11:30: 30 minutes remain — exactly the 50% warn-band edge (included).
    edge = _ticket(created_at="2026-09-19T11:30:00Z", priority="P2")
    edge_findings = compute_approaching_deadlines([edge], AS_OF)
    assert [item.hours_remaining for item in edge_findings] == [0.5]

    # Created 11:00: remaining 1.0h (full P2 response window) is outside the warn band.
    early = _ticket(created_at="2026-09-19T11:00:00Z", priority="P2")
    assert compute_approaching_deadlines([early], AS_OF) == []


def test_ageing_backlog_is_independent_of_sla():
    ticket = _ticket(
        created_at="2026-09-17T12:00:00Z",
        first_response_at="2026-09-17T16:00:00Z",
        priority="P4",
    )
    ageing = compute_ageing_backlog([ticket], AS_OF)
    assert len(ageing) == 1
    assert ageing[0].computed_age_hours == AGEING_BACKLOG_HOURS
    # Resolve SLA for P4 is 72h, so this 48h ticket is ageing but not resolve-breached.
    assert compute_breached_slas([ticket], AS_OF) == []
