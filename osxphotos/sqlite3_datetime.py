"""Sqlite3 datetime adapters; import this module to register adapters for datetime objects;
these were built in before Python 3.12 but are deprecated in 3.12 """

import datetime
import sqlite3

# Reference: https://docs.python.org/3/library/sqlite3.html?highlight=sqlite3#sqlite3-adapter-converter-recipes


def adapt_date_iso(val):
    """Adapt datetime.date to ISO 8601 date."""
    return val.isoformat()


def adapt_datetime_iso(val):
    """Adapt datetime.datetime to timezone-naive ISO 8601 date."""
    return val.isoformat()


def adapt_datetime_epoch(val):
    """Adapt datetime.datetime to Unix timestamp."""
    return int(val.timestamp())


def convert_date(val):
    """Convert ISO 8601 date to datetime.date object."""
    return datetime.date.fromisoformat(val.decode())


def convert_datetime(val):
    """Convert ISO 8601 datetime to datetime.datetime object."""
    return datetime.datetime.fromisoformat(val.decode())


def convert_timestamp(val):
    """Convert Unix epoch timestamp to datetime.datetime object."""
    return datetime.datetime.fromtimestamp(int(val))


def register_adapters():
    """Register adapters for datetime objects."""
    sqlite3.register_adapter(datetime.date, adapt_date_iso)
    sqlite3.register_adapter(datetime.datetime, adapt_datetime_iso)
    sqlite3.register_adapter(datetime.datetime, adapt_datetime_epoch)


def register_converters():
    """Register converters for datetime objects."""
    sqlite3.register_converter("date", convert_date)
    sqlite3.register_converter("datetime", convert_datetime)
    sqlite3.register_converter("timestamp", convert_timestamp)


def register():
    """Register adapters and converters for datetime objects."""
    register_adapters()
    register_converters()
