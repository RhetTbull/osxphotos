# Test special photo types

import pytest

PHOTOS_DB_CLOUD = "./tests/Test-Cloud-10.16.0.photoslibrary/database/photos.db"

UUID_DICT = {
    "portrait1": "DB0CCC3C-99B6-479D-9C87-13116501908B",
    "portrait2": "3437FC20-10B7-49AD-A3B6-FF1520212284",
    "hdr": "EC902321-47A2-47FA-B9B9-932F3CF27EF1",
    "selfie": "885AD89C-FD5B-4FC3-A22F-3DE99818E976",
    "time_lapse": "B8C2751C-CAF4-4155-A127-8453093BDA91",
    "panorama": "DC310838-BC30-4AF9-B18A-AC0782D25EFE",
    "no_specials": "793A2156-4E2D-4330-8D7D-97C4E58DDC41",
}


def test_portrait1():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB_CLOUD)
    photos = photosdb.photos(uuid=[UUID_DICT["portrait1"]])

    assert photos[0].portrait
    assert not photos[0].hdr
    assert not photos[0].selfie
    assert not photos[0].time_lapse
    assert not photos[0].panorama

    photos = photosdb.photos(uuid=[UUID_DICT["no_specials"]])
    assert not photos[0].portrait


def test_portrait2():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB_CLOUD)
    photos = photosdb.photos(uuid=[UUID_DICT["portrait2"]])

    assert photos[0].portrait
    assert not photos[0].hdr
    assert not photos[0].selfie
    assert not photos[0].time_lapse
    assert not photos[0].panorama

    photos = photosdb.photos(uuid=[UUID_DICT["no_specials"]])
    assert not photos[0].portrait


def test_hdr():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB_CLOUD)
    photos = photosdb.photos(uuid=[UUID_DICT["hdr"]])

    assert photos[0].hdr
    assert not photos[0].portrait
    assert not photos[0].selfie
    assert not photos[0].time_lapse
    assert not photos[0].panorama

    photos = photosdb.photos(uuid=[UUID_DICT["no_specials"]])
    assert not photos[0].hdr


def test_selfie():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB_CLOUD)
    photos = photosdb.photos(uuid=[UUID_DICT["selfie"]])

    assert photos[0].selfie
    assert not photos[0].portrait
    assert not photos[0].hdr
    assert not photos[0].time_lapse
    assert not photos[0].panorama

    photos = photosdb.photos(uuid=[UUID_DICT["no_specials"]])
    assert not photos[0].selfie


def test_time_lapse():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB_CLOUD)
    photos = photosdb.photos(uuid=[UUID_DICT["time_lapse"]], movies=True)

    assert photos[0].time_lapse
    assert not photos[0].portrait
    assert not photos[0].hdr
    assert not photos[0].selfie
    assert not photos[0].panorama

    photos = photosdb.photos(uuid=[UUID_DICT["no_specials"]])
    assert not photos[0].time_lapse


def test_panorama():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB_CLOUD)
    photos = photosdb.photos(uuid=[UUID_DICT["panorama"]])

    assert photos[0].panorama
    assert not photos[0].portrait
    assert not photos[0].selfie
    assert not photos[0].time_lapse
    assert not photos[0].hdr

    photos = photosdb.photos(uuid=[UUID_DICT["no_specials"]])
    assert not photos[0].panorama
