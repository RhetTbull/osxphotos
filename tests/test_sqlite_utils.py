"""Tests for sqlite_utils"""

import pathlib
import shutil
import sqlite3
import tempfile

import pytest

import osxphotos.sqlite_utils as sqlite_utils
from osxphotos.sqlite_utils import (
    sqlite_db_is_locked,
    sqlite_open_ro,
    sqlite_open_ro_with_temp_copy,
)

DB_UNLOCKED_10_15 = "./tests/Test-10.15.1.photoslibrary/database/photos.db"


def test_db_is_locked_unlocked():
    assert not sqlite_db_is_locked(DB_UNLOCKED_10_15)


def test_open_sqlite_ro():
    conn, cur = sqlite_open_ro(DB_UNLOCKED_10_15)
    assert isinstance(conn, sqlite3.Connection)
    assert isinstance(cur, sqlite3.Cursor)
    conn.close()


def test_open_sqlite_ro_with_temp_copy_if_locked(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test_table (value TEXT)")
    conn.execute("INSERT INTO test_table VALUES ('test')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(sqlite_utils, "sqlite_db_is_locked", lambda _: True)

    conn, cur = sqlite_open_ro_with_temp_copy(db_path)
    temp_db = pathlib.Path(conn.execute("PRAGMA database_list").fetchone()[2])

    assert temp_db != db_path.resolve()
    assert cur.execute("SELECT value FROM test_table").fetchone()[0] == "test"
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO test_table VALUES ('readonly')")

    conn.close()
    assert not temp_db.exists()


def test_sqlite_temp_copy_dbfiles_copies_associated_files(tmp_path, monkeypatch):
    class CopyUtil:
        @classmethod
        def copy(cls, src, dst):
            copied.append((pathlib.Path(src).name, pathlib.Path(dst).name))
            shutil.copyfile(src, dst)

    copied = []
    db_path = tmp_path / "test.sqlite"
    for suffix in ["", "-wal", "-shm"]:
        pathlib.Path(f"{db_path}{suffix}").write_text(f"data{suffix}")

    monkeypatch.setattr(sqlite_utils, "is_macos", False)
    monkeypatch.setattr(sqlite_utils, "FileUtil", CopyUtil)

    tempdir = tempfile.TemporaryDirectory()
    try:
        temp_db = sqlite_utils._sqlite_temp_copy_dbfiles(db_path, tempdir)

        assert temp_db == pathlib.Path(tempdir.name) / db_path.name
        assert pathlib.Path(f"{temp_db}-wal").read_text() == "data-wal"
        assert pathlib.Path(f"{temp_db}-shm").read_text() == "data-shm"
        assert copied == [
            ("test.sqlite", "test.sqlite"),
            ("test.sqlite-wal", "test.sqlite-wal"),
            ("test.sqlite-shm", "test.sqlite-shm"),
        ]
    finally:
        tempdir.cleanup()
