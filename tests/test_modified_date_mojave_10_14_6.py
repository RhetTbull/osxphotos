import pytest

import osxphotos

PHOTOS_DB = "./tests/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-Shared-10.14.6.photoslibrary"

UUID_DICT = {
    "modified": "3Jn73XpSQQCluzRBMWRsMA",
    "not_modified": "35243F7D-88C4-4408-B516-C74406E90C15",
}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_modified(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["modified"]])
    assert photos[0].date_modified is not None
    assert photos[0].date_modified.isoformat() == "2019-12-01T11:43:45.714123-04:00"


# no non-modified photos in the 10.14.6 database
# def test_not_modified():
#     import osxphotos

#     photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
#     photos = photosdb.photos(uuid=[UUID_DICT["not_modified"]])
#     assert photos[0].date_modified is None
