"""Utilities for working with Photo dates in Apple Photos; used by osxphotos timewarp command"""

from __future__ import annotations

import datetime
import os
import pathlib
import sqlite3
from typing import Callable
from zoneinfo import ZoneInfo

import photoscript
from strpdatetime import strpdatetime
from tenacity import retry, stop_after_attempt, wait_exponential

from ._constants import _DB_TABLE_NAMES, SQLITE_CHECK_SAME_THREAD
from .datetime_utils import (
    datetime_has_tz,
    datetime_naive_to_local,
    datetime_remove_tz,
    datetime_tz_to_utc,
    datetime_utc_to_local,
    get_local_tz,
    utc_offset_seconds,
)
from .platform import assert_macos
from .utils import get_last_library_path, get_system_library_path

assert_macos()

from .photos_datetime import photos_datetime, photos_datetime_local
from .photosdb.photosdb_utils import get_photos_library_version
from .phototz import PhotoTimeZone, PhotoTimeZoneUpdater
from .timeutils import get_valid_timezone, timezone_for_delta_seconds, update_datetime
from .timezones import Timezone

MACOS_TIME_EPOCH = datetime.datetime(2001, 1, 1, 0, 0, 0)


def reset_photo_date_time_tz(
    photo: photoscript.Photo, library_path: str, verbose: Callable[..., None]
):
    """Reset the date/time/timezone of a photo to the original values
    Args:
            photo: photo to reset
            library_path: path to the Photos library
            verbose: callable to print verbose output
    """
    date_original = get_photo_date_original(photo, library_path)
    if not date_original:
        verbose(
            f"Could not get original date for photo {photo.filename} ({photo.uuid})"
        )
        return
    date_current = get_photo_date_created(photo, library_path)
    tz = date_original.tzinfo.tzname(date_original)
    tz_updater = PhotoTimeZoneUpdater(
        timezone=Timezone(tz), verbose=verbose, library_path=library_path
    )
    tz_updater.update_photo(photo)
    update_photo_date_time(
        library_path=library_path,
        photo=photo,
        date=date_original.date(),
        time=date_original.time(),
        date_delta=None,
        time_delta=None,
        verbose=verbose,
    )
    verbose(
        f"Reset original date/time for photo [filename]{photo.filename}[/filename] "
        f"([uuid]{photo.uuid}[/uuid]) from: [time]{date_current}[/time] to [time]{date_original}[/time]"
    )


def update_photo_date_time(
    library_path: str,
    photo: photoscript.Photo,
    date: datetime.date | None,
    time: datetime.time | None,
    date_delta: datetime.timedelta | None,
    time_delta: datetime.timedelta | None,
    verbose: Callable[..., None],
) -> datetime.datetime | None:
    """Update date, time in photo.

    Args:
        library_path: path to Photos library
        photo: photo to update
        date: new date
        time: new time
        date_delta: timedelta to add to date
        time_delta: timedelta to add to time
        verbose: callable to print verbose output

    Returns: datetime photo was set to or None if photo not updated

    Raises:
        ValueError: if date and date_delta are both set or if time and time_delta are both set
        ValueError: if timezone cannot be set
    Note: date & date_delta, time & time_delta are mutually exclusive
    """
    if date and date_delta:
        raise ValueError("date and date_delta are mutually exclusive")
    if time and time_delta:
        raise ValueError("time and time_delta are mutually exclusive")

    photo_date = photo.date
    tz_offset_sec, _, tz_name = PhotoTimeZone(library_path=library_path).get_timezone(
        photo
    )

    # if adjusting time, need to adjust for timezone offset from local time
    # as AppleScript sets time in local time
    # if time_delta provided use that as setting time & time_delta are mutually exclusive
    local_time_delta = time_delta or local_tz_delta_from_photo_tz(
        photo_date, tz_offset_sec
    )
    new_photo_date = update_datetime(
        photo_date,
        date=date,
        time=time,
        date_delta=date_delta,
        time_delta=time_delta,
        local_time_delta=local_time_delta,
    )
    filename = photo.filename
    uuid = photo.uuid
    if new_photo_date != photo_date:
        photo.date = new_photo_date
        # convert to photo's timezone for display
        # if this isn't done then the time will be displayed in local time which may be confusing
        try:
            # a timezone like "GMT-0500", which is valid on macOS won't work for apply_tz_to_date
            # so find a valid timezone if we can or use the local timezone
            # this is just for display to user and doesn't affect the actual date/time
            tz_name = get_valid_timezone(tz_name, photo.date)
        except ValueError as e:
            # use local timezone if we can't get a valid timezone
            tz_name = get_local_tz(photo.date).tzname(photo.date)
        photo_date_tz = apply_tz_to_date(photo_date, tz_name)
        new_photo_date_tz = apply_tz_to_date(new_photo_date, tz_name)
        verbose(
            f"Updated date/time for photo [filename]{filename}[/filename] "
            f"([uuid]{uuid}[/uuid]) from: [time]{photo_date_tz}[/time] to [time]{new_photo_date_tz}[/time]"
        )
        return new_photo_date_tz
    else:
        verbose(
            f"Skipped date/time update for photo [filename]{filename}[/filename] "
            f"([uuid]{uuid}[/uuid]): nothing to do"
        )
        return None


