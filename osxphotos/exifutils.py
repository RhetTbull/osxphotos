"""Utilities for working with EXIF and other photo metadata."""

from __future__ import annotations

import datetime
import re
from collections import namedtuple
from typing import Any

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
    """

    # set to True if no time is found
    default_time = False

    # set to True if no date/time in EXIF and the FileModifyDate is used
    used_file_modify_date = False

    # search these fields in this order for date/time/timezone
    time_fields = [
        "Composite:DateTimeCreated",
        "Composite:SubSecDateTimeOriginal",
        "Composite:SubSecCreateDate",
        "EXIF:DateTimeOriginal",
        "EXIF:CreateDate",
        "QuickTime:ContentCreateDate",
        "QuickTime:CreationDate",
        "QuickTime:CreateDate",
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
    if use_file_modify_date:
        time_fields.extend(["File:FileModifyDate", "FileModifyDate"])

    for dt_str in time_fields:
        dt = exif.get(dt_str)
        # Some old mp4 may return ContentCreationDate as YYYY (eg. 2014) which
        # is converted to int causing re.match(pattern, dt) to fail.
        dt = str(dt) if isinstance(dt, int) else dt
        if dt and dt_str in {"IPTC:DateCreated", "DateCreated"}:
            # also need time
            time_ = exif.get("IPTC:TimeCreated") or exif.get("TimeCreated")
            if not time_:
                time_ = "00:00:00"
                default_time = True
            dt = f"{dt} {time_}"

        if dt:
            used_file_modify_date = dt_str in {"File:FileModifyDate", "FileModifyDate"}
            break
    else:
        # no date/time found
        dt = None

    # try to get offset from EXIF:OffsetTimeOriginal
    offset = exif.get("EXIF:OffsetTimeOriginal") or exif.get("OffsetTimeOriginal")
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

    if offset:
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

    # format offset in form +/-hhmm
    offset_str = offset.replace(":", "") if offset else ""
    return ExifDateTime(
        dt, offset_seconds, offset_str, default_time, used_file_modify_date
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
