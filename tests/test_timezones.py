"""Test timezones.py """

import datetime
from zoneinfo import ZoneInfo

import pytest

from osxphotos.platform import is_macos
from osxphotos.timezones import format_offset_time

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
        Timezone(1.23)  # Invalid offset input


def test_format_offset():
    """Test the formatting of time offset to string."""
    # Testing UTC -4 hours (in seconds: -4 * 3600 = -14400)
    assert format_offset_time(-14400) == "-04:00"
    # Testing UTC +5 hours (in seconds: 5 * 3600 = 18000)
    assert format_offset_time(18000) == "+05:00"
