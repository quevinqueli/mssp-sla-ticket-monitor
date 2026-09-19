import json

from mssp_sla.ai_brief import generate_ai_section, validate_ai_payload
from mssp_sla.models import Finding, MetricsReport, VerificationResult


def _report(*, passed: bool = True) -> MetricsReport:
    finding = Finding(
        evidence_id="response_sla_breach:TCK-1001:SLA-RESPONSE-P1",
        ticket_id="TCK-1001",
        finding_type="response_sla_breach",
        rule_id="SLA-RESPONSE-P1",
        why_it_qualifies="hand-built for gate tests",
        computed_deadline="2026-09-19T10:15:00+00:00",
        hours_overdue=1.75,
    )
    return MetricsReport(
        as_of="2026-09-19T12:00:00+00:00",
        source_csv="tests/fixtures/hand_checked_tickets.csv",
        sla_catalog_version="v1",
        row_count=1,
        eligible_for_sla=1,
        counts={"breached_slas": 1, "attention": 0, "total_tickets": 1},
        data_quality_findings=[],
        breached_slas=[finding],
        approaching_deadlines=[],
        ageing_backlog=[],
        attention_list=[],
        verification=VerificationResult(
            passed=passed,
            checks=[{"name": "unit", "passed": passed, "detail": "ok"}],
        ),
        generated_at="2026-09-19T12:00:00+00:00",
    )


def test_ai_is_skipped_when_verification_fails():
    section, reason = generate_ai_section(
        _report(passed=False),
        api_key="sk-test",
        llm_call=lambda **_kwargs: '{"narrative": "should not run"}',
    )
    assert section is None
    assert reason == "verification_failed"


def test_ai_is_skipped_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MSSP_SLA_AI_API_KEY", raising=False)
    section, reason = generate_ai_section(_report(passed=True))
    assert section is None
    assert reason == "no_api_key"


def test_ai_rejects_invented_evidence_and_ticket_ids():
    report = _report()
    invented = {
        "narrative": "TCK-9999 will cost the customer $2M",
        "recommended_actions": [
            {
                "evidence_ids": ["response_sla_breach:TCK-FAKE:SLA-RESPONSE-P1"],
                "action": "page the CEO",
                "rationale": "invented",
            }
        ],
        "refusals": [],
    }
    problems = validate_ai_payload(report, invented)
    assert any("unknown evidence_id" in item for item in problems)
    assert any("unknown ticket id" in item for item in problems)

    def _llm(_messages=None, **_kwargs):
        return json.dumps(invented)

    section, reason = generate_ai_section(report, llm_call=_llm)
    assert section is None
    assert reason is not None and reason.startswith("model_invented_or_ungrounded")


def test_ai_accepts_grounded_actions_that_cite_phase_a():
    report = _report()
    grounded = {
        "narrative": "TCK-1001 breached the P1 response SLA (see evidence).",
        "recommended_actions": [
            {
                "evidence_ids": ["response_sla_breach:TCK-1001:SLA-RESPONSE-P1"],
                "action": "Have the on-call analyst respond to TCK-1001 now.",
                "rationale": "Verified 1.75h overdue against SLA-RESPONSE-P1.",
            }
        ],
        "refusals": [
            "No customer financial impact is present in the metrics JSON."
        ],
    }

    def _llm(_messages=None, **_kwargs):
        return json.dumps(grounded)

    section, reason = generate_ai_section(report, llm_call=_llm)
    assert reason is None
    assert section is not None
    assert "response_sla_breach:TCK-1001:SLA-RESPONSE-P1" in section
    assert "1.75h overdue" in section
