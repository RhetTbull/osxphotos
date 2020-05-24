""" test datetime_formatter.DateTimeFormatter """
import pytest

def test_datetime_formatter():
    import datetime
    import locale
    from osxphotos.datetime_formatter import DateTimeFormatter
    
    locale.setlocale(locale.LC_ALL, "en_US")

    dt = datetime.datetime(2020,5,23)
    dtf = DateTimeFormatter(dt)

    assert dtf.date == "2020-05-23"
    assert dtf.year == "2020"
    assert dtf.yy == "20"
    assert dtf.month == "May"
    assert dtf.mon == "May"
    assert dtf.mm == "05"
    assert dtf.dd == "23"
    assert dtf.doy == "144"
