from pathlib import Path

from mssp_sla.brief import render_brief
from mssp_sla.pipeline import build_report, write_outputs
from mssp_sla.timeutil import parse_timestamp

FIXTURE_CSV = Path(__file__).resolve().parent / "fixtures" / "hand_checked_tickets.csv"
AS_OF = parse_timestamp("2026-09-19T12:00:00Z")


def test_brief_is_plain_markdown_from_verified_numbers():
    report = build_report(FIXTURE_CSV, AS_OF)
    text = render_brief(report)
    assert text.startswith("# MSSP Daily SLA Operational Brief")
    assert "Verification: **PASSED" in text
    assert "`response_sla_breach:TCK-1001:SLA-RESPONSE-P1`" in text
    assert "Hours overdue: 1.7500h" in text or "Hours overdue: 1.75h" in text
    assert "Attention-list rows:" in text
    assert "Attention-list tickets:" not in text
    assert "CSV-row grain" in text
    assert "## Rows requiring attention" in text
    assert "AI section omitted" in text
    # Must not invent business outcomes.
    assert "revenue" not in text.lower()
    assert "customer impact score" not in text.lower()


def test_failed_verification_omits_ai_and_shows_banner(tmp_path):
    report = build_report(FIXTURE_CSV, AS_OF)
    report.verification.passed = False
    report.verification.checks = [
        {"name": "forced_fail", "passed": False, "detail": "unit-test injection"}
    ]
    write_outputs(report, tmp_path, enable_ai=True)
    brief = (tmp_path / "daily_brief.md").read_text(encoding="utf-8")
    assert "FAILED" in brief
    assert "AI section omitted" in brief or "Verification failed" in brief
    assert "unit-test injection" in brief
