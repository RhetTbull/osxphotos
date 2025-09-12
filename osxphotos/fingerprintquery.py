"""Query Photos database for photos matching fingerprint """

from __future__ import annotations

import datetime
import os
import pathlib
import sqlite3

from ._constants import _DB_TABLE_NAMES
from .fingerprint import fingerprint
from .photos_datetime import photos_datetime
from .photosdb.photosdb_utils import get_photos_version_from_model


class FingerprintQuery:
    """Class to query Photos database for photos matching fingerprint"""

    def __init__(self, photos_library: str | pathlib.Path):
        """Create a new FingerprintQuery object

        Args:
            photos_library: path to Photos library
        """
        self.photos_library = (
            pathlib.Path(photos_library)
            if not isinstance(photos_library, pathlib.Path)
            else photos_library
        )
        if self.photos_library.is_dir():
            # assume path to root of Photos library
            # if not, assume it's the path to the Photos.sqlite file
            self.photos_library = self.photos_library / "database" / "Photos.sqlite"
        self.conn = sqlite3.connect(str(self.photos_library))
        self.photos_version = get_photos_version_from_model(str(self.photos_library))

    def photos_by_fingerprint(
        self, fingerprint: str, in_trash: bool = False
    ) -> list[tuple[str, datetime.datetime, str]]:
        """Return a list of tuples of (uuid, date_added, filename) for all photos matching fingerprint"""

        asset_table = _DB_TABLE_NAMES[self.photos_version]["ASSET"]
        fingerprint_column = _DB_TABLE_NAMES[self.photos_version]["MASTER_FINGERPRINT"]

        sql = f"""
            SELECT
            {asset_table}.ZUUID,
            {asset_table}.ZADDEDDATE,
            ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET,
            ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME
            FROM {asset_table}
            JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK
            WHERE {fingerprint_column} = ?
            """
        if not in_trash:
            sql += f"\nAND {asset_table}.ZTRASHEDSTATE = 0"

        results = self.conn.execute(sql, (fingerprint,)).fetchall()
        results = [
            (row[0], photos_datetime(row[1], row[2], default=True), row[3])
            for row in results
        ]
        return results

    def photos_by_filename_size(
        self, filename: str, size: int, in_trash: bool = False
    ) -> list[tuple[str, datetime.datetime, str]]:
        """Return a list of tuples of (uuid, date_added, filename) for all photos matching filename and size"""

        asset_table = _DB_TABLE_NAMES[self.photos_version]["ASSET"]
        sql = f"""
            SELECT
            {asset_table}.ZUUID,
            {asset_table}.ZADDEDDATE,
            ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET,
            ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME
            FROM {asset_table}
            JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK
            WHERE ZADDITIONALASSETATTRIBUTES.ZORIGINALFILESIZE = ?
            AND LOWER(ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME) = LOWER(?)
            """

        if not in_trash:
            sql += f"\nAND {asset_table}.ZTRASHEDSTATE = 0"

        results = self.conn.execute(sql, (size, filename)).fetchall()
        results = [
            (row[0], photos_datetime(row[1], row[2], default=True), row[3])
            for row in results
        ]
        return results

    def possible_duplicates(
        self, filepath: str | os.PathLike, in_trash: bool = False
    ) -> list[tuple[str, datetime.datetime, str]]:
        """Return a list of tuples of (uuid, date_added, filename) for all photos that might be duplicates of filepath

        Args:
            filepath: path to file
            in_trash: if True, search for possible duplicates in the Photos trash otherwise exclude photos in the trash

        Returns:
            list of tuples of (uuid, date_added, filename) for all photos that might be duplicates of filepath

        Note: returns empty list if no possible duplicates found
        """
        # first check by fingerprint
        # Photos stores fingerprint for photos but not videos
        filepath = str(filepath)
        if results := self.photos_by_fingerprint(fingerprint(filepath), in_trash):
            return results

        # if not fingerprint matches, could still be a match based on filename/size
        # this is not 100% perfect but close enough to find likely duplicates
        filename = pathlib.Path(filepath).name
        size = pathlib.Path(filepath).stat().st_size
        if results := self.photos_by_filename_size(filename, size, in_trash):
            return results

        return []
