"""Use exiftool to update exif data in photos """

import datetime
import re
from collections import namedtuple
from typing import Callable, Dict, Optional, Tuple

from photoscript import Photo

from .datetime_utils import (
    datetime_has_tz,
    datetime_naive_to_local,
    datetime_remove_tz,
    datetime_to_new_tz,
    datetime_tz_to_utc,
    datetime_utc_to_local,
)
from .exiftool import ExifTool
from .photosdb import PhotosDB
from .phototz import PhotoTimeZone, PhotoTimeZoneUpdater
from .timezones import Timezone, format_offset_time
from .utils import noop

__all__ = ["ExifDateTime", "ExifDateTimeUpdater"]

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


class ExifDateTimeUpdater:
    """Update exif data in photos"""

    def __init__(
        self,
        library_path: Optional[str] = None,
        verbose: Optional[Callable] = None,
        exiftool_path: Optional[str] = None,
        plain=False,
    ):
        self.library_path = library_path
        self.db = PhotosDB(self.library_path)
        self.verbose = verbose or noop
        self.exiftool_path = exiftool_path
        self.tzinfo = PhotoTimeZone(library_path=self.library_path)
        self.plain = plain

    def filename_color(self, filename: str) -> str:
        """Colorize filename for display in verbose output"""
        return filename if self.plain else f"[filename]{filename}[/filename]"

    def uuid_color(self, uuid: str) -> str:
        """Colorize uuid for display in verbose output"""
        return uuid if self.plain else f"[uuid]{uuid}[/uuid]"

    def update_exif_from_photos(self, photo: Photo) -> Tuple[str, str]:
        """Update EXIF data in photo to match the date/time/timezone in Photos library

        Args:
            photo: photoscript.Photo object to act on
        """

        # photo is the photoscript.Photo object passed in
        # _photo is the osxphotos.PhotoInfo object for the same photo
        # Need _photo to get the photo's path
        _photo = self.db.get_photo(photo.uuid)
        if not _photo:
            raise ValueError(f"Photo {photo.uuid} not found")

        if not _photo.path:
            self.verbose(
                "Skipping EXIF update for missing photo "
                f"[filename]{_photo.original_filename}[/filename] ([uuid]{_photo.uuid}[/uuid])"
            )
            return "", ""

        self.verbose(
            "Updating EXIF data for "
            f"[filename]{photo.filename}[/filename] ([uuid]{photo.uuid}[/uuid])"
        )

        photo_date = datetime_naive_to_local(photo.date)
        timezone_offset = self.tzinfo.get_timezone(photo)[0]
        photo_date = datetime_to_new_tz(photo_date, timezone_offset)

        # exiftool expects format to "2015:01:18 12:00:00"
        datetimeoriginal = photo_date.strftime("%Y:%m:%d %H:%M:%S")

        # exiftool expects format of "-04:00"
        offset = format_offset_time(timezone_offset)

        # process date/time and timezone offset
        # Photos exports the following fields and sets modify date to creation date
        # [EXIF]    Date/Time Original      : 2020:10:30 00:00:00
        # [EXIF]    Create Date             : 2020:10:30 00:00:00
        # [IPTC]    Digital Creation Date   : 2020:10:30
        # [IPTC]    Date Created            : 2020:10:30
        #
        # for videos:
        # [QuickTime]     CreateDate                      : 2020:12:11 06:10:10
        # [Keys]          CreationDate                    : 2020:12:10 22:10:10-08:00
        exif = {}
        if _photo.isphoto:
            exif["EXIF:DateTimeOriginal"] = datetimeoriginal
            exif["EXIF:CreateDate"] = datetimeoriginal
            dateoriginal = photo_date.strftime("%Y:%m:%d")
            exif["IPTC:DateCreated"] = dateoriginal
            timeoriginal = photo_date.strftime(f"%H:%M:%S{offset}")
            exif["IPTC:TimeCreated"] = timeoriginal

            exif["EXIF:OffsetTimeOriginal"] = offset

        elif _photo.ismovie:
            # QuickTime spec specifies times in UTC
            # QuickTime:CreateDate and ModifyDate are in UTC w/ no timezone
            # QuickTime:CreationDate must include time offset or Photos shows invalid values
            # reference: https://exiftool.org/TagNames/QuickTime.html#Keys
            #            https://exiftool.org/forum/index.php?topic=11927.msg64369#msg64369
            creationdate = f"{datetimeoriginal}{offset}"
            exif["QuickTime:CreationDate"] = creationdate

            # need to convert to UTC then back to formatted string
            tzdate = datetime.datetime.strptime(creationdate, "%Y:%m:%d %H:%M:%S%z")
            utcdate = datetime_tz_to_utc(tzdate)
            createdate = utcdate.strftime("%Y:%m:%d %H:%M:%S")
            exif["QuickTime:CreateDate"] = createdate

        self.verbose(
            f"Writing EXIF data with exiftool to {self.filename_color(_photo.path)}"
        )
        with ExifTool(filepath=_photo.path, exiftool=self.exiftool_path) as exiftool:
            for tag, val in exif.items():
                if type(val) == list:
                    for v in val:
                        exiftool.setvalue(tag, v)
                else:
                    exiftool.setvalue(tag, val)
        return exiftool.warning, exiftool.error

    def update_photos_from_exif(
        self, photo: Photo, use_file_modify_date: bool = False
    ) -> None:
        """Update date/time/timezone in Photos library to match the data in EXIF

        Args:
            photo: photoscript.Photo object to act on
            use_file_modify_date: if True, use the file modify date if there's no date/time in the exif data
        """

        # photo is the photoscript.Photo object passed in
        # _photo is the osxphotos.PhotoInfo object for the same photo
        # Need _photo to get the photo's path
        _photo = self.db.get_photo(photo.uuid)
        if not _photo:
            raise ValueError(f"Photo {photo.uuid} not found")

        if not _photo.path:
            self.verbose(
                "Skipping EXIF update for missing photo "
                f"[filename]{_photo.original_filename}[/filename] ([uuid]{_photo.uuid}[/uuid])"
            )
            return None

        self.verbose(
            "Updating Photos from EXIF data for "
            f"[filename]{photo.filename}[/filename] ([uuid]{photo.uuid}[/uuid])"
        )

        dtinfo = self.get_date_time_offset_from_exif(
            _photo.path, use_file_modify_date=use_file_modify_date
        )
        if dtinfo.used_file_modify_date:
            self.verbose(
                "EXIF date/time missing, using file modify date/time for "
                f"[filename]{photo.filename}[/filename] ([uuid]{photo.uuid}[/uuid])"
            )
        if not dtinfo.datetime and not dtinfo.offset_seconds:
            self.verbose(
                "Skipping update for missing EXIF data in photo "
                f"[filename]{photo.filename}[/filename] ([uuid]{photo.uuid}[/uuid])"
            )
            return None

        if dtinfo.offset_seconds:
            # update timezone then update date/time
            timezone = Timezone(dtinfo.offset_seconds)
            tzupdater = PhotoTimeZoneUpdater(
                library_path=self.library_path, timezone=timezone
            )
            tzupdater.update_photo(photo)
            self.verbose(
                "Updated timezone offset for photo "
                f"[filename]{photo.filename}[/filename] ([uuid]{photo.uuid}[/uuid]): [tz]{timezone}[/tz]"
            )

        if dtinfo.datetime:
            if datetime_has_tz(dtinfo.datetime):
                # convert datetime to naive local time for setting in photos
                local_datetime = datetime_remove_tz(
                    datetime_utc_to_local(datetime_tz_to_utc(dtinfo.datetime))
                )
            else:
                local_datetime = dtinfo.datetime
            # update date/time
            photo.date = local_datetime
            self.verbose(
                "Updated date/time for photo "
                f"[filename]{photo.filename}[/filename] ([uuid]{photo.uuid}[/uuid]): [time]{local_datetime}[/time]"
            )

        return None

    def get_date_time_offset_from_exif(
        self, photo_path: str, use_file_modify_date: bool = False
    ) -> ExifDateTime:
        """Get date/time/timezone from EXIF data for a photo

        Args:
            photo_path: path to photo to get EXIF data from
            use_file_modify_date: if True, use the file modify date if there's no date/time in the exif data

        Returns:
            ExifDateTime named tuple

        """
        exiftool = ExifTool(filepath=photo_path, exiftool=self.exiftool_path)
        exif = exiftool.asdict()
        return get_exif_date_time_offset(
            exif, use_file_modify_date=use_file_modify_date
        )

    def get_photo_path(self, photo: Photo) -> Optional[str]:
        """Get the path to a photo

        Args:
            photo: photoscript.Photo object to act on

        Returns:
            str: path to photo or None if not found
        """
        _photo = self.db.get_photo(photo.uuid)
        return _photo.path if _photo else None


