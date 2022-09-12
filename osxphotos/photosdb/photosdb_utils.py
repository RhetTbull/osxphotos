""" utility functions used by PhotosDB """

import logging
import pathlib
import plistlib

from .._constants import (
    _PHOTOS_2_VERSION,
    _PHOTOS_3_VERSION,
    _PHOTOS_4_VERSION,
    _PHOTOS_5_MODEL_VERSION,
    _PHOTOS_5_VERSION,
    _PHOTOS_6_MODEL_VERSION,
    _PHOTOS_7_MODEL_VERSION,
    _PHOTOS_8_MODEL_VERSION,
    _TESTED_DB_VERSIONS,
)
from ..sqlite_utils import sqlite_open_ro

__all__ = [
    "get_db_version",
    "get_model_version",
    "get_db_model_version",
    "UnknownLibraryVersion",
    "get_photos_library_version",
]


def get_db_version(db_file):
    """Gets the Photos DB version from LiGlobals table

    Args:
        db_file: path to photos.db database file containing LiGlobals table or Photos.sqlite database file

    Returns: version as str
    """

    version = None

    (conn, c) = sqlite_open_ro(db_file)

    # get database version
    result = [
        row[0]
        for row in c.execute(
            "SELECT name FROM sqlite_master WHERE type ='table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
    ]
    if "LiGlobals" in result:
        # it's a photos.db file
        c.execute(
            "SELECT value FROM LiGlobals WHERE LiGlobals.keyPath IS 'libraryVersion'"
        )
        version = c.fetchone()[0]
    elif "Z_METADATA" in result:
        # assume it's a Photos 5+ Photos.sqlite file
        # get_model_version will find the exact version
        version = "5001"
    else:
        raise ValueError(f"Unknown database format: {db_file}")
    conn.close()

    if version not in _TESTED_DB_VERSIONS:
        print(
            f"WARNING: Only tested on database versions [{', '.join(_TESTED_DB_VERSIONS)}]"
            + f" You have database version={version} which has not been tested"
        )

    return version


def get_model_version(db_file):
    """Returns the database model version from Z_METADATA

    Args:
        db_file: path to Photos.sqlite database file containing Z_METADATA table

    Returns: model version as str
    """

    (conn, c) = sqlite_open_ro(db_file)

    # get database version
    c.execute("SELECT MAX(Z_VERSION), Z_PLIST FROM Z_METADATA")
    results = c.fetchone()

    conn.close()

    plist = plistlib.loads(results[1])
    return plist["PLModelVersion"]


def get_db_model_version(db_file):
    """Returns Photos version based on model version found in db_file

    Args:
        db_file: path to Photos.sqlite file

    Returns: int of major Photos version number (e.g. 5 or 6).
    If unknown model version found, logs warning and returns most current Photos version.
    """

    model_ver = get_model_version(db_file)
    if _PHOTOS_5_MODEL_VERSION[0] <= model_ver <= _PHOTOS_5_MODEL_VERSION[1]:
        return 5
    elif _PHOTOS_6_MODEL_VERSION[0] <= model_ver <= _PHOTOS_6_MODEL_VERSION[1]:
        return 6
    elif _PHOTOS_7_MODEL_VERSION[0] <= model_ver <= _PHOTOS_7_MODEL_VERSION[1]:
        return 7
    elif _PHOTOS_8_MODEL_VERSION[0] <= model_ver <= _PHOTOS_8_MODEL_VERSION[1]:
        return 8
    else:
        logging.warning(f"Unknown model version: {model_ver}")
        # cross our fingers and try latest version
        return 8


class UnknownLibraryVersion(Exception):
    pass


def get_photos_library_version(library_path):
    """Return int indicating which Photos version a library was created with"""
    library_path = pathlib.Path(library_path)
    db_ver = get_db_version(str(library_path / "database" / "photos.db"))
    db_ver = int(db_ver)
    if db_ver == int(_PHOTOS_2_VERSION):
        return 2
    if db_ver == int(_PHOTOS_3_VERSION):
        return 3
    if db_ver == int(_PHOTOS_4_VERSION):
        return 4

    # assume it's a Photos 5+ library, get the model version to determine which version
    model_ver = get_model_version(str(library_path / "database" / "Photos.sqlite"))
    model_ver = int(model_ver)
    if _PHOTOS_5_MODEL_VERSION[0] <= model_ver <= _PHOTOS_5_MODEL_VERSION[1]:
        return 5
    if _PHOTOS_6_MODEL_VERSION[0] <= model_ver <= _PHOTOS_6_MODEL_VERSION[1]:
        return 6
    if _PHOTOS_7_MODEL_VERSION[0] <= model_ver <= _PHOTOS_7_MODEL_VERSION[1]:
        return 7
    raise UnknownLibraryVersion(f"db_ver = {db_ver}, model_ver = {model_ver}")
