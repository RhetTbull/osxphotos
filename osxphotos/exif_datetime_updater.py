"""Use exiftool to update exif data in photos """

from __future__ import annotations

import datetime
from typing import Callable, Optional, Tuple

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
from .exifutils import ExifDateTime, get_exif_date_time_offset
from .photodates import update_photo_date_time
from .photosdb import PhotosDB
from .platform import assert_macos
from .utils import noop

assert_macos()

from .phototz import PhotoTimeZone, PhotoTimeZoneUpdater
from .timezones import Timezone, format_offset_time

__all__ = ["ExifDateTimeUpdater"]


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

        if dtinfo.offset_seconds is not None:
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
                new_datetime = datetime_remove_tz(dtinfo.datetime)
                # local_datetime = datetime_remove_tz(
                #     datetime_utc_to_local(datetime_tz_to_utc(dtinfo.datetime))
                # )
            else:
                new_datetime = dtinfo.datetime
            #     local_datetime = dtinfo.datetime
            # update date/time
            # photo.date = local_datetime
            update_photo_date_time(
                self.library_path,
                photo,
                new_datetime.date(),
                new_datetime.time(),
                None,
                None,
                self.verbose,
            )
            # self.verbose(
            #     "Updated date/time for photo "
            #     f"[filename]{photo.filename}[/filename] ([uuid]{photo.uuid}[/uuid]): [time]{local_datetime}[/time]"
            # )

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
