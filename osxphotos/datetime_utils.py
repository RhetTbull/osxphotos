""" datetime.datetime helper functions for converting to/from UTC and other datetime manipulations"""

# source: https://github.com/RhetTbull/datetime-utils

__version__ = "2022.04.30"

import datetime

# TODO: probably shouldn't use replace here, see this:
# https://stackoverflow.com/questions/13994594/how-to-add-timezone-into-a-naive-datetime-instance-in-python/13994611#13994611

__all__ = [
    "datetime_has_tz",
    "datetime_naive_to_local",
    "datetime_naive_to_utc",
    "datetime_remove_tz",
    "datetime_to_new_tz",
    "datetime_tz_to_utc",
    "datetime_utc_to_local",
    "get_local_tz",
    "utc_offset_seconds",
]


# TODO: look at https://github.com/regebro/tzlocal for more robust implementation
def get_local_tz(dt: datetime.datetime) -> datetime.tzinfo:
    """Return local timezone as datetime.timezone tzinfo for dt

    Args:
        dt: datetime.datetime

    Returns:
        local timezone for dt as datetime.timezone

    Raises:
        ValueError if dt is not timezone naive
    """
    if not datetime_has_tz(dt):
        return dt.astimezone().tzinfo
    else:
        raise ValueError("dt must be naive datetime.datetime object")


def datetime_has_tz(dt: datetime.datetime) -> bool:
    """Return True if datetime dt has tzinfo else False

    Args:
        dt: datetime.datetime

    Returns:
        True if dt is timezone aware, else False

    Raises:
        TypeError if dt is not a datetime.datetime object
    """

    if type(dt) != datetime.datetime:
        raise TypeError(f"dt must be type datetime.datetime, not {type(dt)}")

    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def datetime_tz_to_utc(dt: datetime.datetime) -> datetime.datetime:
    """Convert datetime.datetime object with timezone to UTC timezone

    Args:
        dt: datetime.datetime object

    Returns:
        datetime.datetime in UTC timezone

    Raises:
        TypeError if dt is not datetime.datetime object
        ValueError if dt does not have timeone information
    """

    if type(dt) != datetime.datetime:
        raise TypeError(f"dt must be type datetime.datetime, not {type(dt)}")

    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        return dt.replace(tzinfo=dt.tzinfo).astimezone(tz=datetime.timezone.utc)
    else:
        raise ValueError("dt does not have timezone info")


def datetime_remove_tz(dt: datetime.datetime) -> datetime.datetime:
    """Remove timezone from a datetime.datetime object

    Args:
        dt: datetime.datetime object with tzinfo

    Returns:
        dt without any timezone info (naive datetime object)

    Raises:
        TypeError if dt is not a datetime.datetime object
    """

    if type(dt) != datetime.datetime:
        raise TypeError(f"dt must be type datetime.datetime, not {type(dt)}")

    return dt.replace(tzinfo=None)


def datetime_naive_to_utc(dt: datetime.datetime) -> datetime.datetime:
    """Convert naive (timezone unaware) datetime.datetime
        to aware timezone in UTC timezone

    Args:
        dt: datetime.datetime without timezone

    Returns:
        datetime.datetime with UTC timezone

    Raises:
        TypeError if dt is not a datetime.datetime object
        ValueError if dt is not a naive/timezone unaware object
    """

    if type(dt) != datetime.datetime:
        raise TypeError(f"dt must be type datetime.datetime, not {type(dt)}")

    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        # has timezone info
        raise ValueError(
            "dt must be naive/timezone unaware: "
            f"{dt} has tzinfo {dt.tzinfo} and offset {dt.tzinfo.utcoffset(dt)}"
        )

    return dt.replace(tzinfo=datetime.timezone.utc)


def datetime_naive_to_local(dt: datetime.datetime) -> datetime.datetime:
    """Convert naive (timezone unaware) datetime.datetime
        to aware timezone in local timezone

    Args:
        dt: datetime.datetime without timezone

    Returns:
        datetime.datetime with local timezone

    Raises:
        TypeError if dt is not a datetime.datetime object
        ValueError if dt is not a naive/timezone unaware object
    """

    if type(dt) != datetime.datetime:
        raise TypeError(f"dt must be type datetime.datetime, not {type(dt)}")

    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        # has timezone info
        raise ValueError(
            "dt must be naive/timezone unaware: "
            f"{dt} has tzinfo {dt.tzinfo} and offset {dt.tzinfo.utcoffset(dt)}"
        )

    return dt.replace(tzinfo=get_local_tz(dt))


def datetime_utc_to_local(dt: datetime.datetime) -> datetime.datetime:
    """Convert datetime.datetime object in UTC timezone to local timezone

    Args:
        dt: datetime.datetime object

    Returns:
        datetime.datetime in local timezone

    Raises:
        TypeError if dt is not a datetime.datetime object
        ValueError if dt is not in UTC timezone
    """

    if type(dt) != datetime.datetime:
        raise TypeError(f"dt must be type datetime.datetime, not {type(dt)}")

    if dt.tzinfo is not datetime.timezone.utc:
        raise ValueError(f"{dt} must be in UTC timezone: timezone = {dt.tzinfo}")

    return dt.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)


def datetime_to_new_tz(dt: datetime.datetime, offset) -> datetime.datetime:
    """Convert datetime.datetime object from current timezone to new timezone with offset of seconds from UTC"""
    if not datetime_has_tz(dt):
        raise ValueError("dt must be timezone aware")

    time_delta = datetime.timedelta(seconds=offset)
    tz = datetime.timezone(time_delta)
    return dt.astimezone(tz=tz)


def utc_offset_seconds(dt: datetime.datetime) -> int:
    """Return offset in seconds from UTC for timezone aware datetime.datetime object

    Args:
        dt: datetime.datetime object

    Returns:
        offset in seconds from UTC

    Raises:
        ValueError if dt does not have timezone information
    """

    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        return dt.tzinfo.utcoffset(dt).total_seconds()
    else:
        raise ValueError("dt does not have timezone info")
