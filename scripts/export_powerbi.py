#!/usr/bin/env python3
"""Export Power BI star-schema CSVs from the same frozen demo as scripts/run_demo.py.

Does not call any model. Does not change artifacts/metrics.json or daily_brief.md.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mssp_sla.timeutil import parse_timestamp
from powerbi.build_export import DEFAULT_CSV, DEFAULT_OUT, export_powerbi

AS_OF = (ROOT / "data" / "DEMO_AS_OF.txt").read_text(encoding="utf-8").strip()


if __name__ == "__main__":
    os.chdir(ROOT)
    as_of = parse_timestamp(AS_OF)
    if as_of is None:
        raise SystemExit("error: data/DEMO_AS_OF.txt is empty")
    paths = export_powerbi(DEFAULT_CSV, as_of, DEFAULT_OUT)
    print(f"as_of: {AS_OF}")
    print(f"source_csv: {DEFAULT_CSV.relative_to(ROOT)}")
    print("wrote:")
    for name in sorted(paths):
        print(f"  {paths[name].relative_to(ROOT)}")
