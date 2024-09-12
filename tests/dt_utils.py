"""Utilities for working with datetime values in tests"""

import datetime

from osxphotos.datetime_utils import datetime_naive_to_local, datetime_remove_tz


def dt_to_local(dt: datetime.datetime) -> datetime.datetime:
    """Convert a datetime local timezone without changing the time"""
    dt = datetime_remove_tz(dt)
    dt = datetime_naive_to_local(dt)
    return dt
