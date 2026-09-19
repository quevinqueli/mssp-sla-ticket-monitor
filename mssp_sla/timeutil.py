"""Timestamp parsing and hour arithmetic. Invalid values are never guessed."""

from __future__ import annotations

from datetime import datetime, timedelta

from mssp_sla.constants import HOURS_PRECISION, UTC


def parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp. Empty string is None. Invalid raises ValueError."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        # Naive timestamps are ambiguous (which timezone?). Never assume UTC.
        raise ValueError("timestamp is missing a timezone offset")
    return parsed.astimezone(UTC)


def round_hours(value: float) -> float:
    return round(value, HOURS_PRECISION)


def hours_between(start: datetime, end: datetime) -> float:
    return round_hours((end - start).total_seconds() / 3600.0)


def add_hours(start: datetime, hours: float) -> datetime:
    return start + timedelta(hours=hours)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).isoformat()
