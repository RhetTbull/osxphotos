""" Test custom click paramater types used by osxphotos CLI"""

import datetime

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
    UTCOffset,
)
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


def test_utcoffset():
    """Test UTCOffset"""
    utcoffset_data = {
        "+00:00": Timezone(0),
        "-00:00": Timezone(-0),
        "+01:00": Timezone(3600),
        "-01:00": Timezone(-3600),
        "+01:30": Timezone(5400),
        "-01:30": Timezone(-5400),
    }
    for utcoffset_str, utcoffset_int in utcoffset_data.items():
        assert UTCOffset().convert(utcoffset_str, None, None) == utcoffset_int


def test_utcoffset_invalid_format():
    """Test UTCOffset with invalid format"""
    utcoffset_data = [
        "20-01-01T00:00:00",
        "20-01-1",
    ]
    for utcoffset_str in utcoffset_data:
        with pytest.raises(BadParameter):
            UTCOffset().convert(utcoffset_str, None, None)
