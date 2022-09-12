"""sqlite utils for use by osxphotos"""

import logging
import pathlib
import sqlite3
from typing import List, Tuple


def sqlite_open_ro(dbname: str) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
    """opens sqlite file dbname in read-only mode
    returns tuple of (connection, cursor)"""
    try:
        dbpath = pathlib.Path(dbname).resolve()
        conn = sqlite3.connect(f"{dbpath.as_uri()}?mode=ro", timeout=1, uri=True)
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
        logging.debug(f"sqlite_db_is_locked: {e}")
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
