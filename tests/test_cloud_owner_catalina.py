# Test cloud photos and album owner

import pytest

import osxphotos

PHOTOS_DB_CLOUD = "./tests/Test-Cloud-10.15.6.photoslibrary/"
PHOTOS_DB_NOT_CLOUD = "./tests/Test-10.15.6.photoslibrary/"

UUID_DICT = {
    "not_cloudasset": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "owner": "7572C53E-1D6A-410C-A2B1-18CCA3B5AD9F",
}


@pytest.fixture(scope="module")
def photosdb_cloud():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_CLOUD)


@pytest.fixture(scope="module")
def photosdb_nocloud():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_NOT_CLOUD)


def test_album_owner_cloud(photosdb_cloud):
    album = [a for a in photosdb_cloud.album_info_shared if a.title == "osxphotos"][0]
    assert album.owner == "Rhet Turnbull"


def test_album_owner_not_cloud(photosdb_nocloud):
    album = [a for a in photosdb_nocloud.album_info if a.title == "Test Album"][0]
    assert album.owner is None


def test_photo_owner_cloud(photosdb_cloud):
    photo = photosdb_cloud.get_photo(UUID_DICT["owner"])
    assert photo.owner == "Rhet Turnbull"


def test_photo_owner_nocloud(photosdb_nocloud):
    photo = photosdb_nocloud.get_photo(UUID_DICT["not_cloudasset"])
    assert photo.owner is None
