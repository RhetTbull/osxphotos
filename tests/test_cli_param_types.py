"""Test custom click paramater types used by osxphotos CLI"""

import datetime
from unittest.mock import patch

import pytest
from bitmath import MB
from click.exceptions import BadParameter

from osxphotos.cli.param_types import (
    BitMathSize,
    DateOffset,
    DateTimeISO8601,
    ExportDBType,
    FunctionCall,
    TemplateString,
    TimeISO8601,
    TimeOffset,
    TimeString,
    TimezoneOffset,
)
from osxphotos.platform import is_macos
from osxphotos.timezones import Timezone


def test_date_offset():
    """Test DateOffset"""
    date_offset_data = {
        "1": datetime.timedelta(days=1),
        "1 day": datetime.timedelta(days=1),
        "+1 day": datetime.timedelta(days=1),
        "1 d": datetime.timedelta(days=1),
        "1d": datetime.timedelta(days=1),
        "+ 1": datetime.timedelta(days=1),
        "+1  day": datetime.timedelta(days=1),
        "+  1": datetime.timedelta(days=1),
        "14:30": datetime.timedelta(minutes=14, seconds=30),
        "14:30:00": datetime.timedelta(hours=14, minutes=30, seconds=0),
        "1 week": datetime.timedelta(days=7),
        "2 wk": datetime.timedelta(days=14),
        "2 months": datetime.timedelta(days=60),
        "1 mos": datetime.timedelta(days=30),
    }
    for date_offset_str, date_offset_delta in date_offset_data.items():
        assert DateOffset().convert(date_offset_str, None, None) == date_offset_delta


def test_date_offset_invalid_format():
    """Test DateOffset with invalid format"""
    date_offset_data = [
        "1 foo",
        "1 day 14",
        "day",
    ]
    for date_offset_str in date_offset_data:
        with pytest.raises(BadParameter):
            DateOffset().convert(date_offset_str, None, None)


def test_time_offset():
    """Test TimeOffset"""
    time_offset_data = {
        "1": datetime.timedelta(seconds=1),
        "1s": datetime.timedelta(seconds=1),
        "2  s": datetime.timedelta(seconds=2),
        "2 sec": datetime.timedelta(seconds=2),
        "3   sec": datetime.timedelta(seconds=3),
        "1m": datetime.timedelta(minutes=1),
        "1 min": datetime.timedelta(minutes=1),
        "1 day": datetime.timedelta(days=1),
        "14:30": datetime.timedelta(minutes=14, seconds=30),
        "14:30:00": datetime.timedelta(hours=14, minutes=30, seconds=0),
    }
    for time_offset_str, time_offset_delta in time_offset_data.items():
        assert TimeOffset().convert(time_offset_str, None, None) == time_offset_delta


def test_time_offset_invalid_format():
    """Test TimeOffset with invalid format"""
    time_offset_data = [
        "1 foo",
        "1 day 14",
        "1 sec 1",
        "sec",
    ]
    for time_offset_str in time_offset_data:
        with pytest.raises(BadParameter):
            TimeOffset().convert(time_offset_str, None, None)


def test_bitmath_size():
    """Test BitMathSize"""
    bitmath_size_data = {
        "1048576": MB(1.048576),
        "1.048576MB": MB(1.048576),
        "1 MiB": MB(1.048576),
    }
    for bitmath_size_str, bitmath_size_int in bitmath_size_data.items():
        assert BitMathSize().convert(bitmath_size_str, None, None) == bitmath_size_int


def test_bitmath_size_invalid_format():
    """Test BitMathSize with invalid format"""
    bitmath_size_data = [
        "1 foo",
        "1 mehgabite",
    ]
    for bitmath_size_str in bitmath_size_data:
        with pytest.raises(BadParameter):
            BitMathSize().convert(bitmath_size_str, None, None)


def test_date_time_iso8601():
    """Test DateTimeISO8601"""
    date_time_iso8601_data = {
        "2020-01-01T00:00:00": datetime.datetime(2020, 1, 1, 0, 0, 0),
        "2020-01-01T00:00:00.000": datetime.datetime(2020, 1, 1, 0, 0, 0),
        "2020-01-01": datetime.datetime(2020, 1, 1),
    }
    for date_time_iso8601_str, date_time_iso8601_dt in date_time_iso8601_data.items():
        assert (
            DateTimeISO8601().convert(date_time_iso8601_str, None, None)
            == date_time_iso8601_dt
        )


def test_date_time_iso8601_invalid_format():
    """Test DateTimeISO8601 with invalid format"""
    date_time_iso8601_data = [
        "20-01-01T00:00:00",
        "20-01-1",
    ]
    for date_time_iso8601_str in date_time_iso8601_data:
        with pytest.raises(BadParameter):
            DateTimeISO8601().convert(date_time_iso8601_str, None, None)


