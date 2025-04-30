"""Utilities for working with datetimes"""

import datetime
import re
import zoneinfo
from functools import cache
from typing import Optional
from zoneinfo import ZoneInfo

from osxphotos.datetime_utils import get_local_tz


def utc_offset_string_to_seconds(utc_offset: str) -> int:
    """Match a UTC offset in format ±[hh]:[mm], ±[h]:[mm], ±[hh][mm], GMT±[hh][mm], and return number of seconds offset"""
    patterns = [
        r"^([+-]?)(\d{1,2}):(\d{2})$",
        r"^([+-]?)(\d{2})(\d{2})$",
        r"^GMT([+-]?)(\d{2})(\d{2})$",
    ]
    utc_offset = utc_offset.upper()
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
    local_time_delta: Optional[datetime.timedelta] = None,
) -> datetime.datetime:
    """
    Update the date and time of a datetime object.

    Args:
        dt: datetime object
        date: new date
        time: new time
        date_delta: a timedelta to apply
        time_delta: a timedelta to apply
        local_time_delta: the difference between the local time and timezone that the datetime object is in

    Returns:
        datetime object with updated date and time

    Note:
        local_time_delta is only used when both time and local_time_delta are provided
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
    if time and local_time_delta is not None:
        dt = dt + local_time_delta
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


def get_local_utc_offset_str(dt: datetime.datetime | str) -> str:
    """Get the local timezone offset from UTC as a string in the format ±HHMM, for example +0500 or -0700.""" ""
    if isinstance(dt, str):
        dt = datetime.datetime.fromisoformat(dt)
    local_tz = get_local_tz(dt)

    offset = local_tz.utcoffset(dt)
    total_minutes = offset.total_seconds() / 60
    hours, minutes = divmod(abs(int(total_minutes)), 60)

    sign = "+" if total_minutes >= 0 else "-"
    offset_string = f"{sign}{hours:02d}{minutes:02d}"

    return offset_string


@cache
def available_timezones() -> list[str]:
    """Return sorted list of available timezones"""
    # zoneinfo.available_timezones() returns a set and the order is not deterministic
    return sorted(zoneinfo.available_timezones())


@cache
def available_timezones_lc() -> list[str]:
    """Return sorted list of available timezones in lower case"""
    return [tz.lower() for tz in available_timezones()]


def timedelta_from_gmt_str(offset: str) -> datetime.timedelta:
    """Return timedelta from UTC from a string in form 'GMT-0400'

    Args:
        offset: offset string in form 'GMT-0400', 'GMT+0100', etc

    Returns:
        offset from UTC as a timedelta

    Raises:
        ValueError if offset string cannot be parsed
    """
    seconds = utc_offset_string_to_seconds(offset)
    return datetime.timedelta(seconds=seconds)


def timezone_for_offset(offset: str, dt: datetime.datetime) -> str:
    """Given a offset from UTC in form 'GMT-0400', find the named timezone with the same UTC offset

    Args:
        offset: offset from UTC in form 'GMT-0400', 'GMT+0100', etc.
        dt: the datetime for which the offset applies

    Returns: name of first timezone found with the same offset

    Raises: ValueError if timezone cannot be found

    Note: offset may be in format ±[hh]:[mm], ±[h]:[mm], ±[hh][mm], or GMT±[hh][mm]
    """
    offset_delta = timedelta_from_gmt_str(offset)
    try:
        return timezone_for_timedelta(offset_delta, dt)
    except ValueError as e:
        raise ValueError("No matching named timezone found.") from e


def timezone_for_delta_seconds(delta: int, dt: datetime.datetime):
    """Given a offset delta from UTC in seconds find the named timezone with the same UTC offset

    Args:
        delta: offset from UTC seconds
        dt: the datetime for which the offset applies

    Returns: name of first timezone found with the same offset

    Raises: ValueError if timezone cannot be found
    """
    offset_delta = datetime.timedelta(seconds=delta)
    try:
        return timezone_for_timedelta(offset_delta, dt)
    except ValueError as e:
        raise ValueError("No matching named timezone found.") from e


def timezone_for_timedelta(
    offset_delta: datetime.timedelta, dt: datetime.datetime
) -> str:
    """Given a offset timedelta from UTC in seconds find the named timezone with the same UTC offset

    Args:
        offset_delta: timedelta from UTC
        dt: the datetime for which the offset applies

    Returns: name of first timezone found with the same offset

    Raises: ValueError if timezone cannot be found
    """
    for tz_name in sorted(available_timezones()):
        tz = ZoneInfo(tz_name)
        if dt.astimezone(tz).utcoffset() == offset_delta:
            return tz_name
    raise ValueError("No matching named timezone found.")


def get_valid_timezone(tz_name: str, dt: datetime.datetime) -> str:
    """Return a valid timezone name or raise a ValueError

    Args:
        tz_name: timezone name
        dt: datetime object to use for validation

    Returns: valid timezone name

    Raises: ValueError if timezone is not valid
    """
    if tz_name.lower() in available_timezones_lc():
        return tz_name

    try:
        return timezone_for_offset(tz_name, dt)
    except ValueError as e:
        raise ValueError(f"{tz_name} does not appear to be a valid timezone.") from e
