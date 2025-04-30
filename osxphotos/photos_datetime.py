""" Utilities for working with date/time values in the Photos library """

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from .datetime_utils import datetime_naive_to_local, get_local_tz

# Time delta: add this to Photos times to get unix time
# Apple Epoch is Jan 1, 2001
TIME_DELTA = (
    datetime.datetime(2001, 1, 1, 0, 0) - datetime.datetime(1970, 1, 1, 0, 0)
).total_seconds()

# Default datetime for when we can't determine the date
DEFAULT_DATETIME = datetime.datetime(1970, 1, 1, 0, tzinfo=datetime.timezone.utc)
DEFAULT_DATETIME_LOCAL = datetime.datetime(
    1970, 1, 1, 0, tzinfo=get_local_tz(datetime.datetime(1970, 1, 1, 0))
)


__all__ = ["photos_datetime", "photos_datetime_local"]


def photos_datetime(
    timestamp: float | None,
    tzoffset: int | None = None,
    tzname: str | None = None,
    default: bool = False,
) -> datetime.datetime | None:
    """Convert a timestamp from the Photos database to a timezone aware datetime"""
    if timestamp is None:
        return DEFAULT_DATETIME if default else None

    tzoffset = tzoffset or 0
    try:
        dt = datetime.datetime.fromtimestamp(timestamp + TIME_DELTA)
        # Try to use tzname if provided
        if tzname:
            try:
                tz = ZoneInfo(tzname)
                return dt.astimezone(tz)
            except Exception:
                # If tzname fails, fall back to tzoffset
                pass

        # Use tzoffset if tzname wasn't provided or failed
        tz = datetime.timezone(datetime.timedelta(seconds=tzoffset))
        return dt.astimezone(tz)
    except (ValueError, TypeError):
        return DEFAULT_DATETIME if default else None


def photos_datetime_local(
    timestamp: float | None, default: bool = False
) -> datetime.datetime | None:
    """
    Convert a timestamp from the Photos database to a timezone aware datetime
    in the local timezone.
    """
    if timestamp is None:
        return DEFAULT_DATETIME_LOCAL if default else None

    try:
        # Convert the timestamp to a datetime
        dt_naive = datetime.datetime.fromtimestamp(timestamp + TIME_DELTA)
        # Get the local timezone
        local_tz = get_local_tz(dt_naive.replace(tzinfo=None))
        # Convert naive datetime to local timezone
        dt_local = dt_naive.astimezone(local_tz)
        return dt_local
    except (ValueError, TypeError):
        return DEFAULT_DATETIME_LOCAL if default else None


def iphoto_date_to_datetime(
    date: int | None, tz: str | None = None
) -> datetime.datetime:
    """ "Convert iPhoto date to datetime; if tz provided, will be timezone aware

    Args:
        date: iPhoto date
        tz: timezone name

    Returns:
        datetime.datetime

    Note:
        If date is None or invalid, will return 1970-01-01 00:00:00
    """
    try:
        dt = datetime.datetime.fromtimestamp(date + TIME_DELTA)
    except (ValueError, TypeError):
        dt = datetime.datetime(1970, 1, 1)
    if tz:
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    return dt


def naive_iphoto_date_to_datetime(date: int) -> datetime.datetime:
    """ "Convert iPhoto date to datetime with local timezone

    Args:
        date: iPhoto date

    Returns:
        timezone aware datetime.datetime in local timezone

    Note:
        If date is invalid, will return 1970-01-01 00:00:00
    """
    try:
        dt = datetime.datetime.fromtimestamp(date + TIME_DELTA)
    except ValueError:
        dt = datetime.datetime(1970, 1, 1)
    return datetime_naive_to_local(dt)
