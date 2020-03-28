""" Test PlaceInfo """
import pytest

PHOTOS_DB = "./tests/Test-Places-High-Sierra-10.13.6.photoslibrary/database/photos.db"

UUID_DICT = {
    "place_dc": "YnaaVzUeQn28zK%eSrT8jg",
    "no_place": "pERZk5T1Sb+XcKDFRCsGpA",
    "place_2_names": "ohmoG%mITSG6dcN1PqDMkg",
    "place_chihuly": "B3PCiPVKSt2eEFGrV5CAFQ",
    "place_elder_park": "2L6X2hv3ROWRSCU3WRRAGQ",
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
    assert photo.place.names.country == ["United States"]
    assert photo.place.names.state_province == ["District of Columbia"]
    assert photo.place.names.sub_administrative_area == []
    assert photo.place.names.city == ["Washington"]
    assert photo.place.names.additional_city_info == []
    assert photo.place.names.ocean == []
    assert photo.place.names.area_of_interest == []
    assert photo.place.names.inland_water == []
    assert photo.place.names.region == []
    assert photo.place.names.postal_code == []
    assert photo.place.names.street_address == []
    assert photo.place.names.sub_throughfare == []
    assert photo.place.names.body_of_water == []

    assert photo.place.country_code == "US"
    assert photo.place.address_str is None
    assert photo.place.address.city is None
    assert photo.place.address.country is None
    assert photo.place.address.postal_code is None
    assert photo.place.address.state_province is None
    assert photo.place.address.street is None
    assert photo.place.address.sub_administrative_area is None
    assert photo.place.address.sub_locality is None
    assert photo.place.address.iso_country_code is None


def test_place_place_info_2():
    # test valid place info with only 2 names of info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_2_names"]])[0]
    assert photo.place is not None
    assert isinstance(photo.place, osxphotos.placeinfo.PlaceInfo)
    assert not photo.place.ishome
    assert photo.place.name == "Artibonite, Haiti"
    assert photo.place.names.country == ["Haiti"]
    assert photo.place.names.state_province == ["Artibonite"]
    assert photo.place.names.sub_administrative_area == []
    assert photo.place.names.city == []
    assert photo.place.names.additional_city_info == []
    assert photo.place.names.ocean == []
    assert photo.place.names.area_of_interest == []
    assert photo.place.names.inland_water == []
    assert photo.place.names.region == []
    assert photo.place.names.postal_code == []
    assert photo.place.names.street_address == []
    assert photo.place.names.sub_throughfare == []
    assert photo.place.names.body_of_water == ["Caribbean Sea"]

    assert photo.place.country_code == "HT"
    assert photo.place.address_str is None
    assert photo.place.address.city is None
    assert photo.place.address.country is None
    assert photo.place.address.postal_code is None
    assert photo.place.address.state_province is None
    assert photo.place.address.street is None
    assert photo.place.address.sub_administrative_area is None
    assert photo.place.address.sub_locality is None
    assert photo.place.address.iso_country_code is None


def test_place_place_info_3():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_chihuly"]])[0]
    assert photo.place is not None
    assert isinstance(photo.place, osxphotos.placeinfo.PlaceInfo)
    assert not photo.place.ishome
    assert photo.place.name == "Chihuly Garden and Glass, Seattle, United States"
    assert photo.place.names.country == ["United States"]
    assert photo.place.names.state_province == ["Washington"]
    assert photo.place.names.sub_administrative_area == ["King"]
    assert photo.place.names.city == ["Seattle"]
    assert photo.place.names.additional_city_info == []
    assert photo.place.names.ocean == []
    assert photo.place.names.area_of_interest == ["Chihuly Garden and Glass"]
    assert photo.place.names.inland_water == []
    assert photo.place.names.region == []
    assert photo.place.names.postal_code == []
    assert photo.place.names.street_address == []
    assert photo.place.names.sub_throughfare == []
    assert photo.place.names.body_of_water == []

    assert photo.place.country_code == "US"
    assert photo.place.address_str is None
    assert photo.place.address.city is None
    assert photo.place.address.country is None
    assert photo.place.address.postal_code is None
    assert photo.place.address.state_province is None
    assert photo.place.address.street is None
    assert photo.place.address.sub_administrative_area is None
    assert photo.place.address.sub_locality is None
    assert photo.place.address.iso_country_code is None


def test_place_place_info_4():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["place_elder_park"]])[0]
    assert photo.place is not None
    assert isinstance(photo.place, osxphotos.placeinfo.PlaceInfo)
    assert not photo.place.ishome
    assert photo.place.name == "Elder Park, Adelaide, Australia"
    assert photo.place.names.country == ["Australia"]
    assert photo.place.names.state_province == ["South Australia"]
    assert photo.place.names.sub_administrative_area == ["Adelaide"]
    assert photo.place.names.city == ["Adelaide"]
    assert photo.place.names.additional_city_info == []
    assert photo.place.names.ocean == []
    assert photo.place.names.area_of_interest == ["Elder Park"]
    assert photo.place.names.inland_water == []
    assert photo.place.names.region == []
    assert photo.place.names.postal_code == []
    assert photo.place.names.street_address == []
    assert photo.place.names.sub_throughfare == []
    assert photo.place.names.body_of_water == ["River Torrens"]


def test_place_no_place_info():
    # test valid place info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.photos(uuid=[UUID_DICT["no_place"]])[0]

    assert photo.place is None


# def test_place_str():
#     # test __str__
#     import osxphotos

#     photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
#     photo = photosdb.photos(uuid=[UUID_DICT["place_uk"]])[0]
#     assert (
#         str(photo.place)
#         == "PlaceInfo(name='St James's Park, Westminster, United Kingdom', "
#         "names='PlaceNames(field0=[], country=['United Kingdom'], "
#         "state_province=['England'], sub_administrative_area=['London'], "
#         "city=['Westminster'], field5=[], additional_city_info=[], ocean=[], "
#         "area_of_interest=[\"St James's Park\"], inland_water=[], field10=[], "
#         "region=[], sub_throughfare=[], field13=[], postal_code=[], field15=[], "
#         "field16=[], street_address=[], body_of_water=[])', country_code='GB')"
#     )
