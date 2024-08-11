""" Utilities for working with date/time values in the Photos library """

from __future__ import annotations

import datetime

from .datetime_utils import get_local_tz

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


__all__ = ["photos_datetime"]


def photos_datetime(
    timestamp: float | None, tzoffset: int, default: bool = False
) -> datetime.datetime | None:
    """Convert a timestamp from the Photos database to a timezone aware datetime"""
    if timestamp is None:
        return DEFAULT_DATETIME if default else None

    try:
        dt = datetime.datetime.fromtimestamp(
            timestamp + TIME_DELTA, datetime.timezone.utc
        )
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
        # Convert the timestamp to a UTC datetime
        dt_utc = datetime.datetime.fromtimestamp(
            timestamp + TIME_DELTA, datetime.timezone.utc
        )

        # Get the local timezone
        local_tz = get_local_tz(dt_utc.replace(tzinfo=None))

        # Convert UTC datetime to local timezone
        dt_local = dt_utc.astimezone(local_tz)

        return dt_local
    except (ValueError, TypeError):
        return DEFAULT_DATETIME_LOCAL if default else None
