import pytest

PHOTOS_DB = "./tests/Test-Shared-10.15.1.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-Shared-10.15.1.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-Shared-10.15.1.photoslibrary"

UUID_DICT = {
    "modified": "37210110-E940-4227-92D3-45C40F68EB0A",
    "not_modified": "35243F7D-88C4-4408-B516-C74406E90C15",
}


def test_modified():
    import datetime
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["modified"]])
    assert photos[0].date_modified is not None
    assert photos[0].date_modified.isoformat() == "2019-12-26T21:08:48.306538-07:00"


def test_not_modified():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["not_modified"]])
    assert photos[0].date_modified is None
