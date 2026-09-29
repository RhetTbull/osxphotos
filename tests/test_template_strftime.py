"""Test the strftime handling in osxphotos.phototemplate.

Regression tests for issue #2157: the `%s` (epoch seconds) strftime code must
reflect the datetime's own timezone rather than the machine's local timezone.
These tests are platform-independent (no Photos library needed).
"""

from __future__ import annotations

import datetime

import pytest

from osxphotos.phototemplate import _strftime, format_date_field

# 2022-05-24 14:20:00 -07:00 (California, DST active). Correct epoch seconds
# (independent of the machine timezone) is 1653427200.
_DST_DT = datetime.datetime(
    2022, 5, 24, 14, 20, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-7))
)
_CORRECT_EPOCH = "1653427200"


@pytest.fixture
def _machine_timezones(monkeypatch):
    """Run a check under several machine timezones (where tzset is available)."""
    time = pytest.importorskip("time")
    if not hasattr(time, "tzset"):
        pytest.skip("time.tzset not available on this platform")
    return time


@pytest.mark.parametrize(
    "tz_name", ["UTC", "America/Los_Angeles", "America/New_York", "Asia/Kolkata"]
)
def test_strftime_epoch_independent_of_machine_timezone(
    tz_name, monkeypatch, _machine_timezones
):
    """`%s` yields the same epoch for a tz-aware datetime regardless of machine tz."""
    time = _machine_timezones
    monkeypatch.setenv("TZ", tz_name)
    time.tzset()
    assert _strftime(_DST_DT, "%s") == _CORRECT_EPOCH


def test_strftime_epoch_matches_timestamp():
    """`%s` matches datetime.timestamp() for a tz-aware datetime."""
    assert _strftime(_DST_DT, "%s") == str(int(_DST_DT.timestamp()))


def test_strftime_epoch_in_mixed_format():
    """`%s` is substituted correctly alongside other format codes."""
    assert _strftime(_DST_DT, "%Y-%m-%d_%s") == f"2022-05-24_{_CORRECT_EPOCH}"


def test_strftime_escaped_percent_s_is_literal():
    """An escaped `%%s` is a literal percent followed by 's', not epoch seconds."""
    assert _strftime(_DST_DT, "%%s") == "%s"


def test_strftime_without_epoch_code_unchanged():
    """A format string without `%s` behaves like datetime.strftime."""
    assert _strftime(_DST_DT, "%Y-%U") == _DST_DT.strftime("%Y-%U")


def test_format_date_field_strftime_epoch():
    """format_date_field routes `%s` through the corrected handler."""
    assert format_date_field(_DST_DT, "created.strftime", ["%s"]) == _CORRECT_EPOCH


def test_format_date_field_strftime_regular_code():
    """format_date_field still handles ordinary strftime codes."""
    assert format_date_field(_DST_DT, "created.strftime", ["%Y"]) == "2022"
