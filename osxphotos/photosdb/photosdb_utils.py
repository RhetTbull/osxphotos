""" utility functions used by PhotosDB """

import logging
import plistlib

from .._constants import (
    _PHOTOS_5_MODEL_VERSION,
    _PHOTOS_6_MODEL_VERSION,
    _PHOTOS_7_MODEL_VERSION,
    _TESTED_DB_VERSIONS,
)
from ..utils import _open_sql_file


def get_db_version(db_file):
    """ Gets the Photos DB version from LiGlobals table

    Args:
        db_file: path to photos.db database file containing LiGlobals table

    Returns: version as str
    """

    version = None

    (conn, c) = _open_sql_file(db_file)

    # get database version
    c.execute("SELECT value from LiGlobals where LiGlobals.keyPath is 'libraryVersion'")
    version = c.fetchone()[0]
    conn.close()

    if version not in _TESTED_DB_VERSIONS:
        print(
            f"WARNING: Only tested on database versions [{', '.join(_TESTED_DB_VERSIONS)}]"
            + f" You have database version={version} which has not been tested"
        )

    return version


def get_model_version(db_file):
    """ Returns the database model version from Z_METADATA
    
    Args:
        db_file: path to Photos.sqlite database file containing Z_METADATA table
        
    Returns: model version as str
    """

    version = None

    (conn, c) = _open_sql_file(db_file)

    # get database version
    c.execute("SELECT MAX(Z_VERSION), Z_PLIST FROM Z_METADATA")
    results = c.fetchone()

    conn.close()

    plist = plistlib.loads(results[1])
    return plist["PLModelVersion"]


def get_db_model_version(db_file):
    """ Returns Photos version based on model version found in db_file
    
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
    else:
        logging.warning(f"Unknown model version: {model_ver}")
        # cross our fingers and try latest version
        return 7
