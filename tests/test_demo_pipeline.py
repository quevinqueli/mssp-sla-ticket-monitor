import json
from pathlib import Path

from mssp_sla.cli import main
from mssp_sla.pipeline import build_report
from mssp_sla.timeutil import parse_timestamp

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = ROOT / "data" / "synthetic_tickets.csv"
AS_OF_TEXT = (ROOT / "data" / "DEMO_AS_OF.txt").read_text(encoding="utf-8").strip()


def test_synthetic_demo_verifies_and_writes_artifacts(tmp_path):
    as_of = parse_timestamp(AS_OF_TEXT)
    report = build_report(SYNTHETIC, as_of)
    assert report.verification.passed, report.verification.failed_checks
    assert report.counts["total_tickets"] >= 15
    assert report.counts["data_quality_flags"] >= 1
    assert report.counts["attention"] == len(report.attention_list) == 18
    attention_ids = [finding.ticket_id for finding in report.attention_list]
    # CSV-row grain: duplicate TCK-1020 is two attention rows, not one ticket.
    assert attention_ids.count("TCK-1020") == 2
    assert len(set(attention_ids)) == 17
    assert report.counts["ageing_backlog"] == 2
    assert all(finding.ticket_id != "TCK-1020" for finding in report.ageing_backlog)


    exit_code = main(
        ["--csv", str(SYNTHETIC), "--as-of", AS_OF_TEXT, "--out", str(tmp_path)]
    )
    assert exit_code == 0
    metrics = tmp_path / "metrics.json"
    brief = tmp_path / "daily_brief.md"
    assert metrics.is_file()
    assert brief.is_file()
    text = brief.read_text(encoding="utf-8")
    assert "MSSP Daily SLA Operational Brief" in text
    assert "PASSED" in text
    assert "AI section omitted" in text
    assert "Attention-list rows:" in text
    assert "Attention-list tickets:" not in text


def test_committed_sample_artifacts_are_verified_phase_a():
    metrics_path = ROOT / "artifacts" / "metrics.json"
    brief_path = ROOT / "artifacts" / "daily_brief.md"
    assert metrics_path.is_file(), "run python3 scripts/run_demo.py to refresh artifacts/"
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert payload["meta"]["verification"]["passed"]
    assert payload["meta"]["source_csv"] == "data/synthetic_tickets.csv"
    assert payload["counts"]["attention"] == 18
    assert payload["counts"]["ageing_backlog"] == 2
    text = brief_path.read_text(encoding="utf-8")
    assert "PASSED" in text
    assert "AI section omitted" in text
    assert "Attention-list rows:" in text
    assert "Attention-list tickets:" not in text
    assert any(
        finding["ticket_id"] == "TCK-1020" and finding["finding_type"] == "attention"
        for finding in payload["attention_list"]
    )
    assert all(finding["ticket_id"] != "TCK-1020" for finding in payload["ageing_backlog"])

