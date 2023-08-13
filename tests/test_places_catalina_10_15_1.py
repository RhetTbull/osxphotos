""" Test PlaceInfo """
import pytest

PHOTOS_DB = "./tests/Test-Places-Catalina-10_15_1.photoslibrary/database/photos.db"

UUID_DICT = {
    "place_dc": "128FB4C6-0B16-4E7D-9108-FB2E90DA1546",
    "place_maui": "FF7AFE2C-49B0-4C9B-B0D7-7E1F8B8F2F0C",
    "no_place": "A9B73E13-A6F2-4915-8D67-7213B39BAE9F",
}

MAUI_DICT = {
    "name": "Maui, Wailea, Hawai'i, United States",
    "names": {
        "field0": [],
        "country": ["United States"],
        "state_province": ["Hawai'i"],
        "sub_administrative_area": ["Maui"],
        "city": ["Wailea", "Kihei", "Kihei"],
        "field5": [],
        "additional_city_info": [],
        "ocean": [],
        "area_of_interest": [],
        "inland_water": [],
        "field10": [],
        "region": ["Maui"],
        "sub_throughfare": [],
        "field13": [],
        "postal_code": [],
        "field15": [],
        "field16": [],
        "street_address": ["3700 Wailea Alanui Dr"],
        "body_of_water": [],
    },
    "country_code": "US",
    "ishome": False,
    "address_str": "3700 Wailea Alanui Dr, Kihei, HI  96753, United States",
    "address": {
        "street": "3700 Wailea Alanui Dr",
        "sub_locality": None,
        "city": "Kihei",
        "sub_administrative_area": "Maui",
        "state_province": "HI",
        "postal_code": "96753",
        "country": "United States",
        "iso_country_code": "US",
    },
}


def test_place_place_info_1():
    # test valid place info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_dc"]])[0]
    assert photo.place is not None
    assert isinstance(photo.place, osxphotos.placeinfo.PlaceInfo)
    assert not photo.place.ishome
    assert photo.place.name == "Washington, District of Columbia, United States"
    assert photo.place.names.country[0] == "United States"
    assert photo.place.names.state_province[0] == "District of Columbia"
    assert photo.place.names.city[0] == "Washington"
    assert photo.place.names.additional_city_info[0] == "Adams Morgan"
    assert photo.place.names.street_address[0] == "2038 18th St NW"
    assert photo.place.names.ocean == []
    assert photo.place.names.area_of_interest == []
    assert photo.place.names.inland_water == []
    assert photo.place.names.postal_code == []
    assert photo.place.names.sub_throughfare == []
    assert photo.place.names.body_of_water == []

    assert photo.place.country_code == "US"
    assert (
        photo.place.address_str
        == "2038 18th St NW, Washington, DC  20009, United States"
    )
    assert photo.place.address.city == "Washington"
    assert photo.place.address.country == "United States"
    assert photo.place.address.postal_code == "20009"
    assert photo.place.address.state_province == "DC"
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
    assert photo.place.name == "Maui, Wailea, Hawai'i, United States"
    assert photo.place.names.street_address == ["3700 Wailea Alanui Dr"]
    assert photo.place.names.city == ["Wailea", "Kihei", "Kihei"]
    assert photo.place.names.region == ["Maui"]
    assert photo.place.names.sub_administrative_area == ["Maui"]
    assert photo.place.names.state_province == ["Hawai'i"]
    assert photo.place.names.country == ["United States"]

    assert photo.place.country_code == "US"
    assert (
        photo.place.address_str
        == "3700 Wailea Alanui Dr, Kihei, HI  96753, United States"
    )
    assert type(photo.place.address) == osxphotos.placeinfo.PostalAddress
    assert photo.place.address.city == "Kihei"
    assert photo.place.address.country == "United States"
    assert photo.place.address.postal_code == "96753"
    assert photo.place.address.state_province == "HI"
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


def test_place_place_info_asdict():
    # test PlaceInfo.asdict()
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_maui"]])[0]

    assert isinstance(photo.place, osxphotos.placeinfo.PlaceInfo)
    assert photo.place.asdict() == MAUI_DICT
