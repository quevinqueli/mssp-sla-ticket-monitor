"""Command-line entry for the daily SLA brief."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from mssp_sla.pipeline import build_report, write_outputs
from mssp_sla.timeutil import parse_timestamp


def parse_as_of(value: str) -> datetime:
    try:
        parsed = parse_timestamp(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if parsed is None:
        raise argparse.ArgumentTypeError("as-of timestamp is empty")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic MSSP ticket SLA daily brief (Phase A). "
            "Optional Phase B AI runs only after verification passes."
        )
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to the ticket CSV (synthetic demo: data/synthetic_tickets.csv)",
    )
    parser.add_argument(
        "--as-of",
        required=True,
        type=parse_as_of,
        help="Timezone-aware ISO-8601 instant used as 'now' (example: 2026-09-19T12:00:00Z)",
    )
    parser.add_argument(
        "--out",
        default="artifacts",
        help="Directory for metrics.json and daily_brief.md (default: artifacts)",
    )
    parser.add_argument(
        "--ai",
        action="store_true",
        help=(
            "Opt in to Phase B. Requires MSSP_SLA_AI_API_KEY or OPENAI_API_KEY. "
            "Ignored/withheld if verification fails."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"error: CSV not found: {csv_path}", file=sys.stderr)
        return 2

    report = build_report(csv_path, args.as_of)
    paths = write_outputs(report, args.out, enable_ai=args.ai)

    status = "PASSED" if report.verification.passed else "FAILED"
    print(f"verification: {status}")
    print(f"metrics: {paths['metrics']}")
    print(f"brief:   {paths['brief']}")
    if not report.verification.passed:
        for check in report.verification.failed_checks:
            print(f"  failed check: {check['name']}: {check['detail']}", file=sys.stderr)
        return 1
    return 0
