"""Query Photos database for photos matching fingerprint """

from __future__ import annotations

import pathlib
import sqlite3

from ._constants import _DB_TABLE_NAMES
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

    def photos_by_fingerprint(self, fingerprint: str) -> list[tuple[str, str]]:
        """Return a list of tuples of (uuid, fingerprint) for all photos matching fingerprint"""

        asset_table = _DB_TABLE_NAMES[self.photos_version]["ASSET"]
        sql = f"""
            SELECT {asset_table}.ZUUID, 
            ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME 
            FROM {asset_table}
            JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK
            WHERE ZADDITIONALASSETATTRIBUTES.ZMASTERFINGERPRINT = ?
            """
        return self.conn.execute(sql, (fingerprint,)).fetchall()
