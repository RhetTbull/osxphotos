""" test datetime_formatter.DateTimeFormatter """
import pytest

from .locale_util import setlocale


def test_datetime_formatter_1():
    """Test DateTimeFormatter"""
    import datetime
    import locale

    from osxphotos.datetime_formatter import DateTimeFormatter

    setlocale(locale.LC_ALL, "en_US")

    dt = datetime.datetime(2020, 5, 23, 12, 42, 33)
    dtf = DateTimeFormatter(dt)

    assert dtf.date == "2020-05-23"
    assert dtf.year == "2020"
    assert dtf.yy == "20"
    assert dtf.month == "May"
    assert dtf.mon == "May"
    assert dtf.mm == "05"
    assert dtf.dd == "23"
    assert dtf.doy == "144"
    assert dtf.hour == "12"
    assert dtf.min == "42"
    assert dtf.sec == "33"


def test_datetime_formatter_2():
    """Test DateTimeFormatter with hour > 12"""
    import datetime
    import locale

    from osxphotos.datetime_formatter import DateTimeFormatter

    setlocale(locale.LC_ALL, "en_US")

    dt = datetime.datetime(2020, 5, 23, 14, 42, 33)
    dtf = DateTimeFormatter(dt)

    assert dtf.date == "2020-05-23"
    assert dtf.year == "2020"
    assert dtf.yy == "20"
    assert dtf.month == "May"
    assert dtf.mon == "May"
    assert dtf.mm == "05"
    assert dtf.dd == "23"
    assert dtf.doy == "144"
    assert dtf.hour == "14"
    assert dtf.min == "42"
    assert dtf.sec == "33"


def test_datetime_formatter_3():
    """Test DateTimeFormatter zero-padding"""
    import datetime
    import locale

    from osxphotos.datetime_formatter import DateTimeFormatter

    setlocale(locale.LC_ALL, "en_US")

    dt = datetime.datetime(2020, 5, 2, 9, 3, 6)
    dtf = DateTimeFormatter(dt)

    assert dtf.date == "2020-05-02"
    assert dtf.year == "2020"
    assert dtf.yy == "20"
    assert dtf.month == "May"
    assert dtf.mon == "May"
    assert dtf.mm == "05"
    assert dtf.dd == "02"
    assert dtf.doy == "123"
    assert dtf.hour == "09"
    assert dtf.min == "03"
    assert dtf.sec == "06"
