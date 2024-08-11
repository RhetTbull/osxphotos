"""Test photos_datetime.py utilities"""

from __future__ import annotations

import datetime

import pytest

from osxphotos.photos_datetime import photos_datetime

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


@pytest.mark.parametrize("timestamp, tzoffset, default, expected", TEST_DATA)
def test_photos_datetime(
    timestamp: float, tzoffset: int, default: bool, expected: str | None
):
    """Test photos_datetime"""
    dt = photos_datetime(timestamp, tzoffset, default)
    dt_expected = datetime.datetime.fromisoformat(expected) if expected else None
    assert dt == dt_expected
