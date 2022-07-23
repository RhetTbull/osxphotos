"""Tests for sqlite_utils """

import pytest
import sqlite3

from osxphotos.sqlite_utils import sqlite_open_ro, sqlite_db_is_locked


DB_LOCKED_10_12 = "./tests/Test-Lock-10_12.photoslibrary/database/photos.db"
DB_LOCKED_10_15 = "./tests/Test-Lock-10_15_1.photoslibrary/database/Photos.sqlite"
DB_UNLOCKED_10_15 = "./tests/Test-10.15.1.photoslibrary/database/photos.db"


def test_db_is_locked_locked():

    assert sqlite_db_is_locked(DB_LOCKED_10_12)
    assert sqlite_db_is_locked(DB_LOCKED_10_15)


def test_db_is_locked_unlocked():

    assert not sqlite_db_is_locked(DB_UNLOCKED_10_15)


def test_open_sqlite_ro():

    conn, cur = sqlite_open_ro(DB_UNLOCKED_10_15)
    assert isinstance(conn, sqlite3.Connection)
    assert isinstance(cur, sqlite3.Cursor)
    conn.close()
