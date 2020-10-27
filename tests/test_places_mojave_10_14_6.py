""" Test PlaceInfo """
import pytest

PHOTOS_DB = "./tests/Test-10.14.6.photoslibrary/database/photos.db"

UUID_DICT = {"place_uk": "3Jn73XpSQQCluzRBMWRsMA", "no_place": "15uNd7%8RguTEgNPKHfTWw"}

UK_DICT = {
    "name": "St James's Park, Westminster, United Kingdom",
    "names": {
        "field0": [],
        "country": ["United Kingdom"],
        "state_province": ["England"],
        "sub_administrative_area": ["London"],
        "city": ["Westminster"],
        "field5": [],
        "additional_city_info": [],
        "ocean": [],
        "area_of_interest": ["St James's Park"],
        "inland_water": [],
        "field10": [],
        "region": [],
        "sub_throughfare": [],
        "field13": [],
        "postal_code": [],
        "field15": [],
        "field16": [],
        "street_address": [],
        "body_of_water": [],
    },
    "country_code": "GB",
}


def test_place_place_info_1():
    # test valid place info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_uk"]])[0]
    assert photo.place is not None
    assert isinstance(photo.place, osxphotos.placeinfo.PlaceInfo)
    assert not photo.place.ishome
    assert photo.place.name == "St James's Park, Westminster, United Kingdom"
    assert photo.place.names.area_of_interest == ["St James's Park"]
    assert photo.place.names.city == ["Westminster"]
    assert photo.place.names.sub_administrative_area == ["London"]
    assert photo.place.names.state_province == ["England"]
    assert photo.place.names.country == ["United Kingdom"]

    assert photo.place.country_code == "GB"
    assert photo.place.address_str is None
    assert photo.place.address.city is None
    assert photo.place.address.country is None
    assert photo.place.address.postal_code is None
    assert photo.place.address.state_province is None
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
        == "PlaceInfo(name='St James's Park, Westminster, United Kingdom', "
        "names='PlaceNames(field0=[], country=['United Kingdom'], "
        "state_province=['England'], sub_administrative_area=['London'], "
        "city=['Westminster'], field5=[], additional_city_info=[], ocean=[], "
        'area_of_interest=["St James\'s Park"], inland_water=[], field10=[], '
        "region=[], sub_throughfare=[], field13=[], postal_code=[], field15=[], "
        "field16=[], street_address=[], body_of_water=[])', country_code='GB')"
    )


def test_place_as_dict():
    # test PlaceInfo.asdict()
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_uk"]])[0]
    assert photo.place is not None
    assert isinstance(photo.place, osxphotos.placeinfo.PlaceInfo)
    assert photo.place.asdict() == UK_DICT
