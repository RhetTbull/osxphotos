""" test datetime_utils """
import pytest


def test_get_local_tz():
    """ test get_local_tz during time with no DST """
    import datetime
    import os
    import time

    from osxphotos.datetime_utils import get_local_tz

    os.environ["TZ"] = "US/Pacific"
    time.tzset()

    dt = datetime.datetime(2018, 12, 31, 0, 0, 0)
    local_tz = get_local_tz(dt)
    assert local_tz == datetime.timezone(
        datetime.timedelta(days=-1, seconds=57600), "PST"
    )


def test_get_local_tz_dst():
    """ test get_local_tz during time with DST """
    import datetime
    import os
    import time

    from osxphotos.datetime_utils import get_local_tz

    os.environ["TZ"] = "US/Pacific"
    time.tzset()

    dt = datetime.datetime(2018, 6, 30, 0, 0, 0)
    local_tz = get_local_tz(dt)
    assert local_tz == datetime.timezone(
        datetime.timedelta(days=-1, seconds=61200), "PDT"
    )


def test_datetime_remove_tz():
    """ test datetime_remove_tz """
    import datetime

    from osxphotos.datetime_utils import datetime_remove_tz

    dt = datetime.datetime(
        2018,
        12,
        31,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=57600), "PST"),
    )
    dt_no_tz = datetime_remove_tz(dt)
    assert dt_no_tz.tzinfo is None


def test_datetime_has_tz():
    """ test datetime_has_tz """
    import datetime

    from osxphotos.datetime_utils import datetime_has_tz

    dt = datetime.datetime(
        2018,
        12,
        31,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=57600), "PST"),
    )
    assert datetime_has_tz(dt)

    dt_notz = datetime.datetime(2018, 12, 31)
    assert not datetime_has_tz(dt_notz)


def test_datetime_naive_to_local():
    """ test datetime_naive_to_local """
    import datetime
    import os
    import time

    from osxphotos.datetime_utils import datetime_naive_to_local

    os.environ["TZ"] = "US/Pacific"
    time.tzset()

    dt = datetime.datetime(2018, 6, 30, 0, 0, 0)
    dt_local = datetime_naive_to_local(dt)
    assert dt_local.tzinfo == datetime.timezone(
        datetime.timedelta(days=-1, seconds=61200), "PDT"
    )
