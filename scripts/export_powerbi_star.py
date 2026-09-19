#!/usr/bin/env python3
"""Build Power BI star-schema CSVs and model fragments from the demo snapshot.

Uses the same Phase A clocks as scripts/run_demo.py. Does not open Power BI Desktop.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mssp_sla.powerbi_export import (  # noqa: E402
    export_demo_star,
    render_measures_dax,
    render_measures_tmdl,
    render_model_bim,
)


def main() -> int:
    os.chdir(ROOT)
    written = export_demo_star(ROOT)
    model_dir = ROOT / "powerbi" / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "measures.dax").write_text(render_measures_dax(), encoding="utf-8")
    (model_dir / "measures.tmdl").write_text(render_measures_tmdl(), encoding="utf-8")
    (model_dir / "Model.bim").write_text(render_model_bim(), encoding="utf-8")
    print("wrote:")
    for name, path in written.items():
        print(f"  {name}: {path.relative_to(ROOT)}")
    print(f"  measures.dax: {(model_dir / 'measures.dax').relative_to(ROOT)}")
    print(f"  measures.tmdl: {(model_dir / 'measures.tmdl').relative_to(ROOT)}")
    print(f"  Model.bim: {(model_dir / 'Model.bim').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
