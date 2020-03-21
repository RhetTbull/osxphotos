""" Test PlaceInfo """
import pytest

from osxphotos._constants import _UNKNOWN_PERSON


PHOTOS_DB = "./tests/Test-Places-Catalina-10_15_1.photoslibrary/database/photos.db"

UUID_DICT = {
    "place_dc": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "place_maui": "FF7AFE2C-49B0-4C9B-B0D7-7E1F8B8F2F0C",
    "no_place": "A9B73E13-A6F2-4915-8D67-7213B39BAE9F",
}


def test_place_place_info_1():
    # test valid place info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]
    assert photo.place is not None
    assert isinstance(photo.place, osxphotos.placeinfo.PlaceInfo)
    assert not photo.place.ishome
    assert photo.place.name == "2038 18th St NW"
    assert photo.place.names == [
        "2038 18th St NW",
        "Adams Morgan",
        "Washington",
        "Washington",
        "Washington",
        "District of Columbia",
        "United States",
    ]
    assert photo.place.country_code == "US"
    assert (
        photo.place.address_str
        == "2038 18th St NW, Washington, DC  20009, United States"
    )
    assert photo.place.address.city == "Washington"
    assert photo.place.address.country == "United States"
    assert photo.place.address.postal_code == "20009"
    assert photo.place.address.state == "DC"
    assert photo.place.address.street == "2038 18th St NW"
    assert photo.place.address.sub_administrative_area is None
    assert photo.place.address.sub_locality == "Adams Morgan"
    assert photo.place.address.iso_country_code == "US"


def test_place_place_info_2():
    # test valid place info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_maui"]])[0]

    assert isinstance(photo.place, osxphotos.placeinfo.PlaceInfo)
    assert photo.place is not None
    assert not photo.place.ishome
    assert photo.place.name == "3700 Wailea Alanui Dr"
    assert photo.place.names == [
        "3700 Wailea Alanui Dr",
        "Wailea",
        "Kihei",
        "Kihei",
        "Maui",
        "Maui",
        "Hawai'i",
        "United States",
    ]
    assert photo.place.country_code == "US"
    assert (
        photo.place.address_str
        == "3700 Wailea Alanui Dr, Kihei, HI  96753, United States"
    )
    assert type(photo.place.address) == osxphotos.placeinfo.PostalAddress
    assert photo.place.address.city == "Kihei"
    assert photo.place.address.country == "United States"
    assert photo.place.address.postal_code == "96753"
    assert photo.place.address.state == "HI"
    assert photo.place.address.street == "3700 Wailea Alanui Dr"
    assert photo.place.address.sub_administrative_area == "Maui"
    assert photo.place.address.sub_locality is None
    assert photo.place.address.iso_country_code == "US"


def test_place_no_place_info():
    # test valid place info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["no_place"]])[0]

    assert photo.place is None
