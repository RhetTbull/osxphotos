from datetime import date, timezone

import pytest

from osxphotos.datetime_utils import *


def test_get_local_tz():
    import datetime
    import os

    os.environ["TZ"] = "US/Pacific"

    dt = datetime.datetime(2020, 9, 1, 21, 10, 00)
    tz = get_local_tz(dt)
    assert tz == datetime.timezone(offset=datetime.timedelta(seconds=-25200))

    dt = datetime.datetime(2020, 12, 1, 21, 10, 00)
    tz = get_local_tz(dt)
    assert tz == datetime.timezone(offset=datetime.timedelta(seconds=-28800))


def test_datetime_has_tz():
    import datetime

    tz = datetime.timezone(offset=datetime.timedelta(seconds=-28800))
    dt = datetime.datetime(2020, 9, 1, 21, 10, 00, tzinfo=tz)
    assert datetime_has_tz(dt)

    dt = datetime.datetime(2020, 9, 1, 21, 10, 00)
    assert not datetime_has_tz(dt)


def test_datetime_tz_to_utc():
    import datetime

    tz = datetime.timezone(offset=datetime.timedelta(seconds=-25200))
    dt = datetime.datetime(2020, 9, 1, 22, 6, 0, tzinfo=tz)
    utc = datetime_tz_to_utc(dt)
    assert utc == datetime.datetime(2020, 9, 2, 5, 6, 0, tzinfo=datetime.timezone.utc)


def test_datetime_remove_tz():
    import datetime
    import os

    os.environ["TZ"] = "US/Pacific"

    tz = datetime.timezone(offset=datetime.timedelta(seconds=-25200))
    dt = datetime.datetime(2020, 9, 1, 22, 6, 0, tzinfo=tz)
    dt = datetime_remove_tz(dt)
    assert dt == datetime.datetime(2020, 9, 1, 22, 6, 0)
    assert not datetime_has_tz(dt)


def test_datetime_naive_to_utc():
    import datetime

    dt = datetime.datetime(2020, 9, 1, 12, 0, 0)
    utc = datetime_naive_to_utc(dt)
    assert utc == datetime.datetime(2020, 9, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def test_datetime_naive_to_local():
    import datetime
    import os

    os.environ["TZ"] = "US/Pacific"

    tz = datetime.timezone(offset=datetime.timedelta(seconds=-25200))
    dt = datetime.datetime(2020, 9, 1, 12, 0, 0)
    utc = datetime_naive_to_local(dt)
    assert utc == datetime.datetime(2020, 9, 1, 12, 0, 0, tzinfo=tz)


def test_datetime_utc_to_local():
    import datetime
    import os

    os.environ["TZ"] = "US/Pacific"

    tz = datetime.timezone(offset=datetime.timedelta(seconds=-25200))
    utc = datetime.datetime(2020, 9, 1, 19, 0, 0, tzinfo=datetime.timezone.utc)
    dt = datetime_utc_to_local(utc)
    assert dt == datetime.datetime(2020, 9, 1, 12, 0, 0, tzinfo=tz)


def test_datetime_utc_to_local_2():
    import datetime
    import os

    os.environ["TZ"] = "CEST"

    tz = datetime.timezone(offset=datetime.timedelta(seconds=7200))
    utc = datetime.datetime(2020, 9, 1, 19, 0, 0, tzinfo=datetime.timezone.utc)
    dt = datetime_utc_to_local(utc)
    assert dt == datetime.datetime(2020, 9, 1, 21, 0, 0, tzinfo=tz)
