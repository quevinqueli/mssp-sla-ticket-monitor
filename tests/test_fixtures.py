"""Hand-checked fixture verification.

The expected JSON was filled in from the SLA catalog and the fixture CSV
(pencil-and-paper), then the code is required to match it. Do not regenerate
the expected file from program output without re-checking each number.
"""

from __future__ import annotations

import json
from pathlib import Path

from mssp_sla.pipeline import build_report
from mssp_sla.timeutil import parse_timestamp

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
CSV = FIXTURE_DIR / "hand_checked_tickets.csv"
EXPECTED = FIXTURE_DIR / "hand_checked_expected.json"

FLOAT_KEYS = {
    "computed_age_hours",
    "clock_elapsed_hours",
    "hours_overdue",
    "hours_remaining",
}


def _index_findings(report) -> dict[str, dict]:
    return {finding.evidence_id: finding.to_dict() for finding in report.all_findings()}


def test_hand_checked_fixture_counts_and_evidence():
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    as_of = parse_timestamp(expected["hand_checked_as_of"])
    assert as_of is not None

    report = build_report(CSV, as_of)
    assert report.verification.passed, report.verification.failed_checks
    assert report.counts == expected["counts"]

    actual = _index_findings(report)
    expected_ids = {item["evidence_id"] for item in expected["findings"]}
    assert expected_ids <= set(actual), (
        "code is missing hand-checked evidence ids: "
        f"{sorted(expected_ids - set(actual))}"
    )
    # Extra findings would mean the code is inventing cases the hand-check did not.
    assert set(actual) == expected_ids, (
        "code produced extra findings beyond the hand-check: "
        f"{sorted(set(actual) - expected_ids)}"
    )

    for spec in expected["findings"]:
        got = actual[spec["evidence_id"]]
        for key, value in spec.items():
            if key in FLOAT_KEYS:
                assert got[key] == value, f"{spec['evidence_id']}.{key}: {got[key]} != {value}"
            else:
                assert got[key] == value, f"{spec['evidence_id']}.{key}: {got[key]!r} != {value!r}"


def test_negative_controls_have_no_sla_or_attention_findings():
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    as_of = parse_timestamp(expected["hand_checked_as_of"])
    report = build_report(CSV, as_of)
    controls = set(expected["negative_controls"])
    flagged = {finding.ticket_id for finding in report.all_findings()}
    assert controls.isdisjoint(flagged), (
        f"negative-control tickets were flagged: {sorted(controls & flagged)}"
    )
