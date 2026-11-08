"""utility functions used by PhotosDB"""

from __future__ import annotations

import logging
import os
import pathlib
import plistlib
import sqlite3
import sys

from .._constants import (
    _DB_TABLE_NAMES,
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
    _PHOTOS_11_1_MODEL_VERSION,
    _PHOTOS_11_MODEL_VERSION,
    _PHOTOS_12_3_MODEL_VERSION,
    _PHOTOS_12_MODEL_VERSION,
    _TESTED_DB_VERSIONS,
)
from ..fileutil import FileUtil
from ..sqlite_utils import sqlite_open_ro

logger = logging.getLogger("osxphotos")

__all__ = [
    "create_photos1_merged_db",
    "get_db_version",
    "get_model_version",
    "get_photos1_library_root",
    "get_photos_library_version",
    "get_photos_version_from_model",
]

LATEST_PHOTOS_VERSION = max(_DB_TABLE_NAMES.keys())

# Photos 1.x splits library data across several databases in the library's Database folder
# The main database (Library.apdb) plus these auxiliary databases are merged into a single
# temporary database by create_photos1_merged_db so they can be queried together
# metaSchema.db: LiGlobals (library version)
# Person.db: RKPerson, RKFace (persons and faces)
# ImageProxies.apdb: RKModelResource, RKCloudResource (edited images, resources)
# Properties.apdb: RKPlace (places), RKExif*, RKIptc* properties
_PHOTOS_1_MAIN_DB = "Library.apdb"
_PHOTOS_1_META_DB = "metaSchema.db"
_PHOTOS_1_AUX_DBS = [
    "metaSchema.db",
    "Person.db",
    "ImageProxies.apdb",
    "Properties.apdb",
]


def _photos1_db_file(database_dir: pathlib.Path, name: str) -> pathlib.Path | None:
    """Return path to a Photos 1.x database file in database_dir or None if not found

    Photos 1.x stores most of the database files in Database/apdb with symlinks to
    some (but not all) of them in Database/.
    """
    for path in (database_dir / "apdb" / name, database_dir / name):
        if path.is_file():
            return path
    return None


def _photos1_database_dir(library_root: pathlib.Path) -> pathlib.Path | None:
    """Return the Database directory of a Photos 1.x library or None if not a Photos 1.x library"""
    for dirname in ("database", "Database"):
        database_dir = library_root / dirname
        if (database_dir / "photos.db").exists() or (
            database_dir / "Photos.sqlite"
        ).exists():
            # Photos 2+ library
            return None
        if _photos1_db_file(database_dir, _PHOTOS_1_MAIN_DB) and _photos1_db_file(
            database_dir, _PHOTOS_1_META_DB
        ):
            return database_dir
    return None


def get_photos1_library_root(path: str | os.PathLike) -> pathlib.Path | None:
    """Return the root of a Photos 1.x library or None if path is not a Photos 1.x library

    Args:
        path: path to the root of the library or to one of the database files in the library
            (e.g. Database/Library.apdb, Database/apdb/Library.apdb, or Database/metaSchema.db)

    Returns: pathlib.Path to the library root if path is a Photos 1.x library, else None

    Note: iPhoto libraries share the Library.apdb format but do not contain metaSchema.db
    """
    path = pathlib.Path(path)
    if path.is_dir():
        candidates = [path]
    else:
        # Database/Library.apdb or Database/apdb/Library.apdb
        candidates = [path.parent.parent, path.parent.parent.parent]
    for candidate in candidates:
        if _photos1_database_dir(candidate):
            return candidate
    return None


