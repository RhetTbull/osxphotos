"""Tests for AlbumInfo start_date/end_date (#2238)."""

from __future__ import annotations

import datetime

import pytest

import osxphotos

EMPTY_ALBUM_UUID = "D4DC7467-1F13-46E8-86BC-540FB059463C"

# import session with null ZSTARTDATE/ZENDDATE in Test-15.4.1 and Test-26.1
NULL_DATE_IMPORT_UUID = "78F89405-D463-4AD8-83D2-B89A76182E8A"

# each of these libraries has an album "EmptyAlbum" with null ZSTARTDATE/ZENDDATE
LIBRARIES = [
    "tests/Test-10.15.7.photoslibrary",
    "tests/Test-15.4.1.photoslibrary",
    "tests/Test-26.1.photoslibrary",
]


@pytest.fixture(scope="module", params=LIBRARIES)
def photosdb(request) -> osxphotos.PhotosDB:
    return osxphotos.PhotosDB(dbfile=request.param)


def test_empty_album_dates_are_none(photosdb: osxphotos.PhotosDB):
    """An album with no photos has no start or end date."""
    album = next(a for a in photosdb.album_info if a.uuid == EMPTY_ALBUM_UUID)
    assert album.title == "EmptyAlbum"
    assert not album.photos
    assert album.start_date is None
    assert album.end_date is None
    album_dict = album.asdict()
    assert album_dict["start_date"] is None
    assert album_dict["end_date"] is None


def test_non_empty_album_dates(photosdb: osxphotos.PhotosDB):
    """Albums with photos still have start and end dates."""
    albums = [a for a in photosdb.album_info if a.photos]
    assert albums
    for album in albums:
        assert isinstance(album.start_date, datetime.datetime)
        assert isinstance(album.end_date, datetime.datetime)
        assert album.start_date <= album.end_date


@pytest.mark.parametrize(
    "library", ["tests/Test-15.4.1.photoslibrary", "tests/Test-26.1.photoslibrary"]
)
def test_import_session_null_dates_are_none(library: str):
    """Import session with null start/end dates returns None, not 2001-01-01."""
    photosdb = osxphotos.PhotosDB(dbfile=library)
    import_info = next(
        p.import_info
        for p in photosdb.photos()
        if p.import_info and p.import_info.uuid == NULL_DATE_IMPORT_UUID
    )
    assert isinstance(import_info.creation_date, datetime.datetime)
    assert import_info.start_date is None
    assert import_info.end_date is None
