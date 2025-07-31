"""Example function for use with `osxphotos timewarp --function`

Call this as: `osxphotos timewarp --function timewarp_function_example.py::get_date_time_timezone`
"""

from datetime import datetime, timedelta
from typing import Callable, Optional, Tuple

from photoscript import Photo


def get_date_time_timezone(
    photo: Photo, path: Optional[str], tz_sec: int, tz_name: str, verbose: Callable
) -> Tuple[datetime, int]:
    """Example function for use with `osxphotos timewarp --function`

    Args:
        photo: Photo object
        path: path to photo, which may be None if photo is not on disk
        tz_sec: timezone offset from UTC in seconds
        tz_name: timezone name
        verbose: function to print verbose messages

    Returns:
        tuple of (new date/time as datetime.datetime, and new timezone offset from UTC in seconds as int)
    """

    # this example adds 3 hours to the date/time and subtracts 1 hour from the timezone

    # the photo's date/time can be accessed as photo.date
    # photo.date is a datetime.datetime object
    # the date/time is naive (timezone unaware) and will be in local timezone
    date = photo.date

    # add 3 hours
    date = date + timedelta(hours=3)

    # subtract 1 hour from timezone
    timezone = tz_sec - 3600

    # verbose(msg) prints a message to the console if user used --verbose option
    # otherwise it does nothing
    # photo's filename can be access as photo.filename
    verbose(f"Updating {photo.filename} date/time: {date} and timezone: {timezone}")

    return date, timezone