def create_photos1_merged_db(
    library_root: str | os.PathLike, dest_dir: str | os.PathLike
) -> pathlib.Path:
    """Merge the split databases of a Photos 1.x library into a single sqlite database

    Photos 1.x stores library data in several databases (Library.apdb, Person.db, etc.);
    osxphotos expects all data in a single database as in Photos 2-4 (photos.db) so this creates
    a temporary database with all the tables needed by osxphotos.

    Args:
        library_root: path to the root of the Photos 1.x library
        dest_dir: directory in which to create the merged database (e.g. a temporary directory)

    Returns: pathlib.Path to the merged database

    Raises:
        ValueError if library_root is not a Photos 1.x library

    Note: The database files (and their write-ahead logs) are copied to dest_dir before being read
    so the library itself is never opened or modified. Virtual tables, which rely on sqlite modules
    only available to Photos, are not copied.
    """
    library_root = pathlib.Path(library_root)
    dest_dir = pathlib.Path(dest_dir)
    database_dir = _photos1_database_dir(library_root)
    if not database_dir:
        raise ValueError(f"{library_root} is not a Photos 1.x library")

    def _copy_db(name: str, dest_name: str) -> pathlib.Path | None:
        """Copy database name and any -wal/-shm files to dest_dir/dest_name"""
        src = _photos1_db_file(database_dir, name)
        if not src:
            return None
        dest = dest_dir / dest_name
        for suffix in ("", "-wal", "-shm"):
            src_file = pathlib.Path(f"{src}{suffix}")
            if src_file.is_file():
                FileUtil.copy(src_file, f"{dest}{suffix}")
        return dest

    merged_db = _copy_db(_PHOTOS_1_MAIN_DB, "photos1_merged.db")
    conn = sqlite3.connect(merged_db)
    try:
        # checkpoint any write-ahead log into the copy so it is a single self-contained file
        conn.execute("PRAGMA journal_mode=DELETE")
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for name in _PHOTOS_1_AUX_DBS:
            aux_db = _copy_db(name, f"photos1_aux_{name}")
            if not aux_db:
                logger.warning(
                    f"Could not find Photos 1.x database {name} in {database_dir}"
                )
                continue
            _photos1_merge_tables(conn, aux_db, tables)
            for suffix in ("", "-wal", "-shm"):
                pathlib.Path(f"{aux_db}{suffix}").unlink(missing_ok=True)
        conn.commit()
    finally:
        conn.close()
    return merged_db


def _photos1_merge_tables(
    conn: sqlite3.Connection, aux_db: pathlib.Path, tables: set[str]
):
    """Copy all regular tables and their indexes from aux_db into the main database of conn

    Args:
        conn: connection to the destination database
        aux_db: path to the database to copy tables from
        tables: set of table names already in the destination database; updated with copied tables
    """
    conn.execute("ATTACH DATABASE ? AS aux", (str(aux_db),))
    try:
        schema = conn.execute(
            "SELECT type, name, tbl_name, sql FROM aux.sqlite_master"
        ).fetchall()
        virtual_tables = [
            name
            for type_, name, _, sql in schema
            if type_ == "table" and sql and sql.upper().startswith("CREATE VIRTUAL")
        ]
        copied = set()
        for type_, name, _, sql in schema:
            if type_ != "table" or not sql or name.startswith("sqlite_"):
                continue
            if name in virtual_tables or any(
                name.startswith(f"{vtable}_") for vtable in virtual_tables
            ):
                # virtual table or one of its shadow tables
                continue
            if name in tables:
                logger.debug(f"Skipping duplicate table {name} in {aux_db}")
                continue
            conn.execute(sql)
            conn.execute(f'INSERT INTO main."{name}" SELECT * FROM aux."{name}"')
            copied.add(name)
        for type_, _, tbl_name, sql in schema:
            if type_ == "index" and sql and tbl_name in copied:
                conn.execute(sql)
        tables.update(copied)
        conn.commit()
    finally:
        conn.execute("DETACH DATABASE aux")


