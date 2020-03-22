""" Test PlaceInfo """
import pytest

from osxphotos._constants import _UNKNOWN_PERSON

PHOTOS_DB = "./tests/Test-10.14.6.photoslibrary/database/photos.db"

UUID_DICT = {"place_uk": "3Jn73XpSQQCluzRBMWRsMA", "no_place": "15uNd7%8RguTEgNPKHfTWw"}


def test_place_place_info_1():
    # test valid place info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_uk"]])[0]
    assert photo.place is not None
    assert isinstance(photo.place, osxphotos.placeinfo.PlaceInfo)
    assert not photo.place.ishome
    assert photo.place.name == "St James's Park"
    assert photo.place.names == [
        "St James's Park",
        "Westminster",
        "London",
        "England",
        "United Kingdom",
    ]
    assert photo.place.country_code == "GB"
    assert photo.place.address_str is None
    assert photo.place.address.city is None
    assert photo.place.address.country is None
    assert photo.place.address.postal_code is None
    assert photo.place.address.state is None
    assert photo.place.address.street is None
    assert photo.place.address.sub_administrative_area is None
    assert photo.place.address.sub_locality is None
    assert photo.place.address.iso_country_code is None


def test_place_no_place_info():
    # test valid place info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["no_place"]])[0]

    assert photo.place is None


def test_place_str():
    # test __str__
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_uk"]])[0]
    assert (
        str(photo.place)
        == "PlaceInfo(name='St James's Park', names='[\"St James's Park\", 'Westminster', 'London', 'England', 'United Kingdom']', country_code='GB')"
    )
