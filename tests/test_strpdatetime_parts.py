"""Test strpdatetime_parts """

import pytest

from osxphotos.strpdatetime_parts import (
    date_str_matches_date_time_codes,
    fmt_has_date_time_codes,
)

FMT_TEST_DATA = {
    "%Y": (True, False),
    "%-Y": (True, False),
    "%d": (True, False),
    "%%Y%%m%%d": (False, False),
    "%Y-%m-%d %H:%M:%S": (True, True),
    "%Y-%m-%d %I:%M:%S": (True, True),
    "FOO": (False, False),
    "%%Y%-H": (False, True),
}

DATE_STR_TEST_DATA = [
    ["2020-01-01", "%Y-%m-%d", (True, False)],
    ["2020-01-01 10:00:00", "%Y-%m-%d %H:%M:%S", (True, True)],
    ["12:34:56", "%Y%m%d|%H:%M:%S", (False, True)],
    ["Foo", "%Y%m%d|%H:%M:%S", (False, False)],
]


@pytest.mark.parametrize("fmt,expected", FMT_TEST_DATA.items())
def test_has_date_time_codes(fmt, expected):
    assert fmt_has_date_time_codes(fmt) == expected


@pytest.mark.parametrize("data", DATE_STR_TEST_DATA)
def test_date_str_matches_date_time_codes(data):
    date_str, fmt, expected = data
    assert date_str_matches_date_time_codes(date_str, fmt) == expected
