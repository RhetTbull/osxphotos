import datetime
import os
from datetime import date, timezone
from zoneinfo import ZoneInfo

import pytest

from osxphotos.datetime_utils import *


@pytest.mark.usefixtures("set_tz_pacific")
def test_get_local_tz():
    dt = datetime.datetime(2020, 9, 1, 21, 10, 00)
    tz = get_local_tz(dt)
    assert tz == datetime.timezone(offset=datetime.timedelta(seconds=-25200))

    dt = datetime.datetime(2020, 12, 1, 21, 10, 00)
    tz = get_local_tz(dt)
    assert tz == datetime.timezone(offset=datetime.timedelta(seconds=-28800))


def test_datetime_has_tz():
    tz = datetime.timezone(offset=datetime.timedelta(seconds=-28800))
    dt = datetime.datetime(2020, 9, 1, 21, 10, 00, tzinfo=tz)
    assert datetime_has_tz(dt)

    dt = datetime.datetime(2020, 9, 1, 21, 10, 00)
    assert not datetime_has_tz(dt)


def test_datetime_tz_to_utc():
    tz = datetime.timezone(offset=datetime.timedelta(seconds=-25200))
    dt = datetime.datetime(2020, 9, 1, 22, 6, 0, tzinfo=tz)
    utc = datetime_tz_to_utc(dt)
    assert utc == datetime.datetime(2020, 9, 2, 5, 6, 0, tzinfo=datetime.timezone.utc)


@pytest.mark.usefixtures("set_tz_pacific")
def test_datetime_remove_tz():
    tz = datetime.timezone(offset=datetime.timedelta(seconds=-25200))
    dt = datetime.datetime(2020, 9, 1, 22, 6, 0, tzinfo=tz)
    dt = datetime_remove_tz(dt)
    assert dt == datetime.datetime(2020, 9, 1, 22, 6, 0)
    assert not datetime_has_tz(dt)


def test_datetime_naive_to_utc():
    dt = datetime.datetime(2020, 9, 1, 12, 0, 0)
    utc = datetime_naive_to_utc(dt)
    assert utc == datetime.datetime(2020, 9, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


@pytest.mark.usefixtures("set_tz_pacific")
def test_datetime_naive_to_local():
    tz = datetime.timezone(offset=datetime.timedelta(seconds=-25200))
    dt = datetime.datetime(2020, 9, 1, 12, 0, 0)
    utc = datetime_naive_to_local(dt)
    assert utc == datetime.datetime(2020, 9, 1, 12, 0, 0, tzinfo=tz)


@pytest.mark.usefixtures("set_tz_pacific")
def test_datetime_utc_to_local():
    tz = datetime.timezone(offset=datetime.timedelta(seconds=-25200))
    utc = datetime.datetime(2020, 9, 1, 19, 0, 0, tzinfo=datetime.timezone.utc)
    dt = datetime_utc_to_local(utc)
    assert dt == datetime.datetime(2020, 9, 1, 12, 0, 0, tzinfo=tz)


@pytest.mark.usefixtures("set_tz_cest")
def test_datetime_utc_to_local_2():
    tz = datetime.timezone(offset=datetime.timedelta(seconds=7200))
    utc = datetime.datetime(2020, 9, 1, 19, 0, 0, tzinfo=datetime.timezone.utc)
    dt = datetime_utc_to_local(utc)
    assert dt == datetime.datetime(2020, 9, 1, 21, 0, 0, tzinfo=tz)


def test_datetime_add_tz_with_tzname():
    dt = datetime.datetime(2024, 1, 1, 12, 0)
    tzname = "America/Los_Angeles"
    result = datetime_add_tz(dt, tzname=tzname)
    assert result.tzinfo == ZoneInfo(tzname)
    assert result.utcoffset() == datetime.timedelta(
        hours=-8
    )  # Adjust based on time of year


def test_datetime_add_tz_with_tzname_dst():
    dt = datetime.datetime(2024, 9, 1, 12, 0)
    tzname = "America/Los_Angeles"
    result = datetime_add_tz(dt, tzname=tzname)
    assert result.tzinfo == ZoneInfo(tzname)
    assert result.utcoffset() == datetime.timedelta(
        hours=-7
    )  # Adjust based on time of year


def test_datetime_add_tz_with_tzoffset():
    dt = datetime.datetime(2024, 1, 1, 12, 0)
    tzoffset = -28800  # Offset for UTC-8
    result = datetime_add_tz(dt, tzoffset=tzoffset)
    assert result.tzinfo.utcoffset(None) == datetime.timedelta(seconds=tzoffset)


def test_datetime_add_tz_with_both_tzname_and_tzoffset():
    dt = datetime.datetime(2024, 1, 1, 12, 0)
    tzname = "America/New_York"
    tzoffset = -18000  # Offset for UTC-5
    result = datetime_add_tz(dt, tzoffset=tzoffset, tzname=tzname)
    # Expecting tzname to take precedence
    assert result.tzinfo == ZoneInfo(tzname)


def test_datetime_add_tz_with_invalid_tzname_falls_back_to_tzoffset():
    dt = datetime.datetime(2024, 1, 1, 12, 0)
    tzname = "Invalid/Timezone"
    tzoffset = -3600  # Offset for UTC-1
    result = datetime_add_tz(dt, tzoffset=tzoffset, tzname=tzname)
    assert result.tzinfo.utcoffset(None) == datetime.timedelta(seconds=tzoffset)


def test_datetime_add_tz_raises_value_error_on_naive_datetime():
    dt = datetime.datetime(
        2024, 1, 1, 12, 0, tzinfo=datetime.timezone.utc
    )  # Already aware
    with pytest.raises(ValueError, match="dt must be naive datetime"):
        datetime_add_tz(dt, tzname="America/New_York")


def test_datetime_add_tz_raises_value_error_on_none_tzname_and_tzoffset():
    dt = datetime.datetime(2024, 1, 1, 12, 0)
    with pytest.raises(ValueError, match="Both tzoffset and tzname cannot be None"):
        datetime_add_tz(dt)
