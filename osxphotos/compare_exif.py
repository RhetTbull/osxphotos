""" PhotoCompare class to compare date/time/timezone in Photos to the exif data """

from collections import namedtuple
from typing import Callable, List, Optional, Tuple

from osxphotos import PhotosDB
from osxphotos.exiftool import ExifTool

from .datetime_utils import datetime_naive_to_local, datetime_to_new_tz
from .platform import assert_macos
from .utils import noop

assert_macos()

from photoscript import Photo

from .exifutils import get_exif_date_time_offset
from .phototz import PhotoTimeZone

ExifDiff = namedtuple(
    "ExifDiff",
    [
        "diff",
        "photos_date",
        "photos_time",
        "photos_tz",
        "exif_date",
        "exif_time",
        "exif_tz",
    ],
)


def change(msg: str) -> str:
    """Add change tag to string"""
    return f"[change]{msg}[/change]"


def no_change(msg: str) -> str:
    """Add no change tag to string"""
    return f"[no_change]{msg}[/no_change]"


class PhotoCompare:
    """Class to compare date/time/timezone in Photos to the exif data"""

    def __init__(
        self,
        library_path: Optional[str] = None,
        verbose: Optional[Callable] = None,
        exiftool_path: Optional[str] = None,
    ):
        self.library_path = library_path
        self.db = PhotosDB(self.library_path)
        self.verbose = verbose or noop
        self.exiftool_path = exiftool_path
        self.phototz = PhotoTimeZone(self.library_path)

    def compare_exif(self, photo: Photo) -> List[str]:
        """Compare date/time/timezone in Photos to the exif data

        Args:
            photo (Photo): Photo object to compare

        Returns:
            List of strings:
        """
        photos_offset_seconds, photos_tz_str, _ = self.phototz.get_timezone(photo)
        photos_date = datetime_naive_to_local(photo.date)
        photos_date = datetime_to_new_tz(photos_date, photos_offset_seconds)
        photos_date_str = photos_date.strftime("%Y-%m-%d %H:%M:%S")

        photo_ = self.db.get_photo(photo.uuid)
        if photo_path := photo_.path:
            exif = ExifTool(filepath=photo_path, exiftool=self.exiftool_path)
            exif_dict = exif.asdict()
            exif_dt_offset = get_exif_date_time_offset(exif_dict)
            exif_offset = exif_dt_offset.offset_str
            exif_date = (
                exif_dt_offset.datetime.strftime("%Y-%m-%d %H:%M:%S")
                if exif_dt_offset.datetime
                else ""
            )
        else:
            exif_date = ""
            exif_offset = ""

        return [photos_date_str, photos_tz_str, exif_date, exif_offset]

    def timewarp_compare_exif(self, photo: Photo, plain: bool = False) -> ExifDiff:
        """Compare date/time/timezone in Photos to the exif data and return an ExifDiff named tuple;
        optionally adds rich markup to strings to show differences.

        Args:
            photo (Photo): Photo object to compare
            plain (bool): Flag to determine if plain (True) or markup (False) should be applied
        """

        def compare_values(photo_value: str, exif_value: str) -> tuple:
            """Compare two values and return them with or without markup.

            Affects nonlocal variable diff (from timewarp_compare_exif) with result.
            """

            nonlocal diff
            if photo_value != exif_value:
                diff = True
                if not plain:
                    return change(photo_value), change(exif_value)
            else:
                if not plain:
                    return no_change(photo_value), no_change(exif_value)
            return photo_value, exif_value

        # Get values from comparison function
        photos_date, photos_tz, exif_date, exif_tz = self.compare_exif(photo)
        diff = False

        # Split date and time
        photos_date, photos_time = photos_date.split(" ", 1)
        try:
            exif_date, exif_time = exif_date.split(" ", 1)
        except ValueError:
            exif_time = ""  # Handle missing time in exif_date

        # Compare dates, times, and timezones
        photos_date, exif_date = compare_values(photos_date, exif_date)
        photos_time, exif_time = compare_values(photos_time, exif_time)
        photos_tz, exif_tz = compare_values(photos_tz, exif_tz)

        return ExifDiff(
            diff,
            photos_date,
            photos_time,
            photos_tz,
            exif_date,
            exif_time,
            exif_tz,
        )