def get_db_version(db_file: os.PathLike) -> str:
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
    elif "RKVersion" in result and (library_root := get_photos1_library_root(db_file)):
        # Photos 1.x Library.apdb; version is stored in metaSchema.db
        conn.close()
        meta_db = _photos1_db_file(
            _photos1_database_dir(library_root), _PHOTOS_1_META_DB
        )
        return get_db_version(meta_db)
    else:
        conn.close()
        raise ValueError(f"Unknown database format: {db_file}")
    conn.close()

    if version not in _TESTED_DB_VERSIONS:
        logger.warning(
            f"WARNING: OSXPhotos has only been tested on Photos database versions [{', '.join(_TESTED_DB_VERSIONS)}]"
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
        return LATEST_PHOTOS_VERSION
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
    if _PHOTOS_11_MODEL_VERSION[0] <= model_ver <= _PHOTOS_11_MODEL_VERSION[1]:
        return 11
    if _PHOTOS_11_1_MODEL_VERSION[0] <= model_ver <= _PHOTOS_11_1_MODEL_VERSION[1]:
        return 11.1
    if _PHOTOS_12_MODEL_VERSION[0] <= model_ver <= _PHOTOS_12_MODEL_VERSION[1]:
        return 12
    if _PHOTOS_12_3_MODEL_VERSION[0] <= model_ver <= _PHOTOS_12_3_MODEL_VERSION[1]:
        return 12.3
    logger.warning(
        f"Unknown db / model version for {db_file}: model_ver={model_ver}; assuming latest version"
    )
    return LATEST_PHOTOS_VERSION


def get_photos_library_version(library_path: str | pathlib.Path) -> int:
    """Return int indicating which Photos version a library was created with

    Args:
        library_path: path to Photos library; may be path to the root of the library or the photos.db file

    Returns: int of major Photos version number (e.g. 5, 6, ...)
    """
    library_path = pathlib.Path(library_path)
    if get_photos1_library_root(library_path):
        return 1

    if not library_path.is_dir():
        # assume we got passed library path/database/Photos.sqlite or library path/database/photos.db
        library_path = library_path.parent.parent

    db_path = library_path / "database" / "photos.db"
    if db_path.exists():
        try:
            db_ver = int(get_db_version(str(db_path)))
            if db_ver == int(_PHOTOS_2_VERSION):
                return 2
            if db_ver == int(_PHOTOS_3_VERSION):
                return 3
            if db_ver == int(_PHOTOS_4_VERSION):
                return 4
        except Exception:
            pass

    # assume it's a Photos 5+ library, get the model version to determine which version
    db_path = library_path / "database" / "Photos.sqlite"
    if db_path.exists():
        return get_photos_version_from_model(str(db_path))
    else:
        raise ValueError(f"Could not find Photos database at: {library_path}")


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
    if photos_version == 1:
        database_dir = _photos1_database_dir(photos_library)
        return _photos1_db_file(database_dir, _PHOTOS_1_MAIN_DB)
    if photos_version < 5:
        if photos_library.is_dir():
            photos_library = photos_library / "database" / "photos.db"
    elif photos_library.is_dir():
        photos_library = photos_library / "database" / "Photos.sqlite"
    return photos_library


# ZINTERNALRESOURCE.ZCOMPACTUTI (Photos 7+, macOS 12+) holds Apple's PLUniformFileType
# codes, from PhotoLibraryServices.framework:
# +[PLUniformTypeIdentifierIntegratedLookup compactRepresentationForIdentifier:] /
# identifierFromCompactRepresentation:, via PLFileTypeFromIdentifier /
# PLUTTypeFromUniformFileType (table built in populateExtensionFileTypeMappings; read
# from the macOS 27 dyld shared cache). A UTI without a code is stored as "_" + UTI.
# Codes agree with test libraries from macOS 12 to 27. Codes 9 to 22 are the RAW
# types (PLUniformFileTypeIsRawImage); code 2 is unassigned.
COMPACT_UTI_CODES = {
    "1": "public.jpeg",
    "3": "public.heic",
    "4": "public.heif",
    "5": "public.avci",
    "6": "public.png",
    "7": "com.compuserve.gif",
    "8": "public.tiff",
    "9": "com.adobe.raw-image",
    "10": "com.sony.arw-raw-image",
    "11": "com.canon.cr2-raw-image",
    "12": "com.canon.crw-raw-image",
    "13": "com.olympus.raw-image",
    "14": "com.panasonic.rw2-raw-image",
    "15": "com.panasonic.raw-image",
    "16": "com.pentax.raw-image",
    "17": "com.nikon.raw-image",
    "18": "com.samsung.raw-image",
    "19": "com.leafamerica.raw-image",
    "20": "com.hasselblad.3fr-raw-image",
    "21": "com.fuji.raw-image",
    "22": "com.hasselblad.fff-raw-image",
    "23": "com.apple.quicktime-movie",
    "24": "public.mpeg-4",
    "25": "com.apple.m4v-video",
    "26": "public.3gpp",
    "27": "public.avi",
    "28": "com.apple.m4a-audio",
    "29": "com.apple.coreaudio-format",
    "30": "com.microsoft.waveform-audio",
    "31": "public.aifc-audio",
    "32": "public.aiff-audio",
    "33": "public.mp3",
    "34": "public.ac3-audio",
    "35": "com.apple.property-list",
    "36": "public.data",
    "37": "com.apple.photos.apple-adjustment-envelope",
    "38": "public.avif",
    "39": "public.jpeg-xl",
}


def uti_for_compact_uti(compact_uti: str | int | None) -> str | None:
    """Return the UTI for a ZINTERNALRESOURCE.ZCOMPACTUTI value (Photos 7+)

    Returns: the UTI, or None if the value is None or a code not in COMPACT_UTI_CODES
    """
    if compact_uti is None:
        return None
    compact_uti = str(compact_uti)
    if compact_uti.startswith("_"):
        return compact_uti[1:] or None
    return COMPACT_UTI_CODES.get(compact_uti)


def uti_if_raw(uti: str | None) -> str | None:
    """Return uti if it is a RAW image type, else None

    Every RAW type in COMPACT_UTI_CODES (codes 9 to 22) has "raw-image" in its UTI,
    as do the RAW UTIs for file extensions, so this works for codes, "_" + UTI
    values and UTIs from a file's extension alike.
    """
    return uti if uti and "raw-image" in uti else None
