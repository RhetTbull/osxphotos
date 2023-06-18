"""Utilities for working with datetimes"""

import datetime
import re
from typing import Optional


def utc_offset_string_to_seconds(utc_offset: str) -> int:
    """match a UTC offset in format ±[hh]:[mm], ±[h]:[mm], or ±[hh][mm] and return number of seconds offset"""
    patterns = [r"^([+-]?)(\d{1,2}):(\d{2})$", r"^([+-]?)(\d{2})(\d{2})$"]
    for pattern in patterns:
        match = re.match(pattern, utc_offset)
        if not match:
            continue
        sign = match[1]
        hours = int(match[2])
        minutes = int(match[3])
        if sign == "-":
            hours = -hours
            minutes = -minutes
        return (hours * 60 + minutes) * 60
    raise ValueError(f"Invalid UTC offset format: {utc_offset}.")


def update_datetime(
    dt: datetime.datetime,
    date: Optional[datetime.date] = None,
    time: Optional[datetime.time] = None,
    date_delta: Optional[datetime.timedelta] = None,
    time_delta: Optional[datetime.timedelta] = None,
) -> datetime.datetime:
    """
    Update the date and time of a datetime object.

    Args:
        dt: datetime object
        date: new date
        time: new time
        date_delta: a timedelta to apply
        time_delta: a timedelta to apply
    """
    if date is not None:
        dt = dt.replace(year=date.year, month=date.month, day=date.day)
    if time is not None:
        dt = dt.replace(
            hour=time.hour,
            minute=time.minute,
            second=time.second,
            microsecond=time.microsecond,
        )
    if date_delta is not None:
        dt = dt + date_delta
    if time_delta is not None:
        dt = dt + time_delta
    return dt


def time_string_to_datetime(time: str) -> datetime.time:
    """Convert time string to datetime.datetime"""

    """ valid time formats:
        - HH:MM:SS,
        - HH:MM:SS.fff,
        - HH:MM,

  """

    time_formats = [
        "%H:%M:%S",
        "%H:%M:%S.%f",
        "%H:%M",
    ]

    for dt_format in time_formats:
        try:
            parsed_dt = datetime.datetime.strptime(time, dt_format).time()
        except ValueError as e:
            pass
        else:
            return parsed_dt
    raise ValueError(
        f"Could not parse time format: {time} does not match {time_formats}"
    )
