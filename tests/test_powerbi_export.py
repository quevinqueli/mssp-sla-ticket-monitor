"""Star-schema flags and KPI values must stay aligned with Phase A."""

from __future__ import annotations

import json
from pathlib import Path

from mssp_sla.pipeline import build_report
from mssp_sla.powerbi_export import (
    TABLE_SCHEMAS,
    build_model,
    write_star,
)
from mssp_sla.timeutil import parse_timestamp

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = ROOT / "data" / "synthetic_tickets.csv"
AS_OF_TEXT = (ROOT / "data" / "DEMO_AS_OF.txt").read_text(encoding="utf-8").strip()
POWERBI_DATA = ROOT / "powerbi" / "data"


def _model():
    as_of = parse_timestamp(AS_OF_TEXT)
    return build_model(SYNTHETIC, as_of), build_report(SYNTHETIC, as_of)


def test_demo_kpis_match_documented_snapshot():
    model, report = _model()
    expected = model["expected_measures"]
    page = expected["report_page_measures"]
    aligned = expected["python_aligned_measures"]

    assert report.verification.passed
    assert report.counts["open_tickets"] == 22
    assert report.counts["breached_slas"] == 8
    assert report.counts["approaching_deadlines"] == 3
    assert report.counts["ageing_backlog"] == 2
    assert report.counts["attention"] == 18

    assert page["Open tickets"] == 22
    assert page["Breached tickets"] == 7
    assert page["Approaching tickets"] == 3
    assert page["Ageing backlog"] == 1

    assert aligned["Breached findings (Python-aligned)"] == 8
    assert aligned["Approaching findings (Python-aligned)"] == 3
    assert aligned["Ageing backlog (Python-aligned)"] == 2
    assert aligned["Attention tickets (Python-aligned)"] == 18
    assert aligned["Open tickets (Python-aligned)"] == 22

    assert expected["breached_tickets_by_client"] == {"CUST-A": 4, "CUST-C": 3}
    assert expected["exclusive_kpi_overlap_violations"] == []


def test_tck_1004_counts_as_breached_not_ageing_kpi():
    model, _report = _model()
    rows = [row for row in model["fact_ticket"] if row["ticket_id"] == "TCK-1004"]
    assert len(rows) == 1
    row = rows[0]
    assert row["kpi_breached"] == 1
    assert row["kpi_ageing"] == 0
    assert row["kpi_ageing_python"] == 1
    assert row["primary_reason_key"] == "BREACHED_OPEN"


def test_tck_1021_is_one_breached_ticket_not_two():
    model, _report = _model()
    rows = [row for row in model["fact_ticket"] if row["ticket_id"] == "TCK-1021"]
    assert len(rows) == 1
    assert rows[0]["response_breached"] == 1
    assert rows[0]["resolve_breached"] == 1
    assert rows[0]["kpi_breached"] == 1


def test_tck_1020_duplicates_are_dq_only_not_ageing():
    model, _report = _model()
    rows = [row for row in model["fact_ticket"] if row["ticket_id"] == "TCK-1020"]
    assert len(rows) == 2
    for row in rows:
        assert row["is_ageing"] == 0
        assert row["kpi_ageing"] == 0
        assert row["kpi_ageing_python"] == 0
        assert row["is_python_attention"] == 1
        assert row["primary_reason_key"] == "DATA_QUALITY"
        assert "DQ-DUPLICATE-TICKET-ID" in row["dq_rule_ids"]



def test_ageing_only_and_p3_approaching_still_reach_the_table():
    model, _report = _model()
    by_id = {row["ticket_id"]: row for row in model["fact_ticket"] if row["ticket_id"] != "TCK-1020"}
    # Duplicate TCK-1020 handled separately.
    assert by_id["TCK-1006"]["in_action_table"] == 1
    assert by_id["TCK-1006"]["is_python_attention"] == 0
    assert by_id["TCK-1006"]["primary_reason_key"] == "AGEING"
    assert by_id["TCK-1010"]["in_action_table"] == 1
    assert by_id["TCK-1010"]["is_python_attention"] == 0
    assert by_id["TCK-1010"]["primary_reason_key"] == "APPROACHING"


def test_negative_controls_are_not_in_the_action_table():
    model, _report = _model()
    controls = {"TCK-1002", "TCK-1011", "TCK-1016", "TCK-1018", "TCK-1022", "TCK-1023", "TCK-1025"}
    flagged = {
        row["ticket_id"]
        for row in model["fact_ticket"]
        if row["ticket_id"] in controls and int(row["in_action_table"])
    }
    assert flagged == set()


def test_committed_star_files_match_live_export(tmp_path):
    model, _report = _model()
    written = write_star(model, tmp_path)
    frozen = json.loads((POWERBI_DATA / "expected_measures.json").read_text(encoding="utf-8"))
    live = json.loads(written["expected_measures"].read_text(encoding="utf-8"))
    assert frozen == live
    for table_name, fields in TABLE_SCHEMAS.items():
        committed = (POWERBI_DATA / f"{table_name}.csv").read_text(encoding="utf-8")
        fresh = (tmp_path / f"{table_name}.csv").read_text(encoding="utf-8")
        assert committed == fresh
        header = committed.splitlines()[0].split(",")
        assert header == fields


def test_fact_ticket_row_count_matches_python_total():
    model, report = _model()
    assert len(model["fact_ticket"]) == report.counts["total_tickets"] == 27
    assert sum(int(row["kpi_open"]) for row in model["fact_ticket"]) == 22
    assert len(model["fact_finding"]) == len(report.all_findings()) == 41


def test_documented_slicer_smoke_numbers():
    model, _report = _model()
    rows = model["fact_ticket"]

    def kpis(pred):
        sub = [row for row in rows if pred(row)]
        return (
            sum(int(row["kpi_open"]) for row in sub),
            sum(int(row["kpi_breached"]) for row in sub),
            sum(int(row["kpi_approaching"]) for row in sub),
            sum(int(row["kpi_ageing"]) for row in sub),
        )

    assert kpis(lambda r: r["status_key"] == "resolved") == (0, 2, 0, 0)
    assert kpis(lambda r: r["client_key"] == "CUST-A") == (4, 4, 0, 0)
    assert kpis(lambda r: r["priority_key"] == "P1") == (5, 4, 1, 0)