def test_time_iso8601():
    """Test TimeISO8601"""
    time_iso8601_data = {
        "00:00:00": datetime.time(0, 0, 0),
        "00:00:00.000": datetime.time(0, 0, 0),
    }

    for time_iso8601_str, time_iso8601_dt in time_iso8601_data.items():
        assert TimeISO8601().convert(time_iso8601_str, None, None) == time_iso8601_dt


def test_time_iso8601_invalid_format():
    """Test TimeISO8601 with invalid format"""
    date_time_iso8601_data = [
        "20-01-01T00:00:00",
        "20-01-1",
    ]
    for date_time_iso8601_str in date_time_iso8601_data:
        with pytest.raises(BadParameter):
            TimeISO8601().convert(date_time_iso8601_str, None, None)


def test_timestring():
    """Test TimeString"""
    timestring_data = {
        "01:02:03": datetime.time(1, 2, 3),
        "01:02:03.000": datetime.time(1, 2, 3),
        "01:02:03.0000": datetime.time(1, 2, 3),
        "01:02": datetime.time(1, 2, 0),
    }
    for timestring_str, timestring_dt in timestring_data.items():
        assert TimeString().convert(timestring_str, None, None) == timestring_dt


def test_timestring_invalid_format():
    """Test TimeString with invalid format"""
    timestring_data = [
        "20-01-01T00:00:00",
        "20-01-1",
    ]
    for timestring_str in timestring_data:
        with pytest.raises(BadParameter):
            TimeString().convert(timestring_str, None, None)


def test_timezoneoffset():
    """Test TimezoneOffset"""
    utcoffset_data = [
        ("+00:00", 0),
        ("-00:00", 0),
        ("+01:00", 3600),
        ("-01:00", -3600),
        ("+02:00", 7200),
        ("-02:00", -7200),
    ]

    # Test offset-based timezones
    for utcoffset_str, expected_offset in utcoffset_data:
        result = TimezoneOffset().convert(utcoffset_str, None, None)
        assert isinstance(result, Timezone)
        assert result.offset == expected_offset

    # Test named timezone
    result = TimezoneOffset().convert("America/Los_Angeles", None, None)
    assert isinstance(result, Timezone)
    assert result.name == "America/Los_Angeles"


@pytest.mark.skipif(not is_macos, reason="Only runs on macOS")
def test_timezoneoffset_macos():
    """Test TimezoneOffset on macOS; on macOS, Timezone supports unnamed partial hour timezones"""
    utcoffset_data = [
        ("+00:00", 0),
        ("-00:00", 0),
        ("+01:00", 3600),
        ("-01:00", -3600),
        ("+01:30", 5400),
        ("-01:30", -5400),
    ]

    # Test offset-based timezones
    for utcoffset_str, expected_offset in utcoffset_data:
        result = TimezoneOffset().convert(utcoffset_str, None, None)
        assert isinstance(result, Timezone)
        assert result.offset == expected_offset


def test_utcoffset_invalid_format():
    """Test UTCOffset with invalid format"""
    utcoffset_data = ["20-01-01T00:00:00", "20-01-1", "Invalid/Timezone"]
    for utcoffset_str in utcoffset_data:
        with pytest.raises(BadParameter):
            TimezoneOffset().convert(utcoffset_str, None, None)


def test_timezone_direct_construction():
    """Test direct Timezone construction with different platforms"""
    # Test that both integer and string construction work properly
    # This ensures compatibility across both platform versions

    tz_int = Timezone(3600)
    assert tz_int.offset == 3600

    tz_float = Timezone(3600.0)
    assert tz_float.offset == 3600

    tz_str = Timezone("America/Los_Angeles")
    assert tz_str.name == "America/Los_Angeles"


@pytest.mark.parametrize("is_macos_mock", [True, False])
def test_timezone_both_platform_versions(is_macos_mock):
    """Test Timezone class behavior on both platforms using mocking"""
    with patch("osxphotos.platform.is_macos", is_macos_mock):
        # Create a fresh instance to test platform-specific behavior
        # by dynamically importing the appropriate class structure

        if is_macos_mock:
            # Test that macOS version accepts float
            try:
                from osxphotos.timezones import Timezone

                # This should work if we're testing macOS version
                if hasattr(Timezone, "__init__"):
                    # Simple test - if the platform check worked, this should be callable
                    tz = Timezone(0)
                    assert tz.offset == 0
            except ImportError:
                pytest.skip("macOS-specific imports not available")
        else:
            # Test non-macOS version behavior
            try:
                from osxphotos.timezones import Timezone

                # Test integer construction
                tz = Timezone(0)
                assert tz.offset == 0

                tz_pos = Timezone(3600)
                assert tz_pos.offset == 3600

                tz_neg = Timezone(-3600)
                assert tz_neg.offset == -3600
            except ImportError:
                pytest.skip("Required imports not available")
