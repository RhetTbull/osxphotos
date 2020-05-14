""" PhotosDB method for processing exif info 
    Do not import this module directly """

import logging

from .._constants import _PHOTOS_4_VERSION
from ..utils import _db_is_locked, _debug, _open_sql_file


def _process_exifinfo(self):
    """ load the exif data from the database 
        this is a PhotosDB method that should be imported in 
        the PhotosDB class definition in photosdb.py
    """
    if self._db_version <= _PHOTOS_4_VERSION:
        _process_exifinfo_4(self)
    else:
        _process_exifinfo_5(self)


# The following methods do not get imported into PhotosDB
# but will get called by _process_exifinfo


def _process_exifinfo_4(photosdb):
    """ process exif info for Photos <= 4 
        photosdb: PhotosDB instance """
    photosdb._db_exifinfo_uuid = {}
    raise NotImplementedError(f"search info not implemented for this database version")


def _process_exifinfo_5(photosdb):
    """ process exif info for Photos >= 5 
        photosdb: PhotosDB instance """

    db = photosdb._tmp_db
    
    (conn, cursor) = _open_sql_file(db)

    result = conn.execute(
        """
        SELECT ZGENERICASSET.ZUUID, ZEXTENDEDATTRIBUTES.*
        FROM ZGENERICASSET
        JOIN ZEXTENDEDATTRIBUTES
        ON ZEXTENDEDATTRIBUTES.ZASSET = ZGENERICASSET.Z_PK
        """
    )

    photosdb._db_exifinfo_uuid = {}
    cols = [c[0] for c in result.description]
    for row in result.fetchall():
        record = dict(zip(cols, row))
        uuid = record["ZUUID"]
        if uuid in photosdb._db_exifinfo_uuid:
            logging.warning(f"duplicate exifinfo record found for uuid {uuid}")
        photosdb._db_exifinfo_uuid[uuid] = record
