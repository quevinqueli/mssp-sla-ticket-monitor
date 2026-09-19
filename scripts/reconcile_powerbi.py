#!/usr/bin/env python3
"""Recompute Power BI KPI values from the star CSVs and compare to Phase A.

Prints a markdown table. Exit 1 on mismatch. Does not run Power BI Desktop.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mssp_sla.pipeline import build_report  # noqa: E402
from mssp_sla.powerbi_export import build_model  # noqa: E402
from mssp_sla.timeutil import parse_timestamp  # noqa: E402


def _md_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def render_markdown(model: dict) -> str:
    expected = model["expected_measures"]
    python = expected["python_counts"]
    page = expected["report_page_measures"]
    aligned = expected["python_aligned_measures"]
    lines = [
        "# Power BI ↔ Python reconciliation",
        "",
        f"- Snapshot: `{expected['as_of']}`",
        f"- Source: `{expected['source_csv']}`",
        f"- Filters: {expected['filters']}",
        f"- Phase A verification: **{'PASSED' if model['verification_passed'] else 'FAILED'}**",
        "",
        "Report-page KPIs are ticket-row counts with a breached > approaching > ageing "
        "exclusion so a ticket is not in two of those three cards. Python list lengths "
        "are shown beside them. Intentional deltas are documented below.",
        "",
        _md_row(["Report measure", "Report value", "Python analog", "Python value", "Match?"]),
        _md_row(["---", "---:", "---", "---:", "---"]),
        _md_row(
            [
                "Open tickets",
                str(page["Open tickets"]),
                "`counts.open_tickets`",
                str(python["open_tickets"]),
                "yes" if page["Open tickets"] == python["open_tickets"] else "no",
            ]
        ),
        _md_row(
            [
                "Breached tickets",
                str(page["Breached tickets"]),
                "`counts.breached_slas` (findings)",
                str(python["breached_slas"]),
                "intentional delta"
                if page["Breached tickets"] != python["breached_slas"]
                else "yes",
            ]
        ),
        _md_row(
            [
                "Approaching tickets",
                str(page["Approaching tickets"]),
                "`counts.approaching_deadlines`",
                str(python["approaching_deadlines"]),
                "yes"
                if page["Approaching tickets"] == python["approaching_deadlines"]
                else "no",
            ]
        ),
        _md_row(
            [
                "Ageing backlog",
                str(page["Ageing backlog"]),
                "`counts.ageing_backlog`",
                str(python["ageing_backlog"]),
                "intentional delta"
                if page["Ageing backlog"] != python["ageing_backlog"]
                else "yes",
            ]
        ),
        _md_row(
            [
                "Breached findings (Python-aligned)",
                str(aligned["Breached findings (Python-aligned)"]),
                "`counts.breached_slas`",
                str(python["breached_slas"]),
                "yes"
                if aligned["Breached findings (Python-aligned)"] == python["breached_slas"]
                else "no",
            ]
        ),
        _md_row(
            [
                "Ageing backlog (Python-aligned)",
                str(aligned["Ageing backlog (Python-aligned)"]),
                "`counts.ageing_backlog`",
                str(python["ageing_backlog"]),
                "yes"
                if aligned["Ageing backlog (Python-aligned)"] == python["ageing_backlog"]
                else "no",
            ]
        ),
        _md_row(
            [
                "Attention tickets (Python-aligned)",
                str(aligned["Attention tickets (Python-aligned)"]),
                "`counts.attention`",
                str(python["attention"]),
                "yes"
                if aligned["Attention tickets (Python-aligned)"] == python["attention"]
                else "no",
            ]
        ),
        "",
        "## Breached tickets by client (bar chart)",
        "",
        _md_row(["Client", "Breached tickets"]),
        _md_row(["---", "---:"]),
    ]
    for client, count in expected["breached_tickets_by_client"].items():
        lines.append(_md_row([client, str(count)]))
    lines.extend(
        [
            "",
            f"Bar total: **{sum(expected['breached_tickets_by_client'].values())}** "
            f"(must equal Breached tickets = {page['Breached tickets']}).",
            "",
            "## Action table by primary reason",
            "",
            f"Rows: **{expected['action_table_rows']}**",
            "",
            _md_row(["Primary reason", "Rows"]),
            _md_row(["---", "---:"]),
        ]
    )
    for reason, count in expected["action_table_by_primary_reason"].items():
        lines.append(_md_row([reason, str(count)]))
    lines.extend(["", "## Intentional deltas", ""])
    for delta in expected["intentional_deltas"]:
        lines.append(
            f"- **{delta['measure']}**: report `{delta['report_value']}` vs "
            f"Python `{delta['python_name']}` = `{delta['python_value']}`. "
            f"{delta['reason']}"
        )
    lines.extend(
        [
            "",
            "## Cross-KPI exclusivity",
            "",
            "A row may contribute to **Open tickets** and at most one of "
            "Breached / Approaching / Ageing.",
            "",
        ]
    )
    violations = expected["exclusive_kpi_overlap_violations"]
    if violations:
        lines.append("Overlapping exclusive flags (should be empty): " + ", ".join(violations))
    else:
        lines.append("No row has more than one of `kpi_breached`, `kpi_approaching`, `kpi_ageing`.")
    lines.extend(
        [
            "",
            "## Trends",
            "",
            "Not included. " + expected["trends_reason"],
            "",
            "## Desktop validation",
            "",
            "These numbers are computed in Python from the same flags the DAX counts. "
            "They were **not** refreshed or visually checked in Power BI Desktop.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write powerbi/RECONCILIATION.md from the live model.",
    )
    args = parser.parse_args(argv)
    os.chdir(ROOT)
    as_of = parse_timestamp((ROOT / "data" / "DEMO_AS_OF.txt").read_text(encoding="utf-8").strip())
    csv_path = ROOT / "data" / "synthetic_tickets.csv"
    report = build_report(csv_path, as_of)
    model = build_model(csv_path, as_of)
    expected = model["expected_measures"]
    mismatches: list[str] = []
    if expected["python_counts"] != report.counts:
        mismatches.append(f"python_counts {expected['python_counts']} != {report.counts}")
    if expected["python_aligned_measures"]["Breached findings (Python-aligned)"] != report.counts["breached_slas"]:
        mismatches.append("python-aligned breached findings mismatch")
    if expected["python_aligned_measures"]["Ageing backlog (Python-aligned)"] != report.counts["ageing_backlog"]:
        mismatches.append("python-aligned ageing mismatch")
    if expected["python_aligned_measures"]["Attention tickets (Python-aligned)"] != report.counts["attention"]:
        mismatches.append("python-aligned attention mismatch")
    if expected["python_aligned_measures"]["Open tickets (Python-aligned)"] != report.counts["open_tickets"]:
        mismatches.append("python-aligned open mismatch")
    if expected["exclusive_kpi_overlap_violations"]:
        mismatches.append(
            "exclusive KPI overlap: " + str(expected["exclusive_kpi_overlap_violations"])
        )
    bar_total = sum(expected["breached_tickets_by_client"].values())
    if bar_total != expected["report_page_measures"]["Breached tickets"]:
        mismatches.append("bar chart total != breached tickets KPI")

    text = render_markdown(model)
    print(text)
    if args.write:
        path = ROOT / "powerbi" / "RECONCILIATION.md"
        path.write_text(text, encoding="utf-8")
        print(f"\nwrote {path.relative_to(ROOT)}", file=sys.stderr)
    frozen = ROOT / "powerbi" / "data" / "expected_measures.json"
    if frozen.is_file():
        payload = json.loads(frozen.read_text(encoding="utf-8"))
        if payload != expected:
            mismatches.append("committed powerbi/data/expected_measures.json is stale; re-run export")
    if mismatches:
        print("reconciliation failed:", file=sys.stderr)
        for item in mismatches:
            print(f"  - {item}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
