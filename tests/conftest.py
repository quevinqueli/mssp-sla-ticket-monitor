from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CSV = Path(__file__).resolve().parent / "fixtures" / "hand_checked_tickets.csv"
FIXTURE_EXPECTED = Path(__file__).resolve().parent / "fixtures" / "hand_checked_expected.json"
SYNTHETIC_CSV = ROOT / "data" / "synthetic_tickets.csv"
AS_OF = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def as_of() -> datetime:
    return AS_OF
