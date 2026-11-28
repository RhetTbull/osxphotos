"""Test that per-photo database queries reuse PhotosDB's shared connection (#2138)

Each sqlite3.Connection is in a reference cycle with its statement cache so a
connection that is not explicitly closed is only freed by the cyclic garbage
collector. Opening a new connection per photo therefore leaks file descriptors
during a large export until the process hits its open file limit.
"""

from __future__ import annotations

import pytest

import osxphotos

PHOTOS_DB = "tests/Test-13.0.0.photoslibrary/database/photos.db"
UUID = "D79B8D77-BFFC-460B-9312-034F2877D35B"  # Pumkins2.jpg

TABLE_NAMES = [
    "ZASSET",
    "ZADDITIONALASSETATTRIBUTES",
    "ZEXTENDEDATTRIBUTES",
    "ZDETECTEDFACE",
    "ZPERSON",
]


@pytest.fixture(scope="module")
def photosdb() -> osxphotos.PhotosDB:
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


@pytest.fixture
def connection_count(photosdb: osxphotos.PhotosDB, monkeypatch) -> list[int]:
    """Count calls to PhotosDB.get_db_connection, each of which opens a new connection"""
    count = [0]
    get_db_connection = photosdb.get_db_connection

    def counting_get_db_connection():
        count[0] += 1
        return get_db_connection()

    monkeypatch.setattr(photosdb, "get_db_connection", counting_get_db_connection)
    return count


def test_execute_reuses_connection(photosdb: osxphotos.PhotosDB, connection_count):
    """Test PhotosDB.execute uses the same connection on every call"""
    first = photosdb.execute("SELECT 1").connection
    second = photosdb.execute("SELECT 1").connection
    assert first is second
    assert connection_count[0] == 0


def test_cloud_metadata_no_new_connection(
    photosdb: osxphotos.PhotosDB, connection_count
):
    """Test PhotoInfo.cloud_metadata does not open a new database connection"""
    photo = photosdb.get_photo(UUID)
    assert isinstance(photo.cloud_metadata, dict)
    assert connection_count[0] == 0


@pytest.mark.parametrize("table_name", TABLE_NAMES)
def test_tables_no_new_connection(
    photosdb: osxphotos.PhotosDB, connection_count, table_name: str
):
    """Test PhotoInfo.tables() does not open a new database connection"""
    photo = photosdb.get_photo(UUID)
    table = getattr(photo.tables(), table_name)
    assert table.columns
    table.rows()
    getattr(table, table.columns[0])
    assert connection_count[0] == 0