def update_photo_from_function(
    library_path: str,
    function: Callable,
    verbose: Callable[..., None],
    photo: photoscript.Photo,
    path: str | None,
):
    """Update photo from function call"""
    photo_tz_sec, _, photo_tz_name = PhotoTimeZone(
        library_path=library_path
    ).get_timezone(photo)
    dt_new, tz_new = function(
        photo=photo,
        path=path,
        tz_sec=photo_tz_sec,
        tz_name=photo_tz_name,
        verbose=verbose,
    )
    if dt_new != photo.date:
        old_date = photo.date
        photo.date = dt_new
        verbose(
            f"Updated date/time for photo [filename]{photo.filename}[/filename] "
            f"([uuid]{photo.uuid}[/uuid]) from: [time]{old_date}[/time] to [time]{dt_new}[/time]"
        )
    else:
        verbose(
            f"Skipped date/time update for photo [filename]{photo.filename}[/filename] "
            f"([uuid]{photo.uuid}[/uuid]): nothing to do"
        )
    if tz_new != photo_tz_sec:
        tz_updater = PhotoTimeZoneUpdater(
            timezone=Timezone(tz_new), verbose=verbose, library_path=library_path
        )
        tz_updater.update_photo(photo)
    else:
        verbose(
            f"Skipped timezone update for photo [filename]{photo.filename}[/filename] "
            f"([uuid]{photo.uuid}[/uuid]): nothing to do"
        )


def update_photo_time_for_new_timezone(
    library_path: str,
    photo: photoscript.Photo,
    new_timezone: Timezone,
    verbose: Callable[..., None],
):
    """Update time in photo to keep it the same time but in a new timezone

    For example, photo time is 12:00+0100 and new timezone is +0200,
    so adjust photo time by 1 hour so it will now be 12:00+0200 instead of
    13:00+0200 as it would be with no adjustment to the time"""
    old_timezone_offset = PhotoTimeZone(library_path=library_path).get_timezone(photo)[
        0
    ]
    delta = old_timezone_offset - new_timezone.offset
    photo_date = photo.date
    new_photo_date = update_datetime(
        dt=photo_date, time_delta=datetime.timedelta(seconds=delta)
    )
    filename = photo.filename
    uuid = photo.uuid
    if photo_date != new_photo_date:
        photo.date = new_photo_date
        verbose(
            f"Adjusted local date/time for photo [filename]{filename}[/] ([uuid]{uuid}[/]) to [time]{new_photo_date}[/] "
            f"to match previous time [time]{photo_date}[/] but in new timezone [tz]{new_timezone}[/]."
        )
        # get datetime for photo in new timezone
        new_photo_date_tz = apply_tz_to_date(new_photo_date, new_timezone.name)
        verbose(
            f"Photo date/time is now [time]{new_photo_date_tz}[/] in new timezone [tz]{new_timezone}[/]."
        )
    else:
        verbose(
            f"Skipping date/time update for photo [filename]{filename}[/] ([uuid]{photo.uuid}[/]), "
            f"already matches new timezone [tz]{new_timezone}[/]"
        )


