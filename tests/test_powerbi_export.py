"""Power BI export stays in lockstep with Phase A metrics for the frozen demo."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from mssp_sla.pipeline import build_report
from mssp_sla.timeutil import parse_timestamp
from powerbi.build_export import DEFAULT_CSV, DEFAULT_OUT, build_tables, export_powerbi, write_tables

ROOT = Path(__file__).resolve().parents[1]
AS_OF_TEXT = (ROOT / "data" / "DEMO_AS_OF.txt").read_text(encoding="utf-8").strip()
COMMITTED_METRICS = ROOT / "artifacts" / "metrics.json"


def _as_of():
    parsed = parse_timestamp(AS_OF_TEXT)
    assert parsed is not None
    return parsed


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_export_kpis_match_python_metrics_json(tmp_path):
    as_of = _as_of()
    report = build_report(DEFAULT_CSV, as_of)
    assert report.verification.passed, report.verification.failed_checks
    tables = build_tables(DEFAULT_CSV, as_of)
    kpis = tables["_kpis"][0]
    dash = kpis["dashboard_unfiltered"]
    counts = report.counts

    assert dash["total_tickets_row_grain"] == counts["total_tickets"] == 27
    assert dash["sla_eligible_row_grain"] == counts["sla_eligible"] == 19
    assert dash["open_tickets_row_grain"] == counts["open_tickets"] == 22
    assert dash["breached_slas_finding_grain"] == counts["breached_slas"] == 8
    assert dash["approaching_deadlines_finding_grain"] == counts["approaching_deadlines"] == 3
    assert dash["ageing_backlog_finding_grain"] == counts["ageing_backlog"] == 3
    assert dash["attention_row_grain"] == counts["attention"] == 18
    assert dash["data_quality_flags_finding_grain"] == counts["data_quality_flags"] == 10

    # Ticket-level KPIs must not double-count TCK-1021's two breach findings.
    assert dash["breached_tickets_distinct"] == 7
    assert {"TCK-1021"} == {
        row["ticket_id"]
        for row in tables["FactFindings"]
        if row["finding_family"] == "sla_breach" and row["ticket_id"] == "TCK-1021"
    }
    tck_1021_findings = [
        row for row in tables["FactFindings"] if row["ticket_id"] == "TCK-1021" and row["finding_family"] == "sla_breach"
    ]
    assert len(tck_1021_findings) == 2

    # Duplicate ticket_id is two DimTicket rows; Python open_tickets counts both.
    tck_1020 = [row for row in tables["DimTicket"] if row["ticket_id"] == "TCK-1020"]
    assert len(tck_1020) == 2
    assert dash["open_ticket_ids_distinct"] == 21
    assert dash["attention_ticket_ids_distinct"] == 17

    assert kpis["breached_tickets_by_client"] == {"CUST-A": 4, "CUST-C": 3}
    assert kpis["slicer_client_CUST_C"] == {
        "open_tickets_row_grain": 5,
        "breached_slas_finding_grain": 4,
        "breached_tickets_distinct": 3,
        "attention_row_grain": 5,
    }
    assert kpis["synthetic_flag"] is True
    assert kpis["verification_passed"] is True
    assert tables["SnapshotMeta"][0]["synthetic_flag"] == 1
    assert tables["SnapshotMeta"][0]["verification_passed"] == 1
    assert tables["SnapshotMeta"][0]["as_of"] == report.as_of

    write_tables(tables, tmp_path)
    assert (tmp_path / "DimTicket.csv").is_file()
    assert (tmp_path / "expected_kpis.json").is_file()


def test_attention_deadline_comes_from_linked_sla_evidence_not_double_counted():
    tables = build_tables(DEFAULT_CSV, _as_of())
    attention = {row["evidence_id"]: row for row in tables["FactAttention"]}

    tck_1021 = attention["attention:TCK-1021"]
    assert tck_1021["linked_deadline"] == "2026-09-19T04:15:00+00:00"
    assert tck_1021["linked_deadline_source"] == "response_sla_breach:TCK-1021:SLA-RESPONSE-P1"
    assert "open ticket has at least one SLA breach" in tck_1021["reason_for_attention"]
    assert "empty assigned_to" in tck_1021["reason_for_attention"]

    tck_1005 = attention["attention:TCK-1005"]
    assert tck_1005["linked_deadline"] == "2026-09-19T12:15:00+00:00"
    assert tck_1005["linked_deadline_kind"] == "approaching_response"

    tck_1007 = attention["attention:TCK-1007"]
    assert tck_1007["linked_deadline"] == ""
    assert tck_1007["reason_rule_ids"] == "ATTENTION-DATA-QUALITY"


def test_committed_powerbi_csvs_match_frozen_pipeline():
    as_of = _as_of()
    tables = build_tables(DEFAULT_CSV, as_of)
    committed_ticket = _read_csv(DEFAULT_OUT / "DimTicket.csv")
    assert [row["ticket_id"] for row in committed_ticket] == [
        str(row["ticket_id"]) for row in tables["DimTicket"]
    ]
    assert len(committed_ticket) == 27

    committed_findings = _read_csv(DEFAULT_OUT / "FactFindings.csv")
    assert len(committed_findings) == (
        8 + 3 + 3 + 10
    )
    committed_attention = _read_csv(DEFAULT_OUT / "FactAttention.csv")
    assert len(committed_attention) == 18

    meta = _read_csv(DEFAULT_OUT / "SnapshotMeta.csv")
    assert meta[0]["synthetic_flag"] == "1"
    assert meta[0]["verification_passed"] == "1"
    assert meta[0]["as_of"] == tables["SnapshotMeta"][0]["as_of"]

    expected = json.loads((DEFAULT_OUT / "expected_kpis.json").read_text(encoding="utf-8"))
    assert expected["dashboard_unfiltered"] == tables["_kpis"][0]["dashboard_unfiltered"]
    assert expected["python_counts"] == tables["_kpis"][0]["python_counts"]

    payload = json.loads(COMMITTED_METRICS.read_text(encoding="utf-8"))
    assert payload["counts"] == expected["python_counts"]
    assert payload["meta"]["verification"]["passed"] is True


def test_export_script_writes_all_tables(tmp_path):
    paths = export_powerbi(DEFAULT_CSV, _as_of(), tmp_path)
    for name in (
        "DimTicket",
        "DimClient",
        "DimPriority",
        "DimStatus",
        "FactFindings",
        "FactAttention",
        "SnapshotMeta",
        "expected_kpis",
    ):
        assert name in paths
        assert paths[name].is_file()
