# Test cloud photos

import pytest

import osxphotos

PHOTOS_DB_CLOUD = "tests/Test-Cloud-10.16.0.photoslibrary"

UUID_DICT = {
    "incloud": "FC638F58-84BE-4083-B5DE-F85BDC729062",
    "shared": "2094984A-21DC-4A6E-88A6-7344F648B92E",
    "cloudasset": "FC638F58-84BE-4083-B5DE-F85BDC729062",
    "cloud_guid": "FC638F58-84BE-4083-B5DE-F85BDC729062",
}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_CLOUD)


def test_incloud(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["incloud"]])
    assert photos[0].incloud


def test_cloudasset_1(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["cloudasset"]])
    assert photos[0].iscloudasset


def test_path_derivatives(photosdb):
    photo = photosdb.get_photo(UUID_DICT["shared"])
    assert photo.path_derivatives


def test_cloud_guid(photosdb):
    photo = photosdb.get_photo(UUID_DICT["cloud_guid"])
    assert photo.cloud_guid == "AV6qPsEIU88bFVPKfEUjoyspg+d+"


def test_cloud_owner_hashed_id(photosdb):
    photo = photosdb.get_photo(UUID_DICT["shared"])
    assert (
        photo.cloud_owner_hashed_id
        == "01cac7cde8a8767251a2cdd183b8ed490fc6e87825f4a495389e824a41a01ba7"
    )
