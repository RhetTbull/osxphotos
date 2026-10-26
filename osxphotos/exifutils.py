"""Utilities for working with EXIF and other photo metadata."""

from __future__ import annotations

import datetime
import logging
import re
from collections import namedtuple
from typing import Any

logger = logging.getLogger("osxphotos")

# date/time/timezone extracted from regex as a timezone aware datetime.datetime object
# default_time is True if the time is not specified in the exif otherwise False (and if True, set to 00:00:00)
# default_offset is True if timezone offset is not specified in the exif otherwise False (and if True, set to +00:00)
# used_file_modify_date is True if the date/time is not specified in the exif and the FileModifyDate is used instead
ExifDateTime = namedtuple(
    "ExifDateTime",
    [
        "datetime",
        "offset_seconds",
        "offset_str",
        "default_time",
        "used_file_modify_date",
    ],
)


# fields used only as a last resort when use_file_modify_date is True
FILE_MODIFY_DATE_FIELDS = ("File:FileModifyDate", "FileModifyDate")

# non-standard date/time strings, tried only when no field holds a date in
# standard EXIF form (YYYY:MM:DD HH:MM:SS); see #2274
# DD.MM.YYYY [HH:MM[:SS]]: day-first, the common European convention
_DOTTED_DATE_RE = re.compile(
    r"^(\d{1,2})\.(\d{1,2})\.(\d{4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$"
)
# YYYY-MM-DD or YYYY/MM/DD [HH:MM[:SS][.fff]][+HH:MM|Z]
_YMD_DATE_RE = re.compile(
    r"^(\d{4})([-/])(\d{1,2})\2(\d{1,2})"
    r"(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?)?"
    r"(Z|[+-]\d{2}:?\d{2})?$"
)


def exif_offset_to_seconds(offset: str) -> int:
    """Convert timezone offset from UTC in exiftool format (+/-hh:mm) to seconds"""

    # Z (for Zulu time) corresponds to a zero UTC offset
    if offset == "Z":
        return 0

    sign = 1 if offset[0] == "+" else -1
    hours, minutes = offset[1:].split(":")
    return sign * (int(hours) * 3600 + int(minutes) * 60)


def get_exif_date_time_offset(
    exif: dict[str, Any], use_file_modify_date: bool = False
) -> ExifDateTime:
    """Get datetime/offset from an exif dict as returned by osxphotos.exiftool.ExifTool.asdict() or exiftool -j

    Args:
        exif: dict of exif data
        use_file_modify_date: if True, use the file modify date if there's no date/time in the exif data

    Note:
        Fields are tried in priority order. A field whose value can't be parsed no longer hides
        the fields after it: every field is first tried in standard EXIF form (YYYY:MM:DD HH:MM:SS);
        only if none parses are common non-standard forms (DD.MM.YYYY HH:MM[:SS],
        YYYY-MM-DD HH:MM:SS, YYYY/MM/DD HH:MM:SS) tried. The file modify date, if requested,
        is used only after both passes fail.
    """

    # search these fields in this order for date/time/timezone
    # Prioritize QuickTime:ContentCreateDate over EXIF:DateTimeOriginal for videos
    time_fields = [
        "Composite:DateTimeCreated",
        "Composite:SubSecDateTimeOriginal",
        "Composite:SubSecCreateDate",
        "QuickTime:ContentCreateDate",
        "QuickTime:CreationDate",
        "QuickTime:CreateDate",
        "EXIF:DateTimeOriginal",
        "EXIF:CreateDate",
        "IPTC:DateCreated",
        "XMP-exif:DateTimeOriginal",
        "XMP-xmp:DateCreated",
        "XMP-xmp:CreateDate",
        "XMP:DateTimeOriginal",
        "XMP:DateCreated",
        "XMP:CreateDate",
        "DateTimeCreated",
        "DateTimeOriginal",
        "DateCreated",
        "CreateDate",
        "ContentCreateDate",
        "CreationDate",
    ]

    # offset stored separately from the date/time string, if any
    exif_offset = exif.get("EXIF:OffsetTimeOriginal") or exif.get("OffsetTimeOriginal")

    # (field, value) for every field that has a value, in priority order
    candidates = [
        (field, value)
        for field in time_fields
        if (value := _get_exif_date_value(exif, field))
    ]
    file_candidates = (
        [
            (field, value)
            for field in FILE_MODIFY_DATE_FIELDS
            if (value := _get_exif_date_value(exif, field))
        ]
        if use_file_modify_date
        else []
    )

    # 1st pass: every field in standard EXIF form
    for field, value in candidates:
        result = _parse_exif_date_time(value, exif_offset)
        if result.datetime is not None:
            return result

    # 2nd pass: every field in a non-standard form
    for field, value in candidates:
        result = _parse_non_standard_date_time(value, exif_offset)
        if result is not None:
            logger.info(
                f"Parsed non-standard date/time {value!r} in {field} as {result.datetime}"
            )
            return result

    # last resort: the file modify date
    for field, value in file_candidates:
        result = _parse_exif_date_time(value, exif_offset)
        if result.datetime is not None:
            return result._replace(used_file_modify_date=True)

    for field, value in candidates + file_candidates:
        logger.warning(f"Could not parse date/time {value!r} in {field}")

    # nothing parsed; return what the first field with a value gave, as before
    if candidates or file_candidates:
        field, value = (candidates + file_candidates)[0]
        result = _parse_exif_date_time(value, exif_offset)
        return result._replace(used_file_modify_date=field in FILE_MODIFY_DATE_FIELDS)
    return _parse_exif_date_time(None, exif_offset)


