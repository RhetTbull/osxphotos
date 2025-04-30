""" utility functions used by PhotosDB """

from __future__ import annotations

import logging
import pathlib
import plistlib
import sys

from .._constants import (
    _PHOTOS_2_VERSION,
    _PHOTOS_3_VERSION,
    _PHOTOS_4_VERSION,
    _PHOTOS_5_MODEL_VERSION,
    _PHOTOS_5_VERSION,
    _PHOTOS_6_MODEL_VERSION,
    _PHOTOS_7_MODEL_VERSION,
    _PHOTOS_8_MODEL_VERSION,
    _PHOTOS_9_14_6_MODEL_VERSION,
    _PHOTOS_9_MODEL_VERSION,
    _PHOTOS_10_MODEL_VERSION,
    _PHOTOS_10B1_MODEL_VERSION,
    _TESTED_DB_VERSIONS,
)
from ..sqlite_utils import sqlite_open_ro

logger = logging.getLogger("osxphotos")

__all__ = [
    "get_db_version",
    "get_model_version",
    "get_photos_version_from_model",
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
            + f" You have database version={version} which has not been tested",
            file=sys.stderr,
        )

    return version


def get_model_version(db_file: str) -> str | None:
    """Returns the database model version from Z_METADATA

    Args:
        db_file: path to Photos.sqlite database file containing Z_METADATA table

    Returns: model version as str or None if model version not found
    """

    (conn, c) = sqlite_open_ro(db_file)

    # get database version
    try:
        c.execute("SELECT MAX(Z_VERSION), Z_PLIST FROM Z_METADATA")
        results = c.fetchone()
    except Exception as e:
        logger.warning(f"Error getting model version: {e}")
        return None

    conn.close()

    if not results or results[0] is None:
        logger.warning(f"Error getting model version; no results from query")
        return None

    try:
        plist = plistlib.loads(results[1])
        return plist["PLModelVersion"]
    except KeyError:
        logger.warning(f"Error getting model version: {results}")
        return None


def get_photos_version_from_model(db_file: str) -> int:
    """Returns Photos version based on model version found in db_file

    Args:
        db_file: path to Photos.sqlite file

    Returns: int of major Photos version number (e.g. 5 or 6).
    If unknown model version found, logs warning and returns most current Photos version.
    """

    model_ver = get_model_version(db_file)
    if model_ver is None:
        logger.warning(
            f"Could not determine model version for {db_file}; assuming latest version"
        )
        return 9
    model_ver = int(model_ver)
    if _PHOTOS_5_MODEL_VERSION[0] <= model_ver <= _PHOTOS_5_MODEL_VERSION[1]:
        return 5
    if _PHOTOS_6_MODEL_VERSION[0] <= model_ver <= _PHOTOS_6_MODEL_VERSION[1]:
        return 6
    if _PHOTOS_7_MODEL_VERSION[0] <= model_ver <= _PHOTOS_7_MODEL_VERSION[1]:
        return 7
    if _PHOTOS_8_MODEL_VERSION[0] <= model_ver <= _PHOTOS_8_MODEL_VERSION[1]:
        return 8
    if _PHOTOS_9_MODEL_VERSION[0] <= model_ver <= _PHOTOS_9_MODEL_VERSION[1]:
        return 9
    if _PHOTOS_9_14_6_MODEL_VERSION[0] <= model_ver <= _PHOTOS_9_14_6_MODEL_VERSION[1]:
        return 9.6
    if _PHOTOS_10B1_MODEL_VERSION[0] <= model_ver <= _PHOTOS_10B1_MODEL_VERSION[1]:
        return 9.9
    if _PHOTOS_10_MODEL_VERSION[0] <= model_ver <= _PHOTOS_10_MODEL_VERSION[1]:
        return 10
    logger.warning(
        f"Unknown db / model version for {db_file}: model_ver={model_ver}; assuming latest version"
    )
    return 10


def get_photos_library_version(library_path: str | pathlib.Path) -> int:
    """Return int indicating which Photos version a library was created with

    Args:
        library_path: path to Photos library; may be path to the root of the library or the photos.db file

    Returns: int of major Photos version number (e.g. 5, 6, ...)
    """
    library_path = pathlib.Path(library_path)
    if library_path.is_dir():
        library_path = library_path / "database" / "photos.db"
    db_ver = int(get_db_version(str(library_path)))
    if db_ver == int(_PHOTOS_2_VERSION):
        return 2
    if db_ver == int(_PHOTOS_3_VERSION):
        return 3
    if db_ver == int(_PHOTOS_4_VERSION):
        return 4

    # assume it's a Photos 5+ library, get the model version to determine which version
    library_path = library_path.parent / "Photos.sqlite"
    return get_photos_version_from_model(str(library_path))


def get_db_path_for_library(photos_library: str | pathlib.Path) -> pathlib.Path:
    """Returns path to Photos database file for Photos library

    Args:
        photos_library: path to Photos library; may be path to the root of the library or the photos.db file

    Returns: pathlib.Path to Photos database file
    """
    photos_library = pathlib.Path(photos_library)
    if photos_library.is_file():
        return photos_library
    photos_version = get_photos_library_version(photos_library)
    if photos_version < 5:
        if photos_library.is_dir():
            photos_library = photos_library / "database" / "photos.db"
    elif photos_library.is_dir():
        photos_library = photos_library / "database" / "Photos.sqlite"
    return photos_library