def set_photo_date_from_filename(
    photo: photoscript.Photo,
    filepath: pathlib.Path | str,
    parse_date: str,
    verbose: Callable[..., None],
    library_path: str | None = None,
):
    """Set date/time of photo from filename

    Args:
        photo: Photo to set date
        filepath: Path to photo's original file
        parse_date: strptime format string to parse date from filename
        verbose: verbose function to use for logging
        library_path: Path to Photos library; if not provided, will attempt to determine automatically

    Returns:
        datetime.datetime: date set on photo or None if date could not be parsed or photo not updated
    """

    if not isinstance(filepath, pathlib.Path):
        filepath = pathlib.Path(filepath)

    try:
        date = strpdatetime(filepath.name, parse_date)
    except ValueError:
        verbose(
            f"[warning]Could not parse date/time from filename [filename]{filepath.name}[/][/]"
        )
        return

    new_date = update_photo_date_time(
        library_path=library_path,
        photo=photo,
        date=date.date(),
        time=date.time(),
        date_delta=None,
        time_delta=None,
        verbose=verbose,
    )
    # # first, set date on photo without timezone (Photos will assume local timezone)
    # date_no_tz = datetime_remove_tz(date) if datetime_has_tz(date) else date
    # verbose(
    #     f"Setting date/time of photo [filename]{filepath.name}[/] to [time]{date_no_tz.strftime('%Y-%m-%d %H:%M:%S')}[/]"
    # )
    # photo.date = date_no_tz
    if datetime_has_tz(date):
        # if timezone, need to update timezone and also the date/time to match
        photo_tz_sec, _, photo_tz_name = PhotoTimeZone(
            library_path=library_path
        ).get_timezone(photo)
        tz_new_secs = int(utc_offset_seconds(date))
        if photo_tz_sec != tz_new_secs:
            # get named timezone that matches the new UTC offset
            # this is a bit of a hack as the timezone name is not encoded in a string like an ISO8601 format
            # but need to set the photo to a valid timezone which something like GMT-0400 is not
            try:
                tz_name = timezone_for_delta_seconds(tz_new_secs, date)
            except ValueError:
                verbose(
                    f"Could not find matching timezone for delta seconds: {tz_new_secs} for date {date}"
                )
                return
            tz_new = Timezone(tz_name)
            update_photo_time_for_new_timezone(library_path, photo, tz_new, verbose)
            tz_updater = PhotoTimeZoneUpdater(
                timezone=tz_new,
                verbose=verbose,
                library_path=library_path,
            )
            tz_updater.update_photo(photo)


def set_photo_date_added(
    photo: photoscript.Photo,
    date_added: datetime.datetime,
    verbose: Callable[..., None],
    library_path: str | None = None,
):
    """Modify the ADDEDDATE of a photo

    Args:
        photo: Photo to modify
        date_added: New date added for photo (naive datetime in local timezone)
        verbose: verbose function to use for logging
        library_path: Path to Photos library; if not provided, will attempt to determine automatically
    """

    if not (library_path := _get_photos_library_path(library_path)):
        raise ValueError("Could not determine Photos library path")
    verbose(
        f"Setting date added for photo [filename]{photo.filename}[/] to [time]{date_added}[/]"
    )

    # convert date_added form local timezone to UTC then remove timezone
    date_added = datetime_naive_to_local(date_added)
    date_added = date_added.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    _set_date_added(library_path, photo.uuid, date_added)

    # Need to update the date on the photo to force Photos to sync date/time changes to iCloud
    photo.date = photo.date + datetime.timedelta(seconds=1)
    photo.date = photo.date - datetime.timedelta(seconds=1)


