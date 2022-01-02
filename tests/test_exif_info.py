""" Test ExifInfo """

import pytest

from osxphotos.exifinfo import ExifInfo

PHOTOS_DB_5 = "tests/Test-Cloud-10.15.1.photoslibrary"
PHOTOS_DB_4 = "tests/Test-10.14.6.photoslibrary"

EXIF_DICT = {
    "D11D25FF-5F31-47D2-ABA9-58418878DC15": ExifInfo(
        flash_fired=False,
        iso=50,
        metering_mode=3,
        sample_rate=None,
        track_format=None,
        white_balance=0,
        aperture=2.4,
        bit_rate=None,
        duration=None,
        exposure_bias=0.0,
        focal_length=4.12,
        fps=None,
        latitude=None,
        longitude=None,
        shutter_speed=0.03333333333333333,
        camera_make="Apple",
        camera_model="iPhone 5",
        codec=None,
        lens_model="iPhone 5 back camera 4.12mm f/2.4",
    ),
    "CCBE0EB9-AE9F-4479-BFFD-107042C75227": ExifInfo(
        flash_fired=False,
        iso=50,
        metering_mode=5,
        sample_rate=None,
        track_format=None,
        white_balance=0,
        aperture=2.4,
        bit_rate=None,
        duration=None,
        exposure_bias=0.0,
        focal_length=4.12,
        fps=None,
        latitude=None,
        longitude=None,
        shutter_speed=0.016666666666666666,
        camera_make="Apple",
        camera_model="iPhone 5",
        codec=None,
        lens_model="iPhone 5 back camera 4.12mm f/2.4",
    ),
    "5159B117-58DD-4DA0-B130-623662D9172F": ExifInfo(
        flash_fired=False,
        iso=None,
        metering_mode=None,
        sample_rate=None,
        track_format=None,
        white_balance=None,
        aperture=None,
        bit_rate=None,
        duration=0.8333333333333334,
        exposure_bias=None,
        focal_length=None,
        fps=30.0,
        latitude=None,
        longitude=None,
        shutter_speed=None,
        camera_make="Apple",
        camera_model="iPhone 5",
        codec="avc1",
        lens_model=None,
    ),
}


@pytest.fixture
def photosdb():
    import osxphotos

    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_5)


def test_exif_info_v5(photosdb):
    """test exif_info"""
    for uuid in EXIF_DICT:
        photo = photosdb.photos(uuid=[uuid], movies=True)[0]
        assert photo.exif_info == EXIF_DICT[uuid]


def test_exif_info_v4():
    """test version 4, exif_info should be None"""
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_4)
    for photo in photosdb.photos():
        assert photo.exif_info is None
