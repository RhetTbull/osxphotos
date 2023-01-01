import pytest

import osxphotos

# TODO: put some of this code into a pre-function

PHOTOS_DB = "./tests/Test-Shared-10.15.1.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-Shared-10.15.1.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-Shared-10.15.1.photoslibrary"

KEYWORDS = ["portrait"]
# Photos 5 includes blank person for detected face
PERSONS = []
ALBUMS = ["Photo Shoot"]
ALBUMS_SHARED = ["osxphotos"]

UUID_DICT = {
    "missing": "9D671650-B2FD-4760-84CA-FD25AF622C63",
    "notmissing": "35243F7D-88C4-4408-B516-C74406E90C15",
}

UUID_SHARED = [
    "9D671650-B2FD-4760-84CA-FD25AF622C63",
    "35243F7D-88C4-4408-B516-C74406E90C15",
]

UUID_NOT_SHARED = ["37210110-E940-4227-92D3-45C40F68EB0A"]


def test_album_names():
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums = photosdb.albums

    assert len(albums) == 1
    assert albums[0] == ALBUMS[0]


def test_albums_shared():
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums_shared = photosdb.albums_shared

    assert len(albums_shared) == 1
    assert albums_shared[0] == ALBUMS_SHARED[0]


def test_albums_as_dict():
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums_as_dict = photosdb.albums_as_dict

    assert len(albums_as_dict) == 1
    assert albums_as_dict[ALBUMS[0]] == 1


def test_albums_shared_as_dict():
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums_shared_as_dict = photosdb.albums_shared_as_dict

    assert len(albums_shared_as_dict) == 1
    assert albums_shared_as_dict[ALBUMS_SHARED[0]] == 2


def test_missing_share():
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = [p for p in photosdb.photos() if p.ismissing]

    assert len(photos) == 1
    assert photos[0].uuid == UUID_DICT["missing"]


def test_shared():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = [p for p in photosdb.photos() if p.shared]
    assert len(photos) == len(UUID_SHARED)
    for p in photos:
        assert p.uuid in UUID_SHARED


def test_not_shared():
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = [p for p in photosdb.photos() if not p.shared]
    assert len(photos) == 1
    for p in photos:
        assert p.uuid in UUID_NOT_SHARED


def test_query_shared_album():
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(albums=[ALBUMS_SHARED[0]])

    assert len(photos) == len(UUID_SHARED)
    for p in photos:
        assert p.uuid in UUID_SHARED


def test_query_shared_path():
    """Test shared path is not None for shared photos"""
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    for p in photosdb.photos():
        if not p.shared or p.ismissing:
            continue
        assert p.path
        assert p.path_derivatives
