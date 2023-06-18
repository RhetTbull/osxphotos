import pytest

# test empty library

PHOTOS_DB = "./tests/Empty-Library-4.0-3461.7.150.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Empty-Library-4.0-3461.7.150.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Empty-Library-4.0-3461.7.150.photoslibrary"

KEYWORDS = []
PERSONS = []
ALBUMS = []
KEYWORDS_DICT = {}
PERSONS_DICT = {}
ALBUM_DICT = {}


def test_init():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_db_version():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert photosdb.db_version in osxphotos._constants._TESTED_DB_VERSIONS
    assert photosdb.db_version == "4025"


def test_persons():
    import collections

    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert photosdb.persons == []


def test_keywords():
    import collections

    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert photosdb.keywords == []


def test_album_names():
    import collections

    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert photosdb.albums == []


def test_keywords_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    keywords = photosdb.keywords_as_dict
    assert keywords == {}


def test_persons_as_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    persons = photosdb.persons_as_dict
    assert persons == {}


def test_albums_as_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums = photosdb.albums_as_dict
    assert albums == {}


def test_count():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos()
    assert len(photos) == 0


def test_get_db_path():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    db_path = photosdb.db_path
    assert db_path.endswith(PHOTOS_DB_PATH)


def test_get_library_path():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    lib_path = photosdb.library_path
    assert lib_path.endswith(PHOTOS_LIBRARY_PATH)
