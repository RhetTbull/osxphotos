"""Utilities for working with datetimes"""

import datetime
import re
import zoneinfo
from functools import cache
from typing import Optional
from zoneinfo import ZoneInfo

from whenever import Date, Time, ZonedDateTime

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
    tzinfo: Optional[ZoneInfo] = None,
    date: Optional[datetime.date] = None,
    time: Optional[datetime.time] = None,
    date_delta: Optional[datetime.timedelta] = None,
    time_delta: Optional[datetime.timedelta] = None,
    local_time_delta: Optional[datetime.timedelta] = None,
) -> datetime.datetime:
    """
    Update the date and time of a datetime object using DST-aware operations.

    Args:
        dt: datetime object
        tzinfo: ZoneInfo for the datetime object or None
        date: new date
        time: new time
        date_delta: a timedelta to apply
        time_delta: a timedelta to apply
        local_time_delta: the difference between the local time and timezone that the datetime object is in

    Returns:
        datetime object with updated date and time

    Note:
        local_time_delta is only used when both time and local_time_delta are provided
        Uses whenever package internally for DST-aware calculations
    """
    if dt.tzinfo is None:
        dt_with_tz = dt.astimezone(tzinfo) if tzinfo else dt.astimezone(ZoneInfo("UTC"))
    else:
        dt_with_tz = dt

    zoned_dt = ZonedDateTime.from_py_datetime(dt_with_tz)

    if date is not None:
        whenever_date = Date(year=date.year, month=date.month, day=date.day)
        zoned_dt = zoned_dt.replace_date(whenever_date)

    if time is not None:
        whenever_time = Time(
            hour=time.hour,
            minute=time.minute,
            second=time.second,
            nanosecond=time.microsecond * 1000,
        )
        zoned_dt = zoned_dt.replace_time(whenever_time)

    if date_delta is not None:
        zoned_dt = zoned_dt.add(seconds=date_delta.total_seconds())

    if time_delta is not None:
        zoned_dt = zoned_dt.add(seconds=time_delta.total_seconds())

    if time is not None and local_time_delta is not None:
        zoned_dt = zoned_dt.add(seconds=local_time_delta.total_seconds())

    result_dt = zoned_dt.py_datetime()

    if dt.tzinfo is None:
        local_tz = get_local_tz(dt)
        result_local = result_dt.astimezone(local_tz)
        return result_local.replace(tzinfo=None)
    else:
        return result_dt.astimezone(dt.tzinfo)


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


def etc_to_gmt_offset(etc_tz: str) -> str:
    """
    Convert an 'Etc/GMT±H' style timezone to 'GMT±HHMM' format.

    Args:
        etc_tz: the timezone str

    Returns: converted timezone str

    Raises:
        ValueError if invalid format or offset

    Note:
      - 'Etc/GMT+5'  -> 'GMT-0500'  (POSIX sign inversion)
      - 'Etc/GMT-3'  -> 'GMT+0300'
      - Leading zeros for NON-ZERO hours are invalid (e.g., 'Etc/GMT+05' -> ValueError)
      - Zero is allowed with or without a sign (e.g., 'Etc/GMT+0', 'Etc/GMT-0', 'Etc/GMT+00')

    Example:
        Etc/GMT+5  -> GMT-0500
        Etc/GMT-3  -> GMT+0300
        Etc/GMT+0  -> GMT+0000
    """
    prefix = "Etc/GMT"
    if not isinstance(etc_tz, str) or not etc_tz.startswith(prefix):
        raise ValueError(f"Invalid Etc/GMT format: {etc_tz!r}")

    offset_part = etc_tz[len(prefix) :]
    if not offset_part:
        raise ValueError(f"Invalid offset in timezone: {etc_tz!r}")

    # Optional sign, then digits only
    sign_char = ""
    digits = offset_part
    if digits[0] in "+-":
        sign_char = digits[0]
        digits = digits[1:]

    if not digits or not digits.isdigit():
        raise ValueError(f"Invalid offset in timezone: {etc_tz!r}")

    # Reject leading zeros on non-zero values (e.g., '05', '007', etc.)
    if len(digits) > 1 and digits[0] == "0":
        raise ValueError(f"Leading zeros not allowed: {etc_tz}")

    offset_hours = int((sign_char or "+") + digits)

    # Invert the sign because Etc/GMT+5 means GMT-5
    sign = "-" if offset_hours > 0 else "+"
    abs_hours = abs(offset_hours)

    return f"GMT{sign}{abs_hours:02d}00"
