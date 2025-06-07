"""Test timezones.py"""

import datetime
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from osxphotos.platform import is_macos
from osxphotos.timezones import convert_offset_timezone_to_etc, format_offset_time

if is_macos:
    from osxphotos.timezones import Timezone, known_timezone_names


@pytest.mark.skipif(not is_macos, reason="macOS only")
def test_known_timezone_names():
    """Test known_timezone_names function on macOS platforms."""
    timezones = known_timezone_names()
    assert "America/New_York" in timezones


@pytest.mark.skipif(not is_macos, reason="macOS only")
def test_timezone_by_zone_name():
    """Test Timezone creation on macOS by zone name."""
    tz = Timezone("America/New_York")
    assert tz.name == "America/New_York"
    assert isinstance(tz.tzinfo(datetime.datetime.now()), ZoneInfo)


@pytest.mark.skipif(not is_macos, reason="macOS only")
def test_timezone_by_offset():
    """Test Timezone creation on macOS with an offset from GMT."""
    tz = Timezone(-18000)  # UTC -5 hours
    assert tz.name == "GMT-0500"
    assert tz.offset == -18000
    assert tz.offset_str == "-05:00"
    assert isinstance(tz.tzinfo(datetime.datetime.now()), ZoneInfo)


@pytest.mark.skipif(not is_macos, reason="macOS only")
def test_timezone_invalid_zone():
    """Test that Timezone creation fails with an invalid zone name."""
    with pytest.raises(ValueError, match="Invalid timezone: Invalid/Zone"):
        Timezone("Invalid/Zone")


@pytest.mark.skipif(not is_macos, reason="macOS only")
def test_timezone_invalid_offset():
    """Test that Timezone creation fails with bad input type."""
    with pytest.raises(TypeError, match="Timezone must be a string or an int"):
        Timezone(None)  # Invalid offset input


@pytest.mark.skipif(not is_macos, reason="macOS only")
def test_timezone_offset_by_date():
    """Test Timezone.offset_by_date method."""
    tz = Timezone("America/New_York")
    assert tz.offset_for_date(datetime.datetime(2021, 1, 1)) == -18000
    assert tz.offset_for_date(datetime.datetime(2021, 6, 1)) == -14400


@pytest.mark.skipif(not is_macos, reason="macOS only")
def test_timezone_offset_str_for_date():
    """Test Timezone.offset_by_date method."""
    tz = Timezone("America/New_York")
    assert tz.offset_str_for_date(datetime.datetime(2021, 1, 1)) == "-05:00"
    assert tz.offset_str_for_date(datetime.datetime(2021, 6, 1)) == "-04:00"


def test_format_offset():
    """Test the formatting of time offset to string."""
    # Testing UTC -4 hours (in seconds: -4 * 3600 = -14400)
    assert format_offset_time(-14400) == "-04:00"
    # Testing UTC +5 hours (in seconds: 5 * 3600 = 18000)
    assert format_offset_time(18000) == "+05:00"


@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("GMT-0800", "Etc/GMT+8"),
        ("GMT+0200", "Etc/GMT-2"),
        ("GMT+0000", "Etc/GMT+0"),
        ("GMT-0000", "Etc/GMT+0"),
        ("utc-0300", "Etc/GMT+3"),
    ],
)
def test_convert_offset_timezone_to_etc_valid_etc_matches(input_str, expected):
    assert convert_offset_timezone_to_etc(input_str) == expected


@pytest.mark.parametrize(
    "bad_input",
    [
        "PST",
        "GMT+5",  # not HHMM
        "GMT++0800",  # invalid format
        "GMT-9999",  # invalid offset
        "GMT+0530"  # partial hour not handled
        "GMT-0530",  # partial hour not handled
    ],
)
def test_convert_offset_timezone_to_etc_invalid_format_raises_value_error(bad_input):
    with pytest.raises(ValueError):
        convert_offset_timezone_to_etc(bad_input)


@pytest.mark.parametrize(
    "out_of_bounds",
    [
        "GMT+1460",  # hours > 14
        "UTC+1275",  # minutes > 59
    ],
)
def test_convert_offset_timezone_to_etc_invalid_bounds_raises_value_error(
    out_of_bounds,
):
    with pytest.raises(ValueError):
        convert_offset_timezone_to_etc(out_of_bounds)


def test_convert_offset_timezone_to_etc_leading_trailing_whitespace_handled():
    assert convert_offset_timezone_to_etc("  GMT-0800 ") == "Etc/GMT+8"
