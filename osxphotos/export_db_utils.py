""" Utility functions for working with export_db """


import datetime
import os
import pathlib
import sqlite3
from typing import Callable, Optional, Tuple, Union

import toml
from rich import print

from ._constants import OSXPHOTOS_EXPORT_DB
from ._version import __version__
from .configoptions import ConfigOptions
from .export_db import OSXPHOTOS_EXPORTDB_VERSION, ExportDB
from .fileutil import FileUtil
from .photosdb import PhotosDB
from .utils import noop

__all__ = [
    "export_db_check_signatures",
    "export_db_get_last_run",
    "export_db_get_version",
    "export_db_save_config_to_file",
    "export_db_touch_files",
    "export_db_update_signatures",
    "export_db_vacuum",
]


def isotime_from_ts(ts: int) -> str:
    """Convert timestamp to ISO 8601 time string"""
    return datetime.datetime.fromtimestamp(ts).isoformat()


def export_db_get_version(
    dbfile: Union[str, pathlib.Path]
) -> Tuple[Optional[int], Optional[int]]:
    """returns version from export database as tuple of (osxphotos version, export_db version)"""
    conn = sqlite3.connect(str(dbfile))
    c = conn.cursor()
    row = c.execute(
        "SELECT osxphotos, exportdb FROM version ORDER BY id DESC LIMIT 1;"
    ).fetchone()
    if row:
        return (row[0], row[1])
    return (None, None)


def export_db_vacuum(dbfile: Union[str, pathlib.Path]) -> None:
    """Vacuum export database"""
    conn = sqlite3.connect(str(dbfile))
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
    conn = sqlite3.connect(str(dbfile))
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
            verbose_(f"[dark_orange]Skipping missing file[/dark_orange]: '{filepath}'")
            continue
        updated += 1
        file_sig = fileutil.file_sig(filepath)
        verbose_(f"[green]Updating signature for[/green]: '{filepath}'")
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
    conn = sqlite3.connect(str(export_db))
    c = conn.cursor()
    row = c.execute(
        "SELECT datetime, args FROM runs ORDER BY id DESC LIMIT 1;"
    ).fetchone()
    if row:
        return row[0], row[1]
    return None, None


def export_db_save_config_to_file(
    export_db: Union[str, pathlib.Path], config_file: Union[str, pathlib.Path]
) -> None:
    """Save export_db last run config to file"""
    export_db = pathlib.Path(export_db)
    config_file = pathlib.Path(config_file)
    conn = sqlite3.connect(str(export_db))
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
    conn = sqlite3.connect(str(export_db))
    c = conn.cursor()
    row = c.execute("SELECT config FROM config ORDER BY id DESC LIMIT 1;").fetchone()
    if not row:
        return ValueError("No config found in export_db")
    return config.load_from_str(row[0], override=override)


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
    conn = sqlite3.connect(str(dbfile))
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
            verbose_(f"[dark_orange]Skipping missing file[/dark_orange]: '{filepath}'")
            continue
        file_sig = fileutil.file_sig(filepath)
        file_rec = exportdb.get_file_record(filepath)
        if file_rec.dest_sig == file_sig:
            matched += 1
            verbose_(f"[green]Signatures matched[/green]: '{filepath}'")
        else:
            notmatched += 1
            verbose_(f"[deep_pink3]Signatures do not match[/deep_pink3]: '{filepath}'")

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
    upgraded = exportdb.was_upgraded
    if upgraded:
        verbose_(
            f"Upgraded export database {dbfile} from version {upgraded[0]} to {upgraded[1]}"
        )
    exportdb.close()

    conn = sqlite3.connect(str(dbfile))
    c = conn.cursor()
    # get most recent config
    row = c.execute("SELECT config FROM config ORDER BY id DESC LIMIT 1;").fetchone()
    if row:
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
                f"[dark_orange]Skipping missing file (not in export directory)[/dark_orange]: '{filepath}'"
            )
            continue

        photo = photosdb.get_photo(uuid)
        if not photo:
            skipped += 1
            verbose_(
                f"[dark_orange]Skipping missing photo (did not find in Photos Library)[/dark_orange]: '{filepath}' ({uuid})"
            )
            continue

        ts = int(photo.date.timestamp())
        stat = os.stat(str(filepath))
        mtime = stat.st_mtime
        if mtime == ts:
            not_touched += 1
            verbose_(
                f"[green]Skipping file (timestamp matches)[/green]: '{filepath}' [dodger_blue1]{isotime_from_ts(ts)} ({ts})[/dodger_blue1]"
            )
            continue

        touched += 1
        verbose_(
            f"[deep_pink3]Touching file[/deep_pink3]: '{filepath}' "
            f"[dodger_blue1]{isotime_from_ts(mtime)} ({mtime}) -> {isotime_from_ts(ts)} ({ts})[/dodger_blue1]"
        )

        if not dry_run:
            os.utime(str(filepath), (ts, ts))
            rec = exportdb.get_file_record(filepath)
            rec.dest_sig = (dest_mode, dest_size, ts)

    return (touched, not_touched, skipped)
