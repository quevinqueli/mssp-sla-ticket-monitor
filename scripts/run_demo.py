#!/usr/bin/env python3
"""One-command demo: Phase A metrics JSON + markdown brief from synthetic tickets.

Does not call any model. No API key required.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mssp_sla.cli import main

AS_OF = (ROOT / "data" / "DEMO_AS_OF.txt").read_text(encoding="utf-8").strip()


if __name__ == "__main__":
    raise SystemExit(
        main(
            [
                "--csv",
                str(ROOT / "data" / "synthetic_tickets.csv"),
                "--as-of",
                AS_OF,
                "--out",
                str(ROOT / "artifacts"),
            ]
        )
    )
