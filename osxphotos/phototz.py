""" Update the timezone of a photo in Apple Photos' library """
# WARNING: This is a hack.  It might destroy your Photos library.
# Ensure you have a backup before using!
# You have been warned.

import datetime
import pathlib
import sqlite3
from typing import Callable, Optional, Tuple

from photoscript import Photo
from tenacity import retry, stop_after_attempt, wait_exponential

from ._constants import _DB_TABLE_NAMES, SQLITE_CHECK_SAME_THREAD
from .photosdb.photosdb_utils import get_photos_library_version
from .timezones import Timezone
from .utils import get_last_library_path, get_system_library_path, noop


def tz_to_str(tz_seconds: int) -> str:
    """convert timezone offset in seconds to string in form +00:00 (as offset from GMT)"""
    sign = "+" if tz_seconds >= 0 else "-"
    tz_seconds = abs(tz_seconds)
    # get min and seconds first
    mm, _ = divmod(tz_seconds, 60)
    # Get hours
    hh, mm = divmod(mm, 60)
    return f"{sign}{hh:02}{mm:02}"


class PhotoTimeZone:
    """Get timezone info for photos"""

    def __init__(
        self,
        library_path: Optional[str] = None,
    ):
        # get_last_library_path() returns the path to the last Photos library
        # opened but sometimes (rarely) fails on some systems
        try:
            db_path = (
                library_path or get_last_library_path() or get_system_library_path()
            )
        except Exception:
            db_path = None
        if not db_path:
            raise FileNotFoundError("Could not find Photos database path")

        photos_version = get_photos_library_version(db_path)
        db_path = str(pathlib.Path(db_path) / "database/Photos.sqlite")
        self.db_path = db_path
        self.ASSET_TABLE = _DB_TABLE_NAMES[photos_version]["ASSET"]

    @retry(
        wait=wait_exponential(multiplier=1, min=0.100, max=5),
        stop=stop_after_attempt(10),
    )
    def get_timezone(self, photo: Photo) -> Tuple[int, str, str]:
        """Return (timezone_seconds, timezone_str, timezone_name) of photo"""
        # Use retry decorator to retry if database is locked
        uuid = photo.uuid
        sql = f"""  SELECT 
                    ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET, 
                    ZADDITIONALASSETATTRIBUTES.ZTIMEZONENAME
                    FROM ZADDITIONALASSETATTRIBUTES
                    JOIN {self.ASSET_TABLE} 
                    ON ZADDITIONALASSETATTRIBUTES.ZASSET = {self.ASSET_TABLE}.Z_PK
                    WHERE {self.ASSET_TABLE}.ZUUID = '{uuid}' 
            """
        with sqlite3.connect(
            self.db_path, check_same_thread=SQLITE_CHECK_SAME_THREAD
        ) as conn:
            c = conn.cursor()
            c.execute(sql)
            results = c.fetchone()
        tz, tzname = (results[0], results[1])
        tz = tz or 0  # it's possible for tz to be None, #976
        tz_str = tz_to_str(tz)
        return tz, tz_str, tzname


class PhotoTimeZoneUpdater:
    """Update timezones for Photos objects"""

    def __init__(
        self,
        timezone: Timezone,
        verbose: Optional[Callable] = None,
        library_path: Optional[str] = None,
    ):
        self.timezone = timezone
        self.tz_offset = timezone.offset
        self.tz_name = timezone.name

        self.verbose = verbose or noop

        # get_last_library_path() returns the path to the last Photos library
        # opened but sometimes (rarely) fails on some systems
        try:
            db_path = (
                library_path or get_last_library_path() or get_system_library_path()
            )
        except Exception:
            db_path = None
        if not db_path:
            raise FileNotFoundError("Could not find Photos database path")

        photos_version = get_photos_library_version(db_path)
        db_path = str(pathlib.Path(db_path) / "database/Photos.sqlite")
        self.db_path = db_path
        self.ASSET_TABLE = _DB_TABLE_NAMES[photos_version]["ASSET"]

    def update_photo(self, photo: Photo):
        """Update the timezone of a photo in the database

        Args:
            photo: Photo object to update
        """
        try:
            self._update_photo(photo)
        except Exception as e:
            self.verbose(f"Error updating {photo.uuid}: {e}")

    @retry(
        wait=wait_exponential(multiplier=1, min=0.100, max=5),
        stop=stop_after_attempt(10),
    )
    def _update_photo(self, photo: Photo):
        # Use retry decorator to retry if database is locked
        try:
            uuid = photo.uuid
            sql = f"""  SELECT 
                        ZADDITIONALASSETATTRIBUTES.Z_PK, 
                        ZADDITIONALASSETATTRIBUTES.Z_OPT, 
                        ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET, 
                        ZADDITIONALASSETATTRIBUTES.ZTIMEZONENAME
                        FROM ZADDITIONALASSETATTRIBUTES
                        JOIN {self.ASSET_TABLE} 
                        ON ZADDITIONALASSETATTRIBUTES.ZASSET = {self.ASSET_TABLE}.Z_PK
                        WHERE {self.ASSET_TABLE}.ZUUID = '{uuid}' 
                """
            with sqlite3.connect(
                self.db_path, check_same_thread=SQLITE_CHECK_SAME_THREAD
            ) as conn:
                c = conn.cursor()
                c.execute(sql)
                results = c.fetchone()
            z_opt = results[1] + 1
            z_pk = results[0]
            tz_offset = results[2]
            tz_name = results[3]
            sql_update = f"""   UPDATE ZADDITIONALASSETATTRIBUTES
                                SET Z_OPT={z_opt}, 
                                ZTIMEZONEOFFSET={self.tz_offset}, 
                                ZTIMEZONENAME='{self.tz_name}' 
                                WHERE Z_PK={z_pk};
                        """
            with sqlite3.connect(
                self.db_path, check_same_thread=SQLITE_CHECK_SAME_THREAD
            ) as conn:
                c = conn.cursor()
                c.execute(sql_update)
                conn.commit()

            # now need to update some other property in the photo via Photos API or
            # changes won't be synced to the cloud (#946)
            photo.date = photo.date + datetime.timedelta(seconds=1)
            photo.date = photo.date - datetime.timedelta(seconds=1)

            self.verbose(
                f"Updated timezone for photo [filename]{photo.filename}[/filename] ([uuid]{photo.uuid}[/uuid]) "
                + f"from [tz]{tz_name}[/tz], offset=[tz]{tz_offset}[/tz] "
                + f"to [tz]{self.tz_name}[/tz], offset=[tz]{self.tz_offset}[/tz]"
            )
        except Exception as e:
            raise e
