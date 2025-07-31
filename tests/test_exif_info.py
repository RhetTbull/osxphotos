""" Test ExifInfo """

import datetime

import pytest

import osxphotos
from osxphotos.exifinfo import ExifInfo

PHOTOS_DB_5 = "tests/Test-Cloud-10.15.1.photoslibrary"
PHOTOS_DB_4 = "tests/Test-10.14.6.photoslibrary"
PHOTOS_DB_8 = "tests/Test-13.0.0.photoslibrary"

EXIF_DICT_5 = {
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

EXIF_DICT_8 = {
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": ExifInfo(
        flash_fired=True,
        iso=160,
        metering_mode=3,
        sample_rate=None,
        track_format=None,
        white_balance=0,
        aperture=2.2,
        bit_rate=None,
        duration=None,
        exposure_bias=None,
        focal_length=100.0,
        fps=None,
        latitude=None,
        longitude=None,
        shutter_speed=0.001,
        camera_make="NIKON CORPORATION",
        camera_model="NIKON D810",
        codec=None,
        lens_model="100.0 mm f/2.0",
        date=datetime.datetime(
            2019,
            4,
            15,
            14,
            40,
            24,
            860000,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
        ),
        tzoffset=-14400,
        tzname="America/New_York",
    ),
    "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A": ExifInfo(
        flash_fired=False,
        iso=200,
        metering_mode=5,
        sample_rate=None,
        track_format=None,
        white_balance=0,
        aperture=2.8,
        bit_rate=None,
        duration=None,
        exposure_bias=0.0,
        focal_length=6.1,
        fps=None,
        latitude=None,
        longitude=None,
        shutter_speed=0.03333333333333333,
        camera_make="Canon",
        camera_model="Canon PowerShot G10",
        codec=None,
        lens_model="6.1-30.5 mm",
        date=None,
        tzoffset=None,
        tzname=None,
    ),
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91": ExifInfo(
        flash_fired=False,
        iso=80,
        metering_mode=5,
        sample_rate=None,
        track_format=None,
        white_balance=0,
        aperture=4.0,
        bit_rate=None,
        duration=None,
        exposure_bias=0.0,
        focal_length=12.07,
        fps=None,
        latitude=None,
        longitude=None,
        shutter_speed=0.0015625,
        camera_make="Canon",
        camera_model="Canon PowerShot G10",
        codec=None,
        lens_model="6.1-30.5 mm",
        date=datetime.datetime(
            2020,
            4,
            15,
            10,
            25,
            51,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
        ),
        tzoffset=-14400,
        tzname="America/New_York",
    ),
}


@pytest.fixture
def photosdb5() -> osxphotos.PhotosDB:
    import osxphotos

    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_5)


@pytest.fixture
def photosdb8() -> osxphotos.PhotosDB:
    import osxphotos

    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_8)


def test_exif_info_v5(photosdb5: osxphotos.PhotosDB):
    """test exif_info"""
    for uuid in EXIF_DICT_5:
        photo = photosdb5.photos(uuid=[uuid], movies=True)[0]
        assert photo.exif_info == EXIF_DICT_5[uuid]


def test_exif_info_v4():
    """test version 4, exif_info should be None"""
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB_4)
    for photo in photosdb.photos():
        assert photo.exif_info is None


def test_exif_info_v8(photosdb8: osxphotos.PhotosDB):
    """test exif_info"""
    for uuid in EXIF_DICT_8:
        photo = photosdb8.photos(uuid=[uuid], movies=True)[0]
        assert photo.exif_info == EXIF_DICT_8[uuid]
