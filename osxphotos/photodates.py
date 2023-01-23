"""Utilities for working with Photo dates in Apple Photos; used by osxphotos timewarp command"""

from __future__ import annotations

import datetime
import pathlib
from typing import Callable

import photoscript
from strpdatetime import strpdatetime

from .datetime_utils import (
    datetime_has_tz,
    datetime_remove_tz,
    datetime_tz_to_utc,
    datetime_utc_to_local,
    utc_offset_seconds,
)
from .phototz import PhotoTimeZone, PhotoTimeZoneUpdater
from .timeutils import update_datetime
from .timezones import Timezone


def update_photo_date_time(
    photo: photoscript.Photo,
    date,
    time,
    date_delta,
    time_delta,
    verbose: Callable,
):
    """Update date, time in photo"""
    photo_date = photo.date
    new_photo_date = update_datetime(
        photo_date, date=date, time=time, date_delta=date_delta, time_delta=time_delta
    )
    filename = photo.filename
    uuid = photo.uuid
    if new_photo_date != photo_date:
        photo.date = new_photo_date
        verbose(
            f"Updated date/time for photo [filename]{filename}[/filename] "
            f"([uuid]{uuid}[/uuid]) from: [time]{photo_date}[/time] to [time]{new_photo_date}[/time]"
        )
    else:
        verbose(
            f"Skipped date/time update for photo [filename]{filename}[/filename] "
            f"([uuid]{uuid}[/uuid]): nothing to do"
        )


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
    old_timezone = PhotoTimeZone(library_path=library_path).get_timezone(photo)[0]
    # need to move time in opposite direction of timezone offset so that
    # photo time is the same time but in the new timezone
    delta = old_timezone - new_timezone.offset
    photo_date = photo.date
    new_photo_date = update_datetime(
        dt=photo_date, time_delta=datetime.timedelta(seconds=delta)
    )
    filename = photo.filename
    uuid = photo.uuid
    if photo_date != new_photo_date:
        photo.date = new_photo_date
        verbose(
            f"Adjusted date/time for photo [filename]{filename}[/] ([uuid]{uuid}[/]) to [time]{new_photo_date}[/] "
            f"to match previous time [time]{photo_date}[/] but in new timezone [tz]{new_timezone}[/]."
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
) -> datetime.datetime | None:
    """Set date of photo from filename

    Args:
        photo: Photo to set date
        filepath: Path to photo's original file
        parse_date: strptime format string to parse date from filename
        verbose: verbose function to use for logging
        library_path: Path to Photos library; if not provided, will attempt to determine automatically

    Returns:
        datetime.datetime: date set on photo or None if date could not be parsed
    """

    if not isinstance(filepath, pathlib.Path):
        filepath = pathlib.Path(filepath)

    try:
        date = strpdatetime(filepath.name, parse_date)
    except ValueError:
        verbose(
            f"[warning]Could not parse date from filename [filename]{filepath.name}[/][/]"
        )
        return None

    # first, set date on photo without timezone (Photos will assume local timezone)
    date_no_tz = datetime_remove_tz(date) if datetime_has_tz(date) else date
    verbose(
        f"Setting date of photo [filename]{filepath.name}[/] to [time]{date_no_tz.strftime('%Y-%m-%d %H:%M:%S')}[/]"
    )
    photo.date = date_no_tz
    if datetime_has_tz(date):
        # if timezone, need to update timezone and also the date/time to match
        photo_tz_sec, _, photo_tz_name = PhotoTimeZone(
            library_path=library_path
        ).get_timezone(photo)
        tz_new_secs = int(utc_offset_seconds(date))
        if photo_tz_sec != tz_new_secs:
            tz_new = Timezone(tz_new_secs)
            update_photo_time_for_new_timezone(library_path, photo, tz_new, verbose)
            tz_updater = PhotoTimeZoneUpdater(
                timezone=tz_new,
                verbose=verbose,
                library_path=library_path,
            )
            tz_updater.update_photo(photo)

    return date
