import pytest

import osxphotos

PHOTOS_DB = "./tests/Test-10.15.7.photoslibrary/database/photos.db"

UUID_DICT = {
    "modified": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "not_modified": "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068",
}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_modified(photosdb):
    import datetime

    photos = photosdb.photos(uuid=[UUID_DICT["modified"]])
    assert photos[0].date_modified is not None
    assert photos[0].date_modified == datetime.datetime(
        2019,
        7,
        27,
        17,
        33,
        28,
        398138,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
    )


def test_not_modified(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["not_modified"]])
    assert photos[0].date_modified is None
