"""Example function for use with `osxphotos timewarp --function`

Call this as: `osxphotos timewarp --function timewarp_parse_date.py::parse_date`
Or: `osxphotos timewarp --function https://raw.githubusercontent.com/RhetTbull/osxphotos/refs/heads/main/examples/timewarp_parse_date.py::parse_date`
"""

from datetime import datetime, timedelta
from typing import Callable, Optional, Tuple

from photoscript import Photo
from strpdatetime import strpdatetime


def parse_date(
    photo: Photo, path: Optional[str], tz_sec: int, tz_name: str, verbose: Callable
) -> Tuple[datetime, int]:
    """Custom function for use with `osxphotos timewarp --function`

    Args:
        photo: Photo object
        path: path to photo, which may be None if photo is not on disk
        tz_sec: timezone offset from UTC in seconds
        tz_name: timezone name
        verbose: function to print verbose messages

    Returns:
        tuple of (new date/time as datetime.datetime, and new timezone offset from UTC in seconds as int)
    """

    # See: https://forums.macrumors.com/threads/changing-photo-metadata-in-apple-photos-using-filename-data.2433396/?post=34006581#post-34006581
    # This example parses a filename in format '03 July 14-59-03 JACK_Starfish.jpg' where the year is 2025
    # Note: the timezone is not changed

    try:
        date = strpdatetime(photo.filename, "%d %B %H-%M-%S")
    except ValueError:
        verbose(f"Failed to parse date from filename: {photo.filename}")
        return photo.date, tz_sec

    date = date.replace(year=2025)
    verbose(f"Updating {photo.filename} date/time: {date}")

    return date, tz_sec
