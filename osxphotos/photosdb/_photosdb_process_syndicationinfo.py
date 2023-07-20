""" Methods for PhotosDB to process Syndication info (#1054) """

from __future__ import annotations

from typing import TYPE_CHECKING

from .._constants import _DB_TABLE_NAMES, _PHOTOS_SYNDICATION_MODEL_VERSION
from ..sqlite_utils import sqlite_open_ro

if TYPE_CHECKING:
    from osxphotos.photosdb import PhotosDB


def _process_syndicationinfo(self: PhotosDB):
    """Process syndication information"""

    self._db_syndication_uuid = {}

    if self.photos_version < 7:
        raise NotImplementedError(
            f"syndication info not implemented for this database version: {self.photos_version}"
        )

    if self._model_ver < _PHOTOS_SYNDICATION_MODEL_VERSION:
        return

    _process_syndicationinfo_7(self)


def _process_syndicationinfo_7(photosdb: PhotosDB):
    """Process Syndication info for Photos 8.0 and later

    Args:
        photosdb: an OSXPhotosDB instance
    """

    db = photosdb._tmp_db
    zasset = _DB_TABLE_NAMES[photosdb._photos_ver]["ASSET"]

    (conn, cursor) = sqlite_open_ro(db)

    result = cursor.execute(
        f""" 
        SELECT
        {zasset}.ZUUID,
        {zasset}.ZSYNDICATIONSTATE,
        ZADDITIONALASSETATTRIBUTES.ZSYNDICATIONHISTORY,
        ZADDITIONALASSETATTRIBUTES.ZSYNDICATIONIDENTIFIER
        FROM {zasset}
        JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {zasset}.Z_PK 
        """
    )

    for row in result:
        uuid = row[0]
        syndication_state = row[1]
        syndication_history = row[2]
        syndication_identifier = row[3]
        photosdb._db_syndication_uuid[uuid] = {
            "syndication_state": syndication_state,
            "syndication_identifier": syndication_identifier,
            "syndication_history": syndication_history,
        }
