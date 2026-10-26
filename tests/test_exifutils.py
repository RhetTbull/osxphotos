"""Tests for osxphotos.exifutils.get_exif_date_time_offset"""

import datetime
import logging

import pytest

from osxphotos.exifutils import get_exif_date_time_offset


def tz(hours: int, minutes: int = 0) -> datetime.timezone:
    return datetime.timezone(datetime.timedelta(hours=hours, minutes=minutes))


def test_standard_date_with_offset():
    exif = {
        "EXIF:DateTimeOriginal": "2020:06:01 12:34:56",
        "EXIF:OffsetTimeOriginal": "-04:00",
    }
    result = get_exif_date_time_offset(exif)
    assert result.datetime == datetime.datetime(2020, 6, 1, 12, 34, 56, tzinfo=tz(-4))
    assert result.offset_seconds == -4 * 3600
    assert result.offset_str == "-0400"
    assert not result.default_time
    assert not result.used_file_modify_date


def test_standard_date_without_time():
    result = get_exif_date_time_offset({"EXIF:DateTimeOriginal": "2020:06:01"})
    assert result.datetime == datetime.datetime(2020, 6, 1)
    assert result.default_time


def test_iptc_date_and_time_combined():
    exif = {"IPTC:DateCreated": "2020:06:01", "IPTC:TimeCreated": "08:09:10+02:00"}
    result = get_exif_date_time_offset(exif)
    assert result.datetime == datetime.datetime(2020, 6, 1, 8, 9, 10, tzinfo=tz(2))
    assert not result.default_time


def test_unparseable_field_falls_through_to_next_standard_field():
    """A bad value in a higher-priority field must not hide a valid one (#2274)"""
    exif = {
        "EXIF:DateTimeOriginal": "0000:00:00 00:00:00",
        "EXIF:CreateDate": "2019:03:04 05:06:07",
    }
    result = get_exif_date_time_offset(exif)
    assert result.datetime == datetime.datetime(2019, 3, 4, 5, 6, 7)


def test_non_standard_dotted_date_day_first():
    """The case reported in #2274"""
    exif = {
        "EXIF:DateTimeOriginal": "04.07.2009 17:19",
        "EXIF:CreateDate": "04.07.2009 17:19",
    }
    result = get_exif_date_time_offset(exif)
    assert result.datetime == datetime.datetime(2009, 7, 4, 17, 19)
    assert not result.default_time
    assert not result.used_file_modify_date


def test_non_standard_dotted_date_month_first_when_day_first_invalid():
    result = get_exif_date_time_offset({"EXIF:DateTimeOriginal": "12.25.2009 17:19:20"})
    assert result.datetime == datetime.datetime(2009, 12, 25, 17, 19, 20)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2009-07-04 17:19:20", datetime.datetime(2009, 7, 4, 17, 19, 20)),
        ("2009/07/04 17:19", datetime.datetime(2009, 7, 4, 17, 19)),
        ("2009-07-04T17:19:20", datetime.datetime(2009, 7, 4, 17, 19, 20)),
        (
            "2009-07-04T17:19:20+05:30",
            datetime.datetime(2009, 7, 4, 17, 19, 20, tzinfo=tz(5, 30)),
        ),
        (
            "2009-07-04 17:19:20Z",
            datetime.datetime(2009, 7, 4, 17, 19, 20, tzinfo=tz(0)),
        ),
    ],
)
def test_non_standard_ymd_dates(value, expected):
    result = get_exif_date_time_offset({"EXIF:DateTimeOriginal": value})
    assert result.datetime == expected


def test_non_standard_date_date_only_sets_default_time():
    result = get_exif_date_time_offset({"EXIF:DateTimeOriginal": "04.07.2009"})
    assert result.datetime == datetime.datetime(2009, 7, 4)
    assert result.default_time


def test_non_standard_date_uses_offset_time_original():
    exif = {
        "EXIF:DateTimeOriginal": "04.07.2009 17:19",
        "EXIF:OffsetTimeOriginal": "+02:00",
    }
    result = get_exif_date_time_offset(exif)
    assert result.datetime == datetime.datetime(2009, 7, 4, 17, 19, tzinfo=tz(2))
    assert result.offset_seconds == 7200
    assert result.offset_str == "+0200"


def test_standard_field_preferred_over_non_standard_higher_priority_field():
    """A well-formed date in a lower-priority field beats a guessed non-standard one"""
    exif = {
        "EXIF:DateTimeOriginal": "04.07.2009 17:19",
        "XMP:DateCreated": "2009:04:07 17:19:00",
    }
    result = get_exif_date_time_offset(exif)
    assert result.datetime == datetime.datetime(2009, 4, 7, 17, 19)


def test_file_modify_date_is_last_resort():
    exif = {
        "EXIF:DateTimeOriginal": "04.07.2009 17:19",
        "File:FileModifyDate": "2024:01:02 03:04:05+00:00",
    }
    result = get_exif_date_time_offset(exif, use_file_modify_date=True)
    assert result.datetime == datetime.datetime(2009, 7, 4, 17, 19)
    assert not result.used_file_modify_date

    exif["EXIF:DateTimeOriginal"] = "garbage"
    result = get_exif_date_time_offset(exif, use_file_modify_date=True)
    assert result.datetime == datetime.datetime(2024, 1, 2, 3, 4, 5, tzinfo=tz(0))
    assert result.used_file_modify_date


def test_unparseable_date_is_logged(caplog):
    with caplog.at_level(logging.WARNING, logger="osxphotos"):
        result = get_exif_date_time_offset({"EXIF:DateTimeOriginal": "sometime"})
    assert result.datetime is None
    assert "EXIF:DateTimeOriginal" in caplog.text
    assert "sometime" in caplog.text


def test_no_date():
    result = get_exif_date_time_offset({"EXIF:OffsetTimeOriginal": "+01:00"})
    assert result.datetime is None
    assert result.offset_seconds == 3600
    assert not result.default_time
    assert not result.used_file_modify_date


def test_integer_year_value():
    result = get_exif_date_time_offset(
        {"QuickTime:ContentCreateDate": 2014, "EXIF:CreateDate": "2014:05:06 07:08:09"}
    )
    assert result.datetime == datetime.datetime(2014, 5, 6, 7, 8, 9)
