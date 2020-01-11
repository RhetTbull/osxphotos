# Test live photos

import pytest

PHOTOS_DB = "./tests/Test-Cloud-10.15.1.photoslibrary/database/photos.db"

UUID_DICT = {
    "live": "51F2BEF7-431A-4D31-8AC1-3284A57826AE",
    "not_live": "9D671650-B2FD-4760-84CA-FD25AF622C63",
}


def test_live_photo():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["live"]])

    assert photos[0].live_photo
    assert photos[0].path_live_photo is not None


def test_not_live_photo():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["not_live"]])

    assert not photos[0].live_photo
    assert photos[0].path_live_photo is None
