"""Utilities for creating photoscript objects from a name or UUID"""

from __future__ import annotations

import sqlite3

from .platform import assert_macos

assert_macos()

import photoscript

from ._constants import _DB_TABLE_NAMES, _PHOTOS_5_ALBUM_KIND, _PHOTOS_5_FOLDER_KIND
from .photosdb.photosdb_utils import get_db_path_for_library, get_photos_library_version
from .sqlite_utils import sqlite_open_ro


def casefold(s: str | None) -> str | None:
    return s.casefold() if s else None


def photoscript_object_from_uuid(
    uuid: str, photos_database: str
) -> photoscript.Photo | None:
    """Return a photoscript object from a uuid"""
    photos_database = get_db_path_for_library(photos_database)
    photos_version = get_photos_library_version(photos_database)
    connection, cursor = sqlite_open_ro(photos_database)
    uuid = uuid.upper()
    if _uuid_is_asset(uuid, connection, photos_version):
        return photoscript.Photo(uuid)
    elif _uuid_is_album(uuid, connection, photos_version):
        return photoscript.Album(uuid)
    elif _uuid_is_folder(uuid, connection, photos_version):
        return photoscript.Folder(uuid)
    else:
        return None


def photoscript_object_from_name(
    name: str, photos_database: str
) -> photoscript.Photo | None:
    """Return a photoscript object from a name"""
    photos_database = get_db_path_for_library(photos_database)
    photos_version = get_photos_library_version(photos_database)
    connection, cursor = sqlite_open_ro(photos_database)
    connection.create_function("CASEFOLD", 1, casefold)
    if uuid := _asset_uuid_for_name(name, connection, photos_version):
        return photoscript.Photo(uuid)
    elif uuid := _album_uuid_for_name(name, connection, photos_version):
        return photoscript.Album(uuid)
    elif uuid := _folder_uuid_for_name(name, connection, photos_version):
        return photoscript.Folder(uuid)
    else:
        return None


def _uuid_is_asset(
    uuid: str, connection: sqlite3.Connection, version: int
) -> str | None:
    """Return uuid if uuid is an asset uuid otherwise None"""
    asset_table = _DB_TABLE_NAMES[version]["ASSET"]
    cursor = connection.cursor()
    if results := cursor.execute(
        f"""
        SELECT ZUUID
        FROM {asset_table}
        WHERE ZUUID=?
        """,
        (uuid,),
    ).fetchone():
        return results[0]
    else:
        return None


def _uuid_is_album(
    uuid: str, connection: sqlite3.Connection, version: int
) -> str | None:
    """Return uuid if uuid is an album uuid otherwise None"""
    cursor = connection.cursor()
    if results := cursor.execute(
        """
        SELECT ZUUID
        FROM ZGENERICALBUM
        WHERE ZUUID=?
        AND ZKIND=?
        """,
        (uuid, _PHOTOS_5_ALBUM_KIND),
    ).fetchone():
        return results[0]
    else:
        return None


def _uuid_is_folder(
    uuid: str, connection: sqlite3.Connection, version: int
) -> str | None:
    """Return uuid if uuid is an folder uuid otherwise None"""
    cursor = connection.cursor()
    if results := cursor.execute(
        """
        SELECT ZUUID
        FROM ZGENERICALBUM
        WHERE ZUUID=?
        AND ZKIND=?
        """,
        (uuid, _PHOTOS_5_FOLDER_KIND),
    ).fetchone():
        return results[0]
    else:
        return None


def _asset_uuid_for_name(
    name: str, connection: sqlite3.Connection, version: int
) -> str | None:
    """Return uuid for asset with name or None if not found"""
    asset_table = _DB_TABLE_NAMES[version]["ASSET"]
    cursor = connection.cursor()
    if results := cursor.execute(
        f"""
        SELECT {asset_table}.ZUUID
        FROM {asset_table}
        JOIN ZADDITIONALASSETATTRIBUTES ON ZADDITIONALASSETATTRIBUTES.ZASSET = {asset_table}.Z_PK 
        WHERE CASEFOLD(ZADDITIONALASSETATTRIBUTES.ZORIGINALFILENAME)=?
        ORDER BY {asset_table}.ZDATECREATED DESC
        """,
        (casefold(name),),
    ).fetchone():
        return results[0]
    else:
        return None


def _album_uuid_for_name(
    name: str, connection: sqlite3.Connection, version: int
) -> str | None:
    """Return uuid for album with name or None if not found"""
    return _folder_album_uuid_for_name(name, connection, version, album=True)


def _folder_uuid_for_name(
    name: str, connection: sqlite3.Connection, version: int
) -> str | None:
    """Return uuid for album with name or None if not found"""
    return _folder_album_uuid_for_name(name, connection, version, folder=True)


def _folder_album_uuid_for_name(
    name: str,
    connection: sqlite3.Connection,
    version: int,
    album: bool = False,
    folder: bool = False,
) -> str | None:
    """Return uuid for album with name or None if not found"""
    if album and folder:
        raise ValueError("album and folder cannot both be True")
    if not album and not folder:
        raise ValueError("album and folder cannot both be False")
    kind = _PHOTOS_5_ALBUM_KIND if album else _PHOTOS_5_FOLDER_KIND
    cursor = connection.cursor()
    if results := cursor.execute(
        """
        SELECT ZUUID
        FROM ZGENERICALBUM
        WHERE CASEFOLD(ZTITLE)=?
        AND ZKIND=?
        ORDER BY ZCREATIONDATE DESC
        """,
        (casefold(name), kind),
    ).fetchone():
        return results[0]
    else:
        return None
