"""Shared constants for parsing, clocks, and output rounding."""

from datetime import timezone

UTC = timezone.utc

# Round hour values so JSON / fixtures stay stable without inventing precision.
HOURS_PRECISION = 4

# Status values we treat as still open (clock may still be ticking).
OPEN_STATUSES = frozenset(
    {
        "open",
        "in_progress",
        "waiting_customer",
        "pending",
        "investigating",
    }
)

# Status values that stop the resolve clock (when resolved_at is present).
CLOSED_STATUSES = frozenset({"resolved", "closed"})

# Column names expected in the ticket CSV (see data/SCHEMA.md).
REQUIRED_COLUMNS = (
    "ticket_id",
    "created_at",
    "priority",
    "status",
)

OPTIONAL_COLUMNS = (
    "first_response_at",
    "resolved_at",
    "status_updated_at",
    "customer_id",
    "assigned_to",
    "ticket_type",
    "category",
    "summary",
)

ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
