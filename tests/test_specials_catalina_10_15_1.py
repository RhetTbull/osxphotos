# Test cloud photos

import pytest

PHOTOS_DB_CLOUD = "./tests/Test-Cloud-10.15.1.photoslibrary/database/photos.db"

UUID_DICT = {
    "portrait": "7CDA5F84-AA16-4D28-9AA6-A49E1DF8A332",
    "hdr": "D11D25FF-5F31-47D2-ABA9-58418878DC15",
    "selfie": "080525C4-1F05-48E5-A3F4-0C53127BB39C",
    "time_lapse": "4614086E-C797-4876-B3B9-3057E8D757C9",
    "panorama": "1C1C8F1F-826B-4A24-B1CB-56628946A834",
    "no_specials": "C2BBC7A4-5333-46EE-BAF0-093E72111B39",
}


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
