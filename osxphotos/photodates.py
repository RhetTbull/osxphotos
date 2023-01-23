"""Utilities for working with Photo dates"""

from __future__ import annotations

import datetime
import pathlib
from typing import Callable, Optional

import photoscript
from strpdatetime import strpdatetime

from .datetime_utils import (
    datetime_has_tz,
    datetime_remove_tz,
    datetime_tz_to_utc,
    datetime_utc_to_local,
)


def set_photo_date_from_filename(
    photo: photoscript.Photo,
    filepath: pathlib.Path | str,
    parse_date: str,
    verbose: Callable[..., None],
) -> datetime.datetime | None:
    """Set date of photo from filename"""
    # TODO: handle timezone (use code from timewarp), for now convert timezone to local timezone

    if not isinstance(filepath, pathlib.Path):
        filepath = pathlib.Path(filepath)

    try:
        date = strpdatetime(filepath.name, parse_date)
        # Photo.date must be timezone naive (assumed to local timezone)
        if datetime_has_tz(date):
            local_date = datetime_remove_tz(
                datetime_utc_to_local(datetime_tz_to_utc(date))
            )
            verbose(
                f"Moving date with timezone [time]{date}[/] to local timezone: [time]{local_date.strftime('%Y-%m-%d %H:%M:%S')}[/]"
            )
            date = local_date
    except ValueError:
        verbose(
            f"[warning]Could not parse date from filename [filename]{filepath.name}[/][/]"
        )
        return None
    verbose(
        f"Setting date of photo [filename]{filepath.name}[/] to [time]{date.strftime('%Y-%m-%d %H:%M:%S')}[/]"
    )
    photo.date = date
    return date