def _get_exif_date_value(exif: dict[str, Any], field: str) -> str | None:
    """Return the date/time value of field in exif or None if field is missing or empty"""
    dt = exif.get(field)
    # Some old mp4 may return ContentCreationDate as YYYY (eg. 2014) which
    # is converted to int causing re.match(pattern, dt) to fail.
    dt = str(dt) if isinstance(dt, int) else dt
    if not dt or not isinstance(dt, str):
        return None
    if field in {"IPTC:DateCreated", "DateCreated"}:
        # also need time
        time_ = exif.get("IPTC:TimeCreated") or exif.get("TimeCreated")
        dt = f"{dt} {time_}" if time_ else dt
    return dt


def _parse_exif_date_time(dt: str | None, offset: str | None) -> ExifDateTime:
    """Parse a date/time string in standard EXIF form (YYYY:MM:DD HH:MM:SS[.fff][+HH:MM])

    Args:
        dt: date/time string or None
        offset: timezone offset (+/-HH:MM) stored separately from dt, e.g. EXIF:OffsetTimeOriginal

    Returns: ExifDateTime; datetime is None if dt can't be parsed
    """
    default_time = False
    if dt and offset is None:
        # see if offset set in the dt string
        for pattern in (
            r"\d{4}:\d{2}:\d{2}\s\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2})",
            r"\d{4}:\d{2}:\d{2}\s\d{2}:\d{2}:\d{2}\.\d+([+-]\d{2}:\d{2})",
        ):
            matched = re.match(pattern, dt)
            if matched:
                offset = matched.group(1)
                break
        else:
            offset = None

    if dt:
        # make sure we have time
        matched = re.match(r"\d{4}:\d{2}:\d{2}\s(\d{2}:\d{2}:\d{2})", dt)
        if not matched:
            if matched := re.match(r"^(\d{4}:\d{2}:\d{2})", dt):
                # set time to 00:00:00
                dt = f"{matched.group(1)} 00:00:00"
                default_time = True

    if offset is not None:
        # make sure we have offset
        if not re.match(r"([+-]\d{2}:\d{2})", offset):
            offset = None

    offset_seconds = exif_offset_to_seconds(offset) if offset else None

    if dt:
        if offset is not None:
            # drop offset from dt string and add it back on in datetime %z format
            dt = re.sub(r"[+-]\d{2}:\d{2}$", "", dt)
            dt = re.sub(r"\.\d+$", "", dt)
            offset = offset.replace(":", "")
            dt = f"{dt}{offset}"
            dt_format = "%Y:%m:%d %H:%M:%S%z"
        else:
            dt = re.sub(r"\.\d+$", "", dt)
            dt_format = "%Y:%m:%d %H:%M:%S"

        # convert to datetime
        # some files can have bad date/time data, (e.g. #24, Date/Time Original = 0000:00:00 00:00:00)
        try:
            dt = datetime.datetime.strptime(dt, dt_format)
        except ValueError:
            dt = None
    else:
        dt = None

    # format offset in form +/-hhmm
    offset_str = offset.replace(":", "") if offset else ""
    return ExifDateTime(dt, offset_seconds, offset_str, default_time, False)


def _parse_non_standard_date_time(dt: str, offset: str | None) -> ExifDateTime | None:
    """Parse a date/time string in a common non-standard form

    Handles DD.MM.YYYY [HH:MM[:SS]] (day-first; month-first only if day-first is not a valid date)
    and YYYY-MM-DD / YYYY/MM/DD [HH:MM[:SS][.fff]][+HH:MM|Z].

    Args:
        dt: date/time string
        offset: timezone offset (+/-HH:MM) stored separately from dt, e.g. EXIF:OffsetTimeOriginal

    Returns: ExifDateTime or None if dt can't be parsed
    """
    dt = dt.strip()
    dt_offset = None
    if matched := _DOTTED_DATE_RE.match(dt):
        day, month, year, hour, minute, second = matched.groups()
        date_orders = ((day, month), (month, day))
    elif matched := _YMD_DATE_RE.match(dt):
        year, _, month, day, hour, minute, second, dt_offset = matched.groups()
        date_orders = ((day, month),)
    else:
        return None

    default_time = hour is None
    parsed = None
    for day_, month_ in date_orders:
        try:
            parsed = datetime.datetime(
                int(year),
                int(month_),
                int(day_),
                int(hour or 0),
                int(minute or 0),
                int(second or 0),
            )
            break
        except ValueError:
            continue
    if parsed is None:
        return None

    if offset is None or not re.match(r"[+-]\d{2}:\d{2}$", offset):
        offset = None
        if dt_offset == "Z":
            offset = "+00:00"
        elif dt_offset:
            offset = f"{dt_offset[:3]}:{dt_offset[-2:]}"

    if offset:
        parsed = parsed.replace(
            tzinfo=datetime.timezone(
                datetime.timedelta(seconds=exif_offset_to_seconds(offset))
            )
        )
    return ExifDateTime(
        parsed,
        exif_offset_to_seconds(offset) if offset else None,
        offset.replace(":", "") if offset else "",
        default_time,
        False,
    )


def angle_to_exif_orientation(angle: int) -> int:
    """Convert angle, in degrees, to EXIF orientation value.

    Args:
        angle: angle in degrees (0, 90, 180, 270) as clockwise rotation from normal orientation

    Returns:
        EXIF orientation value as integer
    """
    if angle % 90 != 0:
        raise ValueError(f"angle must be a multiple of 90: {angle}")

    orientation_map = {0: 1, 90: 6, 180: 3, 270: 8}

    return orientation_map[angle % 360]