def get_exif_date_time_offset(
    exif: Dict, use_file_modify_date: bool = False
) -> ExifDateTime:
    """Get datetime/offset from an exif dict as returned by osxphotos.exiftool.ExifTool.asdict()

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
        "EXIF:DateTimeOriginal",
        "EXIF:CreateDate",
        "QuickTime:ContentCreateDate",
        "QuickTime:CreationDate",
        "QuickTime:CreateDate",
        "IPTC:DateCreated",
        "XMP-exif:DateTimeOriginal",
        "XMP-xmp:CreateDate",
    ]
    if use_file_modify_date:
        time_fields.append("File:FileModifyDate")

    for dt_str in time_fields:
        dt = exif.get(dt_str)
        if dt and dt_str == "IPTC:DateCreated":
            # also need time
            time_ = exif.get("IPTC:TimeCreated")
            if not time_:
                time_ = "00:00:00"
                default_time = True
            dt = f"{dt} {time_}"

        if dt:
            used_file_modify_date = dt_str == "File:FileModifyDate"
            break
    else:
        # no date/time found
        dt = None

    # try to get offset from EXIF:OffsetTimeOriginal
    offset = exif.get("EXIF:OffsetTimeOriginal")
    if dt and not offset:
        # see if offset set in the dt string
        matched = re.match(r"\d{4}:\d{2}:\d{2}\s\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2})", dt)
        offset = matched.group(1) if matched else None

    if dt:
        # make sure we have time
        matched = re.match(r"\d{4}:\d{2}:\d{2}\s(\d{2}:\d{2}:\d{2})", dt)
        if not matched:
            if matched := re.match(r"^(\d{4}:\d{2}:\d{2})", dt):
                # set time to 00:00:00
                dt = f"{matched.group(1)} 00:00:00"
                default_time = True

    offset_seconds = exif_offset_to_seconds(offset) if offset else None

    if dt:
        if offset:
            # drop offset from dt string and add it back on in datetime %z format
            dt = re.sub(r"[+-]\d{2}:\d{2}$", "", dt)
            offset = offset.replace(":", "")
            dt = f"{dt}{offset}"
            dt_format = "%Y:%m:%d %H:%M:%S%z"
        else:
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
