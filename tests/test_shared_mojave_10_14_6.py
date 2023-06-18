import pytest

PHOTOS_DB = "./tests/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-10.14.6.photoslibrary"

ALBUMS = ["Pumpkin Farm", "AlbumInFolder", "Test Album", "Test Album (1)"]
ALBUM_DICT = {
    "Pumpkin Farm": 3,
    "AlbumInFolder": 1,
    "Test Album": 1,
    "Test Album (1)": 1,
}


PHOTOS_DB_LEN = 13
PHOTOS_NOT_IN_TRASH_LEN = 12
PHOTOS_IN_TRASH_LEN = 1


def test_album_names():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums = photosdb.albums

    assert len(albums) == len(ALBUMS)
    for album in albums:
        assert album in ALBUMS


def test_albums_names_shared():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums_shared = photosdb.albums_shared

    assert len(albums_shared) == 0


def test_albums_as_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums_as_dict = photosdb.albums_as_dict

    for album in albums_as_dict:
        assert album in ALBUM_DICT
        assert albums_as_dict[album] == ALBUM_DICT[album]


def test_albums_shared_as_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums_shared_as_dict = photosdb.albums_shared_as_dict

    assert albums_shared_as_dict == {}


def test_shared():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = [p for p in photosdb.photos() if p.shared]
    assert len(photos) == 0


def test_not_shared():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = [p for p in photosdb.photos() if not p.shared]
    assert len(photos) == PHOTOS_NOT_IN_TRASH_LEN
