""" Utility functions for working with export_db """


from __future__ import annotations

import contextlib
import datetime
import json
import os
import pathlib
import sqlite3
from typing import Any, Callable, Optional, Tuple, Union

import toml
from rich import print

from osxphotos.photoinfo import PhotoInfo

from ._constants import OSXPHOTOS_EXPORT_DB, SQLITE_CHECK_SAME_THREAD
from ._version import __version__
from .configoptions import ConfigOptions
from .export_db import OSXPHOTOS_EXPORTDB_VERSION, ExportDB
from .fileutil import FileUtil
from .photosdb import PhotosDB
from .utils import hexdigest, noop

__all__ = [
    "export_db_backup",
    "export_db_check_signatures",
    "export_db_get_errors",
    "export_db_get_last_library",
    "export_db_get_last_run",
    "export_db_get_version",
    "export_db_migrate_photos_library",
    "export_db_save_config_to_file",
    "export_db_touch_files",
    "export_db_update_signatures",
    "export_db_vacuum",
    "find_export_db_for_filepath",
    "get_uuid_for_filepath",
]


def isotime_from_ts(ts: int) -> str:
    """Convert timestamp to ISO 8601 time string"""
    return datetime.datetime.fromtimestamp(ts).isoformat()


def export_db_get_version(
    dbfile: Union[str, pathlib.Path]
) -> Tuple[Optional[int], Optional[int]]:
    """returns version from export database as tuple of (osxphotos version, export_db version)"""
    conn = sqlite3.connect(str(dbfile), check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    if row := c.execute(
        "SELECT osxphotos, exportdb FROM version ORDER BY id DESC LIMIT 1;"
    ).fetchone():
        return (row[0], row[1])
    return (None, None)


def export_db_vacuum(dbfile: Union[str, pathlib.Path]) -> None:
    """Vacuum export database"""
    conn = sqlite3.connect(str(dbfile), check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    c.execute("VACUUM;")
    conn.commit()


def export_db_update_signatures(
    dbfile: Union[str, pathlib.Path],
    export_dir: Union[str, pathlib.Path],
    verbose_: Callable = noop,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """Update signatures for all files found in the export database to match what's on disk

    Returns: tuple of (updated, skipped)
    """
    export_dir = pathlib.Path(export_dir)
    fileutil = FileUtil
    conn = sqlite3.connect(str(dbfile), check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    c.execute("SELECT filepath_normalized, filepath FROM export_data;")
    rows = c.fetchall()
    updated = 0
    skipped = 0
    for row in rows:
        filepath_normalized = row[0]
        filepath = row[1]
        filepath = export_dir / filepath
        if not os.path.exists(filepath):
            skipped += 1
            verbose_(
                f"[dark_orange]Skipping missing file[/dark_orange]: '[filepath]{filepath}[/]'"
            )
            continue
        updated += 1
        file_sig = fileutil.file_sig(filepath)
        verbose_(f"[green]Updating signature for[/green]: '[filepath]{filepath}[/]'")
        if not dry_run:
            c.execute(
                "UPDATE export_data SET dest_mode = ?, dest_size = ?, dest_mtime = ? WHERE filepath_normalized = ?;",
                (file_sig[0], file_sig[1], file_sig[2], filepath_normalized),
            )

    if not dry_run:
        conn.commit()

    return (updated, skipped)


def export_db_get_last_run(
    export_db: Union[str, pathlib.Path]
) -> Tuple[Optional[str], Optional[str]]:
    """Get last run from export database"""
    conn = sqlite3.connect(str(export_db), check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    if row := c.execute(
        "SELECT datetime, args FROM runs ORDER BY id DESC LIMIT 1;"
    ).fetchone():
        return row[0], row[1]
    return None, None


def export_db_get_errors(
    export_db: Union[str, pathlib.Path]
) -> Tuple[Optional[str], Optional[str]]:
    """Get errors from export database"""
    conn = sqlite3.connect(str(export_db), check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    results = c.execute(
        "SELECT filepath, uuid, timestamp, error FROM export_data WHERE error is not null ORDER BY timestamp DESC;"
    ).fetchall()
    results = [
        f"[filepath]{row[0]}[/], [uuid]{row[1]}[/], [time]{row[2]}[/], [error]{row[3]}[/]"
        for row in results
    ]
    return results


def export_db_save_config_to_file(
    export_db: Union[str, pathlib.Path], config_file: Union[str, pathlib.Path]
) -> None:
    """Save export_db last run config to file"""
    export_db = pathlib.Path(export_db)
    config_file = pathlib.Path(config_file)
    conn = sqlite3.connect(str(export_db), check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    row = c.execute("SELECT config FROM config ORDER BY id DESC LIMIT 1;").fetchone()
    if not row:
        return ValueError("No config found in export_db")
    with config_file.open("w") as f:
        f.write(row[0])


def export_db_get_config(
    export_db: Union[str, pathlib.Path], config: ConfigOptions, override=False
) -> ConfigOptions:
    """Load last run config to config

    Args:
        export_db: path to export database
        override: if True, any loaded config values will overwrite existing values in config
    """
    conn = sqlite3.connect(str(export_db), check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    row = c.execute("SELECT config FROM config ORDER BY id DESC LIMIT 1;").fetchone()
    return (
        config.load_from_str(row[0], override=override)
        if row
        else ValueError("No config found in export_db")
    )


def export_db_check_signatures(
    dbfile: Union[str, pathlib.Path],
    export_dir: Union[str, pathlib.Path],
    verbose_: Callable = noop,
) -> Tuple[int, int, int]:
    """Check signatures for all files found in the export database to verify what matches the on disk files

    Returns: tuple of (updated, skipped)
    """
    export_dir = pathlib.Path(export_dir)
    fileutil = FileUtil
    conn = sqlite3.connect(str(dbfile), check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    c.execute("SELECT filepath_normalized, filepath FROM export_data;")
    rows = c.fetchall()
    exportdb = ExportDB(dbfile, export_dir)
    matched = 0
    notmatched = 0
    skipped = 0
    for row in rows:
        filepath_normalized = row[0]
        filepath = row[1]
        filepath = export_dir / filepath
        if not filepath.exists():
            skipped += 1
            verbose_(
                f"[dark_orange]Skipping missing file[/dark_orange]: '[filepath]{filepath}[/]'"
            )
            continue
        file_sig = fileutil.file_sig(filepath)
        file_rec = exportdb.get_file_record(filepath)
        if file_rec.dest_sig == file_sig:
            matched += 1
            verbose_(f"[green]Signatures matched[/green]: '[filepath]{filepath}[/]'")
        else:
            notmatched += 1
            verbose_(
                f"[deep_pink3]Signatures do not match[/deep_pink3]: '[filepath]{filepath}[/]'"
            )

    return (matched, notmatched, skipped)


def export_db_touch_files(
    dbfile: Union[str, pathlib.Path],
    export_dir: Union[str, pathlib.Path],
    verbose_: Callable = noop,
    dry_run: bool = False,
) -> Tuple[int, int, int]:
    """Touch files on disk to match the Photos library created date

    Returns: tuple of (touched, not_touched, skipped)
    """
    export_dir = pathlib.Path(export_dir)

    # open and close exportdb to ensure it gets migrated
    exportdb = ExportDB(dbfile, export_dir)
    if upgraded := exportdb.was_upgraded:
        verbose_(
            f"Upgraded export database {dbfile} from version {upgraded[0]} to {upgraded[1]}"
        )
    exportdb.close()

    conn = sqlite3.connect(str(dbfile), check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    if row := c.execute(
        "SELECT config FROM config ORDER BY id DESC LIMIT 1;"
    ).fetchone():
        config = toml.loads(row[0])
        try:
            photos_db_path = config["export"].get("db", None)
        except KeyError:
            photos_db_path = None
    else:
        # TODO: parse the runs table to get the last --db
        # in the mean time, photos_db_path = None will use the default library
        photos_db_path = None

    photosdb = PhotosDB(dbfile=photos_db_path, verbose=verbose_)
    exportdb = ExportDB(dbfile, export_dir)
    c.execute(
        "SELECT filepath_normalized, filepath, uuid, dest_mode, dest_size FROM export_data;"
    )
    rows = c.fetchall()
    touched = 0
    not_touched = 0
    skipped = 0
    for row in rows:
        filepath_normalized = row[0]
        filepath = row[1]
        filepath = export_dir / filepath
        uuid = row[2]
        dest_mode = row[3]
        dest_size = row[4]
        if not filepath.exists():
            skipped += 1
            verbose_(
                f"[dark_orange]Skipping missing file (not in export directory)[/dark_orange]: '[filepath]{filepath}[/]'"
            )
            continue

        photo = photosdb.get_photo(uuid)
        if not photo:
            skipped += 1
            verbose_(
                f"[dark_orange]Skipping missing photo (did not find in Photos Library)[/dark_orange]: '[filepath]{filepath}[/]' ([uuid]{uuid}[/])"
            )
            continue

        ts = int(photo.date.timestamp())
        stat = os.stat(str(filepath))
        mtime = stat.st_mtime
        if mtime == ts:
            not_touched += 1
            verbose_(
                f"[green]Skipping file (timestamp matches)[/green]: '[filepath]{filepath}[/]' [time]{isotime_from_ts(ts)} ({ts})[/time]"
            )
            continue

        touched += 1
        verbose_(
            f"[deep_pink3]Touching file[/deep_pink3]: '[filepath]{filepath}[/]' "
            f"[time]{isotime_from_ts(mtime)} ({mtime}) -> {isotime_from_ts(ts)} ({ts})[/time]"
        )

        if not dry_run:
            os.utime(str(filepath), (ts, ts))
            rec = exportdb.get_file_record(filepath)
            rec.dest_sig = (dest_mode, dest_size, ts)

    return (touched, not_touched, skipped)


def export_db_migrate_photos_library(
    dbfile: Union[str, pathlib.Path],
    photos_library: Union[str, pathlib.Path],
    verbose: Callable = noop,
    dry_run: bool = False,
):
    """
    Migrate export database to new Photos library
    This will attempt to match photos in the new library to photos in the old library
    and update the UUIDs in the export database
    """
    verbose(f"Loading data from export database {dbfile}")
    conn = sqlite3.connect(str(dbfile), check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    results = c.execute("SELECT uuid, photoinfo FROM photoinfo;").fetchall()
    exportdb_uuids = {}
    for row in results:
        uuid = row[0]
        photoinfo = json.loads(row[1])
        exportdb_uuids[uuid] = photoinfo

    verbose(f"Loading data from Photos library {photos_library}")
    photosdb = PhotosDB(dbfile=photos_library, verbose=verbose)
    photosdb_fingerprint = {}
    photosdb_cloud_guid = {}
    photosdb_shared = {}
    for photo in photosdb.photos():
        photosdb_fingerprint[
            f"{photo.original_filename}:{photo.fingerprint}"
        ] = photo.uuid
        photosdb_cloud_guid[
            f"{photo.original_filename}:{photo.cloud_guid}"
        ] = photo.uuid
        if photo.shared:
            photosdb_shared[_shared_photo_key(photo)] = photo.uuid
    verbose("Matching photos in export database to photos in Photos library")
    matched = 0
    notmatched = 0
    for uuid, photoinfo in exportdb_uuids.items():
        if photoinfo.get("shared"):
            key = _shared_photo_key(photoinfo)
            if key in photosdb_shared:
                new_uuid = photosdb_shared[key]
                verbose(
                    f"[green]Matched by shared info[/green]: [uuid]{uuid}[/] -> [uuid]{new_uuid}[/]"
                )
                _export_db_update_uuid_info(
                    conn, uuid, new_uuid, photoinfo, photosdb, dry_run
                )
                matched += 1
                continue
        if cloud_guid := photoinfo.get("cloud_guid", None):
            key = f"{photoinfo['original_filename']}:{cloud_guid}"
            if key in photosdb_cloud_guid:
                new_uuid = photosdb_cloud_guid[key]
                verbose(
                    f"[green]Matched by cloud_guid[/green]: [uuid]{uuid}[/] -> [uuid]{new_uuid}[/]"
                )
                _export_db_update_uuid_info(
                    conn, uuid, new_uuid, photoinfo, photosdb, dry_run
                )
                matched += 1
                continue
        if fingerprint := photoinfo.get("fingerprint", None):
            key = f"{photoinfo['original_filename']}:{fingerprint}"
            if key in photosdb_fingerprint:
                new_uuid = photosdb_fingerprint[key]
                verbose(
                    f"[green]Matched by fingerprint[/green]: [uuid]{uuid}[/] -> [uuid]{new_uuid}[/]"
                )
                _export_db_update_uuid_info(
                    conn, uuid, new_uuid, photoinfo, photosdb, dry_run
                )
                matched += 1
                continue
        else:
            verbose(
                f"[dark_orange]No match found for photo[/dark_orange]: [uuid]{uuid}[/], [filename]{photoinfo.get('original_filename')}[/]"
            )
            notmatched += 1

    if not dry_run:
        conn.execute("VACUUM;")
    conn.close()
    return (matched, notmatched)


def _shared_photo_key(photo: PhotoInfo | dict[str, Any]) -> str:
    """return a key for matching a shared photo between libraries"""
    photoinfo = photo.asdict() if isinstance(photo, PhotoInfo) else photo
    date = photoinfo.get("date")
    if isinstance(date, datetime.datetime):
        date = date.isoformat()
    return (
        f"{photoinfo.get('cloud_owner_hashed_id')}:"
        f"{photoinfo.get('original_height')}:"
        f"{photoinfo.get('original_width')}:"
        f"{photoinfo.get('isphoto')}:"
        f"{photoinfo.get('ismovie')}:"
        f"{date}"
    )


def _export_db_update_uuid_info(
    conn: sqlite3.Connection,
    uuid: str,
    new_uuid: str,
    photoinfo: dict[str, Any],
    photosdb: PhotosDB,
    dry_run: bool = False,
):
    """
    Update the UUID and digest in the export database to match a new UUID

    Args:
        conn (sqlite3.Connection): connection to export database
        uuid (str): old UUID
        new_uuid (str): new UUID
        photoinfo (dict): photoinfo for old UUID
        photosdb (PhotosDB): PhotosDB instance for new library
        dry_run (bool): if True, don't update the database
    """
    if dry_run:
        return
    new_digest = compute_photoinfo_digest(photoinfo, photosdb.get_photo(new_uuid))
    export_db_update_uuid(conn, uuid, new_uuid)
    export_db_update_digest_for_uuid(conn, new_uuid, new_digest)


def export_db_update_uuid(
    conn: sqlite3.Connection, uuid: str, new_uuid: str
) -> Tuple[bool, str]:
    """Update the UUID in the export database

    Args:
        conn (sqlite3.Connection): connection to export database
        uuid (str): old UUID
        new_uuid (str): new UUID

    Returns:
        (bool, str): (success, error)
    """
    c = conn.cursor()
    try:
        c.execute(
            "UPDATE photoinfo SET uuid=? WHERE uuid=?;",
            (new_uuid, uuid),
        )
        c.execute(
            "UPDATE export_data SET uuid=? WHERE uuid=?;",
            (new_uuid, uuid),
        )
        conn.commit()
        return (True, "")
    except Exception as e:
        return (False, str(e))


def export_db_backup(dbpath: Union[str, pathlib.Path]) -> str:
    """Backup export database, returns name of backup file"""
    dbpath = pathlib.Path(dbpath)
    # create backup with .bak extension and datestamp in YYYYMMDDHHMMSS format
    source_file = dbpath.parent / dbpath.name
    datestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    # first try to copy .db-shm and .db-wal files if they exist
    for suffix in (".db-shm", ".db-wal"):
        backup_file = f"{source_file.with_suffix(suffix)}.{datestamp}.bak"
        with contextlib.suppress(FileNotFoundError):
            FileUtil.copy(source_file, backup_file)
    backup_file = f"{source_file}.{datestamp}.bak"
    FileUtil.copy(source_file, backup_file)
    return backup_file


def export_db_get_last_library(dbpath: Union[str, pathlib.Path]) -> str:
    """Return the last library used to export from

    This isn't stored separately in the database but can be extracted from the
    stored JSON in the photoinfo table. Use the most recent export_data entry
    to get the UUID of the last exported photo and then use that to get the
    library name from the photoinfo table.

    Args:
        dbpath (Union[str, pathlib.Path]): path to export database

    Returns:
        str: name of library used to export from or "" if not found
    """
    dbpath = pathlib.Path(dbpath)
    conn = sqlite3.connect(str(dbpath), check_same_thread=SQLITE_CHECK_SAME_THREAD)
    c = conn.cursor()
    if results := c.execute(
        """
            SELECT json_extract(photoinfo.photoinfo, '$.library')
            FROM photoinfo
            WHERE photoinfo.uuid = (
                SELECT export_data.uuid 
                FROM export_data 
                WHERE export_data.timestamp = (
                    SELECT MAX(export_data.timestamp) 
                    FROM export_data))
    """
    ).fetchone():
        return results[0]
    return ""


def export_db_update_digest_for_uuid(
    conn: sqlite3.Connection, uuid: str, digest: str
) -> None:
    """Update the export_data.digest column for the given UUID"""
    c = conn.cursor()
    c.execute(
        "UPDATE export_data SET digest=? WHERE uuid=?;",
        (digest, uuid),
    )
    conn.commit()


def compute_photoinfo_digest(photoinfo: dict[str, Any], photo: PhotoInfo) -> str:
    """Compute a new digest for a photoinfo dictionary using the UUID and library from photo

    Args:
        photoinfo (dict[str, Any]): photoinfo dictionary
        photo (PhotoInfo): PhotoInfo object for the new photo

    Returns:
        str: new digest
    """
    new_dict = photoinfo.copy()
    new_dict["uuid"] = photo.uuid
    new_dict["library"] = photo._db._library_path
    return hexdigest(json.dumps(new_dict, sort_keys=True))


def find_export_db_for_filepath(filepath: Union[str, pathlib.Path]) -> str:
    """Walk up a directory tree looking for an export database

    Args:
        filepath (Union[str, pathlib.Path]): path to file or directory

    Returns:
        str: path to export database or "" if not found
    """
    filepath = pathlib.Path(filepath)

    if filepath.is_dir():
        return find_export_db_for_filepath(filepath / OSXPHOTOS_EXPORT_DB)

    for root in filepath.parents:
        filenames = root.glob("*")
        for fname in filenames:
            if fname.is_file() and fname.name == OSXPHOTOS_EXPORT_DB:
                return str(fname)
    return ""


def get_uuid_for_filepath(filepath: Union[str, pathlib.Path]) -> str:
    """Find the UUID for a given filepath, traversing the directory tree to find the export database.

    Args:
        filepath (Union[str, pathlib.Path]): path to file or directory

    Returns:
        str: UUID for file or "" if not found
    """
    filepath = pathlib.Path(filepath)
    if export_db_path := find_export_db_for_filepath(filepath):
        export_root = pathlib.Path(export_db_path).parent
        exportdb = ExportDB(export_db_path, export_root)
        return record.uuid if (record := exportdb.get_file_record(filepath)) else ""
    return ""
