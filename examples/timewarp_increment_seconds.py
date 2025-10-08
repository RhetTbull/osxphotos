"""Example function for use with `osxphotos timewarp --function`

Call this as: `osxphotos timewarp --function timewarp_increment_seconds.py::increment_seconds`
"""

import re
from datetime import datetime, timedelta
from typing import Callable, Optional, Tuple

from photoscript import Photo


def increment_seconds(
    photo: Photo, path: Optional[str], tz_sec: int, tz_name: str, verbose: Callable
) -> Tuple[datetime, int]:
    """Example function for use with `osxphotos timewarp --function`; increments photo date/time by seconds based on number found in filename

    Args:
        photo: Photo object
        path: path to photo, which may be None if photo is not on disk
        tz_sec: timezone offset from UTC in seconds
        tz_name: timezone name
        verbose: function to print verbose messages

    Returns:
        tuple of (new date/time as datetime.datetime, and new timezone offset from UTC in seconds as int)
    """

    match = re.search(r"\d+(?=\D*$)", photo.filename)
    if match:
        seconds = int(match.group())
        date = photo.date + timedelta(seconds=seconds)
        verbose(f"Incrementing seconds for [filename]{photo.filename}[/] by [num]{seconds}[/] seconds")
        return date, tz_sec
    else:
        verbose(f"Could not find seconds in filename for [filename]{photo.filename}[/]")

    return photo.date, tz_sec
