"""Example function for use with `osxphotos timewarp --function`

Call this as: `osxphotos timewarp --function timewarp_filename.py::parse_date_time_from_filename`
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from photoscript import Photo
from strpdatetime import strpdatetime


def parse_date_time_from_filename(
    photo: Photo, path: str | None, tz_sec: int, tz_name: str, verbose: Callable
) -> tuple[datetime, int]:
    """Function for use with `osxphotos timewarp --function` that parses date/time from filename in format "YYYY-MM-DD FILENAME.jpg"

    Args:
        photo: Photo object
        path: path to photo, which may be None if photo is not on disk
        tz_sec: timezone offset from UTC in seconds
        tz_name: timezone name
        verbose: function to print verbose messages

    Returns:
        tuple of (new date/time as datetime.datetime, and new timezone offset from UTC in seconds as int)
    """
    filename = photo.filename
    datetime = strpdatetime(filename, "^%Y-%m-%d")

    verbose(f"Updating {photo.filename} date/time: {datetime}")

    return datetime, tz_sec
