"""sqlite utils for use by osxphotos"""

from __future__ import annotations

import logging
import os
import pathlib
import shlex
import shutil
import sqlite3
import subprocess
import tempfile
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
    "sqlite_recover_db",
    "sqlite_repair_db",
    "sqlite_tables",
    "sqlite_db_is_ok",
]


def get_sqlite_cli() -> str:
    """Returns path to sqlite3 command line tool"""
    return shutil.which("sqlite3")


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


def sqlite_db_is_locked(dbname: str | pathlib.Path) -> bool:
    """check to see if a sqlite3 db is locked
    returns True if database is locked, otherwise False
    dbname: name of database to test"""

    try:
        (conn, c) = sqlite_open_ro(dbname)
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        conn.close()
        return False
    except Exception as e:
        logger.debug(f"sqlite_db_is_locked: {e}")
        return True


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


def sqlite_backup_dbfiles(dbpath: str | pathlib.Path) -> list[str]:
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


def sqlite_delete_dbfiles(dbpath: str | pathlib.Path) -> list[str]:
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


def sqlite_delete_backup_files(dbpath: str | pathlib.Path) -> list[str]:
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


def sqlite_check_integrity(dbpath: str | pathlib.Path) -> list[str]:
    """Check integrity of sqlite database at dbpath

    Returns:
        list of errors found or empty list if no errors
    """
    dbpath = str(dbpath)
    try:
        conn = sqlite3.connect(
            dbpath, timeout=1, check_same_thread=SQLITE_CHECK_SAME_THREAD
        )
        results = conn.execute("PRAGMA integrity_check;").fetchall()
        if results[0][0] == "ok":
            return []
        return [row[0] for row in results]
    except sqlite3.Error:
        return ["Unknown error"]
    finally:
        conn.close()


def sqlite_db_is_ok(dbpath: str | pathlib.Path) -> bool:
    """Check integrity of sqlite database at dbpath"""
    return not sqlite_check_integrity(dbpath)


def sqlite_repair_db(dbpath: str | pathlib.Path):
    """Attempt to repair a corrupt sqlite database file at dbpath

    Args:
        dbpath: path to sqlite database file

    Raises:
        sqlite3.Error if repair fails
    """

    if sqlite_db_is_ok(dbpath):
        return
    try:
        sqlite_recover_db(dbpath)
        conn = sqlite3.connect(
            dbpath, timeout=1, check_same_thread=SQLITE_CHECK_SAME_THREAD
        )
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Error repairing sqlite database: {e}") from e
    conn.execute("PRAGMA wal_checkpoint(RESTART);")
    conn.close()


def sqlite_recover_db(dbpath: str | pathlib.Path) -> None:
    """Attempt to recover a corrupt sqlite database file at dbpath

    Args:
        dbpath: path to sqlite database file

    Raises:
        sqlite3.Error if recovery fails
        FileNotFoundError if sqlite3 command line tool not found

    Note: If successful, copies the old database to dbpath.bak and the recovered database to dbpath
    This is a bit of a hack but may work as a last resort to recover a corrupt database.
    """

    dbpath = str(dbpath)

    sqlite_cli = get_sqlite_cli()
    if not sqlite_cli:
        raise FileNotFoundError("sqlite3 command line tool not found")

    try:
        sqlite_backup_dbfiles(dbpath)
        temp_file = os.path.join(tempfile.mkdtemp(), "temp_db.db")
        recovered_tmp_file = os.path.join(tempfile.mkdtemp(), "recovered_db.db")
        shutil.copy(dbpath, temp_file)
        cmd = f"{sqlite_cli} {shlex.quote(dbpath)} .recover > {shlex.quote(temp_file)}"
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        cmd = (
            f"{sqlite_cli} {shlex.quote(recovered_tmp_file)} < {shlex.quote(temp_file)}"
        )
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        os.remove(dbpath)
        shutil.copy(recovered_tmp_file, dbpath)
        os.remove(temp_file)
        os.remove(recovered_tmp_file)
    except subprocess.CalledProcessError as e:
        raise sqlite3.Error(
            f"Error recovering sqlite database: {e} {e.output.decode('utf-8')}"
        ) from e
    except Exception as e:
        raise sqlite3.Error(f"Error recovering sqlite database: {e}") from e
