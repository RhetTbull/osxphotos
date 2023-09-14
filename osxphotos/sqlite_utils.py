"""sqlite utils for use by osxphotos"""

from __future__ import annotations

import logging
import pathlib
import sqlite3
from typing import List, Tuple

from ._constants import SQLITE_CHECK_SAME_THREAD
from .fileutil import FileUtil, FileUtilMacOS
from .platform import is_macos

logger = logging.getLogger("osxphotos")

__all__ = [
    "sqlite_backup_dbfiles",
    "sqlite_columns",
    "sqlite_db_is_locked",
    "sqlite_delete_backup_files",
    "sqlite_delete_dbfiles",
    "sqlite_open_ro",
    "sqlite_tables",
]


def sqlite_open_ro(dbname: str) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
    """opens sqlite file dbname in read-only mode
    returns tuple of (connection, cursor)"""
    try:
        dbpath = pathlib.Path(dbname).resolve()
        conn = sqlite3.connect(
            f"{dbpath.as_uri()}?mode=ro",
            timeout=1,
            uri=True,
            check_same_thread=SQLITE_CHECK_SAME_THREAD,
        )
        c = conn.cursor()
    except sqlite3.Error as e:
        raise sqlite3.Error(
            f"An error occurred opening sqlite file: {e} {dbname}"
        ) from e
    return (conn, c)


def sqlite_db_is_locked(dbname):
    """check to see if a sqlite3 db is locked
    returns True if database is locked, otherwise False
    dbname: name of database to test"""

    locked = None
    try:
        (conn, c) = sqlite_open_ro(dbname)
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        conn.close()
        locked = False
    except Exception as e:
        logger.debug(f"sqlite_db_is_locked: {e}")
        locked = True

    return locked


def sqlite_tables(conn: sqlite3.Connection) -> List[str]:
    """Returns list of tables found in sqlite db"""
    results = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()
    return [row[0] for row in results]


def sqlite_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    """Returns list of column names found in table in sqlite database"""
    results = conn.execute(f"PRAGMA table_info({table});")
    return [row[1] for row in results]


def sqlite_backup_dbfiles(dbpath: str) -> list[str]:
    """Create a .bak copy of all files associated with a sqlite database

    Args:
        dbpath: path to sqlite database file

    Returns:
        list of files copied

    Note:
        Uses the OS to copy the files, not sqlite3 backup API; database should be closed before calling this function
        If an existing backup file is found, it is overwritten
    """
    fileutil = FileUtilMacOS if is_macos else FileUtil
    backup_files = []
    for suffix in ["", "-wal", "-shm"]:
        src = pathlib.Path(dbpath + suffix)
        if not src.exists():
            continue
        dst = pathlib.Path(dbpath + suffix + ".bak")
        if dst.exists():
            dst.unlink()
        fileutil.copy(src, dst)
        backup_files.append(dst)
    return [str(b) for b in backup_files]


def sqlite_delete_dbfiles(dbpath: str) -> list[str]:
    """Delete all files associated with a sqlite file at dbpath

    Args:
        dbpath: path to sqlite database file

    Returns:
        list of files deleted

    Raises:
        FileNotFoundError if dbpath does not exist
    """
    if not pathlib.Path(dbpath).exists():
        raise FileNotFoundError(f"sqlite database file not found: {dbpath}")

    deleted_files = []
    for suffix in ["", "-wal", "-shm"]:
        src = pathlib.Path(dbpath + suffix)
        if not src.exists():
            continue
        src.unlink()
        deleted_files.append(src)
    return [str(d) for d in deleted_files]


def sqlite_delete_backup_files(dbpath: str) -> list[str]:
    """Delete all .bak files associated with a sqlite file at dbpath

    Args:
        dbpath: path to sqlite database file

    Returns: list of files deleted
    """
    deleted_files = []
    for suffix in ["", "-wal", "-shm"]:
        src = pathlib.Path(dbpath + suffix + ".bak")
        if not src.exists():
            continue
        src.unlink()
        deleted_files.append(src)
    return [str(d) for d in deleted_files]
