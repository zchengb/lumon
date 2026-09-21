"""Contract tests for scheduled Auto Delivery configuration."""

from __future__ import annotations

import pytest

from lumon.delivery.scheduler import launchd_timing
from lumon.errors import InvalidInputError, PreflightError
from lumon.workspace.settings import normalize_trigger_hooks, validate_schedule_expression


def test_trigger_hooks_are_normalized_and_deduplicated() -> None:
    assert normalize_trigger_hooks("jira.delivery_ready\njira.delivery_ready\n") == (
        "jira.delivery_ready",
    )


def test_schedule_expression_supports_interval_and_weekdays() -> None:
    assert launchd_timing("*/5 * * * *") == {"StartInterval": 300}
    assert launchd_timing("0 9 * * 1-5") == {
        "StartCalendarInterval": [
            {"Hour": 9, "Minute": 0, "Weekday": 1},
            {"Hour": 9, "Minute": 0, "Weekday": 2},
            {"Hour": 9, "Minute": 0, "Weekday": 3},
            {"Hour": 9, "Minute": 0, "Weekday": 4},
            {"Hour": 9, "Minute": 0, "Weekday": 5},
        ]
    }


def test_schedule_expression_rejects_unsupported_values() -> None:
    with pytest.raises(InvalidInputError):
        validate_schedule_expression("every five minutes")
    with pytest.raises(PreflightError, match="numeric minute"):
        launchd_timing("0 9-17 * * *")
