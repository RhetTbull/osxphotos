# Test cloud photos

import pytest

PHOTOS_DB_CLOUD = "./tests/Test-Cloud-10.14.6.photoslibrary/database/photos.db"

UUID_DICT = {
    # "portrait": "7CDA5F84-AA16-4D28-9AA6-A49E1DF8A332",
    "hdr": "UIgouj2cQqyKJnB2bCHrSg",
    "selfie": "NsO5Yg8qSPGBGiVxsCd5Kw",
    "time_lapse": "pKAWFwtlQYuR962KEaonPA",
    # "panorama": "1C1C8F1F-826B-4A24-B1CB-56628946A834",
    "no_specials": "%PgMNP%xRTWTJF+oOyZbXQ",
}


@pytest.mark.skip(reason="don't have portrait photo in the 10.14.6 database")
def test_portrait():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB_CLOUD)
    photos = photosdb.photos(uuid=[UUID_DICT["portrait"]])

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


@pytest.mark.skip(reason="no panorama in 10.14.6 database")
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
