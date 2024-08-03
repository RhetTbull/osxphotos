"""Example function for use with `osxphotos timewarp --function`

Call this as: `osxphotos timewarp --function timewarp_function_creation_date.py::creation_date`
"""

import datetime
import os
from typing import Callable, Optional, Tuple

from photoscript import Photo


def creation_date(
    photo: Photo, path: Optional[str], tz_sec: int, tz_name: str, verbose: Callable
) -> Tuple[datetime.datetime, int]:
    """Example function for use with `osxphotos timewarp --function`

    Args:
        photo: Photo object
        path: path to photo, which may be None if photo is not on disk
        tz_sec: timezone offset from UTC in seconds
        tz_name: timezone name
        verbose: function to print verbose messages

    Returns:
        tuple of (file creation date/time as datetime.datetime, and new timezone offset from UTC in seconds as int)
    """

    # this example uses's the file's creation date/time; the timezone is not changed
    return get_file_creation_date(str(path)), tz_sec


def get_file_creation_date(file_path: str):
    """Get the creation date of a file"""
    stat = os.stat(file_path)

    # On macOS, st_birthtime is the creation time
    creation_time = stat.st_birthtime

    # Convert the timestamp to a datetime object
    creation_date = datetime.datetime.fromtimestamp(creation_time)

    return creation_date
