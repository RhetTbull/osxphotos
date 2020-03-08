# Test cloud photos

import pytest

PHOTOS_DB = "./tests/Test-10.12.6.photoslibrary/database/photos.db"

UUID_DICT = {"no_specials": "Pj99JmYjQkeezdY2OFuSaw"}


def test_portrait():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    # photos = photosdb.photos(uuid=[UUID_DICT["portrait"]])

    # assert photos[0].portrait
    # assert not photos[0].hdr
    # assert not photos[0].selfie
    # assert not photos[0].time_lapse
    # assert not photos[0].panorama

    photos = photosdb.photos(uuid=[UUID_DICT["no_specials"]])
    assert not photos[0].portrait


def test_hdr():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    # photos = photosdb.photos(uuid=[UUID_DICT["hdr"]])

    # assert photos[0].hdr
    # assert not photos[0].portrait
    # assert not photos[0].selfie
    # assert not photos[0].time_lapse
    # assert not photos[0].panorama

    photos = photosdb.photos(uuid=[UUID_DICT["no_specials"]])
    assert not photos[0].hdr


def test_selfie():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    # photos = photosdb.photos(uuid=[UUID_DICT["selfie"]])

    # assert photos[0].selfie
    # assert not photos[0].portrait
    # assert not photos[0].hdr
    # assert not photos[0].time_lapse
    # assert not photos[0].panorama

    photos = photosdb.photos(uuid=[UUID_DICT["no_specials"]])
    assert photos[0].selfie is None


def test_time_lapse():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    # photos = photosdb.photos(uuid=[UUID_DICT["time_lapse"]], movies=True)

    # assert photos[0].time_lapse
    # assert not photos[0].portrait
    # assert not photos[0].hdr
    # assert not photos[0].selfie
    # assert not photos[0].panorama

    photos = photosdb.photos(uuid=[UUID_DICT["no_specials"]])
    assert not photos[0].time_lapse


def test_panorama():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    # photos = photosdb.photos(uuid=[UUID_DICT["panorama"]])

    # assert photos[0].panorama
    # assert not photos[0].portrait
    # assert not photos[0].selfie
    # assert not photos[0].time_lapse
    # assert not photos[0].hdr

    photos = photosdb.photos(uuid=[UUID_DICT["no_specials"]])
    assert not photos[0].panorama
