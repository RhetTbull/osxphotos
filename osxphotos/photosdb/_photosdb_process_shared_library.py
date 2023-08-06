""" Methods for PhotosDB to process shared iCloud library data (#860)"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .._constants import _DB_TABLE_NAMES, _PHOTOS_SHARED_LIBRARY_VERSION
from ..sqlite_utils import sqlite_open_ro

if TYPE_CHECKING:
    from osxphotos.photosdb import PhotosDB

logger = logging.getLogger("osxphotos")


def _process_shared_library_info(self: PhotosDB):
    """Process syndication information"""

    if self.photos_version < 7:
        raise NotImplementedError(
            f"syndication info not implemented for this database version: {self.photos_version}"
        )

    if self._model_ver < _PHOTOS_SHARED_LIBRARY_VERSION:
        return

    _process_shared_library_info_8(self)


def _process_shared_library_info_8(photosdb: PhotosDB):
    """Process shared iCloud library info for Photos 8.0 and later

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
        {zasset}.ZACTIVELIBRARYSCOPEPARTICIPATIONSTATE,
        {zasset}.ZLIBRARYSCOPESHARESTATE,
        {zasset}.ZLIBRARYSCOPE
        FROM {zasset}
        """
    )

    for row in result:
        uuid = row[0]
        if uuid not in photosdb._dbphotos:
            logger.debug(f"Skipping shared library info for missing uuid: {uuid}")
            continue
        info = photosdb._dbphotos[uuid]
        info["active_library_participation_state"] = row[1]
        info["library_scope_share_state"] = row[2]
        info["library_scope"] = row[3]