@retry(
    wait=wait_exponential(multiplier=1, min=0.100, max=5),
    stop=stop_after_attempt(10),
)
def _set_date_added(library_path: str, uuid: str, date_added: datetime.datetime):
    """Set the ADDEDDATE of a photo

    Args:
            library_path: Path to Photos library
            uuid: UUID of photo
            date_added: New date added for photo (naive in UTC)

    Raises:
        FileNotFoundError: If Photos library path is not found or Photos database is not found
    """
    # Use retry decorator to retry if database is locked
    if not os.path.exists(library_path):
        raise FileNotFoundError(f"Photos library path not found: {library_path}")
    photos_version = get_photos_library_version(library_path)
    db_path = str(pathlib.Path(library_path) / "database/Photos.sqlite")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Photos database not found: {db_path}")
    asset_table = _DB_TABLE_NAMES[photos_version]["ASSET"]

    timestamp = datetime_to_photos_timestamp(date_added)
    conn = sqlite3.connect(db_path, check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    c.execute(
        f"UPDATE {asset_table} SET ZADDEDDATE=? WHERE ZUUID=?",
        (timestamp, uuid),
    )
    conn.commit()
    conn.close()


def _get_photos_library_path(library_path: str | None = None) -> str:
    """Return path to the Photos library or None if not found"""
    # get_last_library_path() returns the path to the last Photos library
    # opened but sometimes (rarely) fails on some systems
    try:
        library_path = (
            library_path or get_last_library_path() or get_system_library_path()
        )
    except Exception:
        library_path = None
    return library_path


def datetime_to_photos_timestamp(dt: datetime.datetime) -> float:
    """Convert naive datetime to Photos timestamp (seconds since 2001-01-01)"""
    return float((dt - MACOS_TIME_EPOCH).total_seconds())


@retry(
    wait=wait_exponential(multiplier=1, min=0.100, max=5),
    stop=stop_after_attempt(5),
)
def get_photo_date_added(
    photo: photoscript.Photo,
    library_path: str | None = None,
) -> datetime.datetime | None:
    """Get the ADDEDDATE of a photo

    Args:
        photo: Photo to get date added
        library_path: Path to Photos library; if not provided, will attempt to determine automatically

    Returns: datetime.datetime: date added of photo or None if date added cannot be determined

    Raises:
        ValueError if library_path is None and Photos library path cannot be determined
        FileNotFoundError if Photos database path cannot be found
    """

    if not (library_path := _get_photos_library_path(library_path)):
        raise ValueError("Could not determine Photos library path")

    photos_version = get_photos_library_version(library_path)
    db_path = str(pathlib.Path(library_path) / "database/Photos.sqlite")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Photos database not found at {db_path}")
    asset_table = _DB_TABLE_NAMES[photos_version]["ASSET"]
    conn = sqlite3.connect(db_path, check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    c.execute(
        f"SELECT ZADDEDDATE FROM {asset_table} WHERE ZUUID=?;",
        (photo.uuid,),
    )
    row = c.fetchone()
    conn.close()
    return photos_datetime_local(row[0])


@retry(
    wait=wait_exponential(multiplier=1, min=0.100, max=5),
    stop=stop_after_attempt(5),
)
def _get_photo_date_original(
    photo: photoscript.Photo,
    library_path: str | None = None,
) -> datetime.datetime | None:
    """Get the original date of a photo as timezone aware datetime
    (date Photos recorded as creation date at import) or None if not found

    Args:
        photo: photoscript.Photo object
        library_path: path to Photos library or None to use last opened library

    Raises:
        ValueError if library_path is None and Photos library path cannot be determined
        FileNotFoundError if Photos database path cannot be found
    """

    if not (library_path := _get_photos_library_path(library_path)):
        raise ValueError("Could not determine Photos library path")

    photos_version = get_photos_library_version(library_path)
    db_path = str(pathlib.Path(library_path) / "database/Photos.sqlite")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Photos database not found at {db_path}")
    asset_table = _DB_TABLE_NAMES[photos_version]["ASSET"]
    conn = sqlite3.connect(db_path, check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    try:
        c.execute(
            f"""
            SELECT
                ZEXTENDEDATTRIBUTES.ZDATECREATED,
                ZEXTENDEDATTRIBUTES.ZTIMEZONEOFFSET,
                ZEXTENDEDATTRIBUTES.ZTIMEZONENAME
            FROM ZEXTENDEDATTRIBUTES
            JOIN {asset_table}
                ON ZEXTENDEDATTRIBUTES.ZASSET = {asset_table}.Z_PK
            WHERE {asset_table}.ZUUID = ?;
            """,
            (photo.uuid,),
        )
        row = c.fetchone()
    except sqlite3.OperationalError as e:
        # error will be no such column: ZEXTENDEDATTRIBUTES.ZDATECREATED
        # if on Photos < 8.0 / Ventura
        if "ZEXTENDEDATTRIBUTES.ZDATECREATED" in str(e):
            row = None
        else:
            raise e
    conn.close()
    if row and row[0] is not None:
        return photos_datetime(timestamp=row[0], tzoffset=row[1], tzname=row[2])
    else:
        return None


@retry(
    wait=wait_exponential(multiplier=1, min=0.100, max=5),
    stop=stop_after_attempt(5),
)
def get_photo_date_created(
    photo: photoscript.Photo,
    library_path: str | None = None,
) -> datetime.datetime:
    """Get the creation date of a photo as timezone aware datetime or default date if not found or error converting date

    Args:
        photo: photoscript.Photo object
        library_path: path to Photos library or None to use last opened library

    Raises:
        ValueError if library_path is None and Photos library path cannot be determined
        FileNotFoundError if Photos database path cannot be found
    """

    if not (library_path := _get_photos_library_path(library_path)):
        raise ValueError("Could not determine Photos library path")

    photos_version = get_photos_library_version(library_path)
    db_path = str(pathlib.Path(library_path) / "database/Photos.sqlite")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Photos database not found at {db_path}")
    asset_table = _DB_TABLE_NAMES[photos_version]["ASSET"]
    conn = sqlite3.connect(db_path, check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    c.execute(
        f"""
        SELECT
            {asset_table}.ZDATECREATED,
            ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET,
            ZADDITIONALASSETATTRIBUTES.ZTIMEZONENAME
        FROM {asset_table}
        JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK
        WHERE {asset_table}.ZUUID = ?;
        """,
        (photo.uuid,),
    )
    row = c.fetchone()
    conn.close()
    if row and row[0] is not None:
        return photos_datetime(
            timestamp=row[0], tzoffset=row[1], tzname=row[2], default=True
        )
    else:
        return photos_datetime(None, default=True)


def get_photo_date_original(
    photo: photoscript.Photo,
    library_path: str | None = None,
) -> datetime.datetime | None:
    """Get the original date of a photo as timezone aware datetime
    (date Photos recorded as creation date at import) or None if not found

    Args:
        photo: photoscript.Photo object
        library_path: path to Photos library or None to use last opened library

    Raises:
        ValueError if library_path is None and Photos library path cannot be determined
        FileNotFoundError if Photos database path cannot be found
    """
    return _get_photo_date_original(photo, library_path) or get_photo_date_created(
        photo, library_path
    )


def local_tz_delta_from_photo_tz(
    dt: datetime.datetime, tz_offset_sec: int
) -> datetime.timedelta:
    """Given a photo's datetime (naive) and the timezone offset in seconds, return the timedelta between the photo's timezone and the local timezone"""
    local_delta_sec = get_local_tz(dt).utcoffset(dt).total_seconds() - tz_offset_sec
    local_delta = datetime.timedelta(seconds=local_delta_sec)
    return local_delta


def apply_tz_to_date(dt: datetime.datetime, tz: str) -> datetime.datetime:
    """Apply timezone to a naive datetime object.

    Args:
        dt: datetime.datetime object to apply timezone to
        tz: timezone name (e.g. 'America/New_York')

    Returns datetime object with timezone applied or original datetime object if error
    """
    try:
        return datetime_naive_to_local(dt).astimezone(ZoneInfo(tz))
    except Exception as e:
        return dt
