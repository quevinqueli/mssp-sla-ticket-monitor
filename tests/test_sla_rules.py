from mssp_sla.sla_rules import (
    approaching_threshold_hours,
    is_approaching,
    normalize_priority,
)


def test_priority_aliases_are_explicit_only():
    assert normalize_priority("Critical") == "P1"
    assert normalize_priority("HIGH") == "P2"
    assert normalize_priority("medium") == "P3"
    assert normalize_priority("4") == "P4"
    # Never guessed:
    assert normalize_priority("Urgent") is None
    assert normalize_priority("P5") is None
    assert normalize_priority("Sev1") is None
    assert normalize_priority("") is None
    assert normalize_priority(None) is None


def test_approaching_thresholds_match_documented_bands():
    assert approaching_threshold_hours(0.25) == 0.125  # P1 response: last 50%
    assert approaching_threshold_hours(1.0) == 0.5  # P2 response: last 50%
    assert approaching_threshold_hours(4.0) == 1.0  # min(2, 1.0)
    assert approaching_threshold_hours(8.0) == 2.0  # min(2, 2.0)
    assert approaching_threshold_hours(24.0) == 2.0  # min(2, 6.0)
    assert approaching_threshold_hours(72.0) == 2.0  # min(2, 18.0)


def test_is_approaching_excludes_breached_and_outside_band():
    assert is_approaching(0.0, 4.0) is False
    assert is_approaching(-1.0, 4.0) is False
    assert is_approaching(0.25, 1.0) is True
    assert is_approaching(0.6, 1.0) is False
    assert is_approaching(2.0, 24.0) is True
    assert is_approaching(2.01, 24.0) is False
