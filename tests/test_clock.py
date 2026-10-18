"""Test `shared.clock.py`.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

import datetime as dt

import pytest

from shared import clock

ANCHOR = dt.datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt.UTC)


@pytest.mark.parametrize(
    ("td", "mode", "expected"),
    [
        (dt.timedelta(hours=2, seconds=66), "full", "2 hours 1 minute 6 seconds"),
        (dt.timedelta(hours=2, seconds=66), "short", "2 hrs 1 min 6 sec"),
        (dt.timedelta(hours=2, seconds=66), "letter", "02h01m06s"),
        (dt.timedelta(seconds=5), "letter", "05s"),
        (dt.timedelta(hours=1, seconds=5), "letter", "01h00m05s"),
        (dt.timedelta(days=0), "letter", "00s"),
    ],
)
def test_human_timedelta(td: dt.timedelta, mode: clock.HumanTimedeltaMode, expected: str) -> None:
    """Test `clock.human_timedelta`."""
    assert clock.human_timedelta(td, mode=mode) == expected


@pytest.mark.parametrize(
    ("when", "mode", "expected"),
    [
        (ANCHOR + dt.timedelta(hours=2, seconds=66), "full", "2 hours 1 minute 6 seconds"),
        (ANCHOR + dt.timedelta(hours=2, seconds=66), "short", "2 hrs 1 min 6 sec"),
        (ANCHOR + dt.timedelta(hours=2, seconds=66), "letter", "02h01m06s"),
        (ANCHOR + dt.timedelta(seconds=5), "letter", "05s"),
        (ANCHOR + dt.timedelta(hours=1, seconds=5), "letter", "01h00m05s"),
        (ANCHOR, "letter", "00s"),
    ],
)
def test_human_datetime_diff(when: dt.datetime, mode: clock.HumanTimedeltaMode, expected: str) -> None:
    """Test `clock.human_datetime_diff`."""
    assert clock.human_datetime_diff(when, relative_to=ANCHOR, mode=mode) == expected
