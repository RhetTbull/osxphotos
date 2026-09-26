"""Test sqlgrep"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest

from osxphotos.sqlgrep import sqlgrep


@pytest.fixture
def db_path(tmp_path: pathlib.Path) -> str:
    """Create a small sqlite database with text, integer, NULL, and blob values"""
    path = tmp_path / "test.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE photos (name TEXT, count INTEGER, data BLOB)")
        conn.execute(
            "INSERT INTO photos VALUES (?, ?, ?)", ("foo.jpg", 0, b"foo in a blob")
        )
        conn.execute("INSERT INTO photos VALUES (?, ?, ?)", ("bar.jpg", None, None))
    conn.close()
    return str(path)


def test_sqlgrep_text(db_path: str):
    assert list(sqlgrep(db_path, "foo", print_filename=False)) == [
        ["photos", "name", "0", "foo.jpg"]
    ]


def test_sqlgrep_integer_zero(db_path: str):
    """Falsy but non-NULL values are still searched"""
    assert list(sqlgrep(db_path, "^0$", print_filename=False)) == [
        ["photos", "count", "0", "0"]
    ]


@pytest.mark.parametrize("pattern", ["blob", "None"])
def test_sqlgrep_skips_blob_and_null(db_path: str, pattern: str):
    assert not list(sqlgrep(db_path, pattern, print_filename=False))
