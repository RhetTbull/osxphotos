# Test cloud photos

import pytest

import osxphotos

PHOTOS_DB_CLOUD = "./tests/Test-Cloud-10.14.6.photoslibrary/database/photos.db"
PHOTOS_DB_NOT_CLOUD = "./tests/Test-10.14.6.photoslibrary/database/photos.db"

UUID_DICT = {
    "incloud": "jNzHQgSxStK%Ll2aDOLakQ",
    "not_incloud": "h0m8G5PWTKqJwD4p9QGA5w",
    "cloudasset": "iOrNkBNSTxSELZtbSeBr1A",
    "not_cloudasset": "8SOE9s0XQVGsuq4ONohTng",
}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_CLOUD)


def test_incloud(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["incloud"]])

    assert photos[0].incloud


def test_not_incloud(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["not_incloud"]])

    assert not photos[0].incloud


def test_cloudasset_1(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["cloudasset"]])

    assert photos[0].iscloudasset


def test_cloudasset_2(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["not_incloud"]])

    # not_incloud is still a cloud asset
    assert photos[0].iscloudasset


def test_cloudasset_3():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB_NOT_CLOUD)
    photos = photosdb.photos(uuid=[UUID_DICT["not_cloudasset"]])

    assert not photos[0].iscloudasset
