"""Tests for sqlite_utils """

import sqlite3

import pytest

from osxphotos.sqlite_utils import sqlite_db_is_locked, sqlite_open_ro

DB_UNLOCKED_10_15 = "./tests/Test-10.15.1.photoslibrary/database/photos.db"


def test_db_is_locked_unlocked():
    assert not sqlite_db_is_locked(DB_UNLOCKED_10_15)


def test_open_sqlite_ro():
    conn, cur = sqlite_open_ro(DB_UNLOCKED_10_15)
    assert isinstance(conn, sqlite3.Connection)
    assert isinstance(cur, sqlite3.Cursor)
    conn.close()
