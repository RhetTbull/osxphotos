""" Utilities for working with date/time values in the Photos library """

from __future__ import annotations

import datetime

# Time delta: add this to Photos times to get unix time
# Apple Epoch is Jan 1, 2001
TIME_DELTA = (datetime.datetime(2001, 1, 1, 0, 0) - datetime.datetime(1970, 1, 1, 0, 0)).total_seconds()

# Default datetime for when we can't determine the date
DEFAULT_DATETIME = datetime.datetime(1970, 1, 1).astimezone(tz=datetime.timezone.utc)

__all__ = ["photos_datetime"]


def photos_datetime(
    timestamp: float | None, tzoffset: int, default: bool = False
) -> datetime.datetime | None:
    """Convert a timestamp from the Photos database to a timezone aware datetime"""
    dt: datetime.datetime | None = None

    if timestamp is None:
        if default:
            return DEFAULT_DATETIME
        else:
            return None

    try:
        dt = datetime.datetime.fromtimestamp(timestamp + TIME_DELTA)
    except (ValueError, TypeError):
        dt = None

    if dt is None:
        if default:
            return DEFAULT_DATETIME
        else:
            return None

    delta = datetime.timedelta(seconds=tzoffset)
    tz = datetime.timezone(delta)
    return dt.astimezone(tz=tz)
