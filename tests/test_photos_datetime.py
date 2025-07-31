"""Test photos_datetime.py utilities"""

from __future__ import annotations

import datetime

import pytest

from osxphotos.photos_datetime import photos_datetime, photos_datetime_local

# data is timestamp, tzoffset, expected datetime
TEST_DATA = [
    (608405423, -25200, False, "2020-04-12 10:30:23-07:00"),
    (123456789012345, -25200, False, None),
    (123456789012345, -25200, True, "1970-01-01 00:00:00+00:00"),
    (714316684, 34200, False, "2023-08-21 22:48:04+09:30"),
    (583964641, -14400, False, "2019-07-04 16:24:01-04:00"),
    (561129492.501, -14400, False, "2018-10-13 09:18:12.501000-04:00"),
    (715411622, -14400, False, "2023-09-03 01:27:02-04:00"),
    (622244186.719, -25200, False, "2020-09-19 14:36:26.719000-07:00"),
    (608664351, -25200, False, "2020-04-15 10:25:51-07:00"),
    (714316684, -14400, False, "2023-08-21 09:18:04-04:00"),
    (608758101, -25200, False, "2020-04-16 12:28:21-07:00"),
    (714316684, -14400, False, "2023-08-21 09:18:04-04:00"),
    (608751778, -25200, False, "2020-04-16 10:42:58-07:00"),
    (559856149.063, -14400, False, "2018-09-28 15:35:49.063000-04:00"),
    (559856399.008, -14400, False, "2018-09-28 15:39:59.008000-04:00"),
    (744897809.3687729, -18000, False, "2024-08-09 07:03:29.368773-05:00"),
]

TEST_DATA_LOCAL = [
    (
        585926353.706262,
        datetime.datetime(
            2019,
            7,
            27,
            8,
            19,
            13,
            706262,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        597444332.900475,
        datetime.datetime(
            2019,
            12,
            7,
            14,
            45,
            32,
            900475,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=64800), "CST"),
        ),
    ),
    (
        597444345.353661,
        datetime.datetime(
            2019,
            12,
            7,
            14,
            45,
            45,
            353661,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=64800), "CST"),
        ),
    ),
    (
        608321109.224879,
        datetime.datetime(
            2020,
            4,
            11,
            13,
            5,
            9,
            224879,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        610122315.01428,
        datetime.datetime(
            2020,
            5,
            2,
            9,
            25,
            15,
            14280,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        613234428.439275,
        datetime.datetime(
            2020,
            6,
            7,
            9,
            53,
            48,
            439275,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        613234481.584484,
        datetime.datetime(
            2020,
            6,
            7,
            9,
            54,
            41,
            584484,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        620539511.367272,
        datetime.datetime(
            2020,
            8,
            30,
            23,
            5,
            11,
            367272,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        621736496.804132,
        datetime.datetime(
            2020,
            9,
            13,
            19,
            34,
            56,
            804132,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
    (
        745072616.284746,
        datetime.datetime(
            2024,
            8,
            11,
            7,
            36,
            56,
            284746,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400), "CDT"),
        ),
    ),
]


@pytest.mark.parametrize("timestamp, tzoffset, default, expected", TEST_DATA)
def test_photos_datetime(
    timestamp: float, tzoffset: int, default: bool, expected: str | None
):
    """Test photos_datetime"""
    dt = photos_datetime(timestamp, tzoffset, default=default)
    dt_expected = datetime.datetime.fromisoformat(expected) if expected else None
    assert dt == dt_expected


@pytest.mark.parametrize("timestamp, expected", TEST_DATA_LOCAL)
def test_photos_datetime_local(timestamp: float, expected: datetime.datetime):
    """Test photos_datetime_local"""
    dt = photos_datetime_local(timestamp)
    assert dt == expected
