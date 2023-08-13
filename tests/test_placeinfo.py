""" Test PlaceInfo """
import pytest
from bpylist2 import archiver

from osxphotos.placeinfo import (
    CNPostalAddress,
    PlaceInfo,
    PlaceInfo4,
    PlaceInfo5,
    PLRevGeoLocationInfo,
    PLRevGeoMapItem,
    PLRevGeoMapItemAdditionalPlaceInfo,
)

REVERSE_GEO_LOC_DATA_1 = b'bplist00\xd4\x01\x02\x03\x04\x05\x06\x07\nX$versionY$archiverT$topX$objects\x12\x00\x01\x86\xa0_\x10\x0fNSKeyedArchiver\xd1\x08\tTroot\x80\x01\xaf\x10,\x0b\x0c!)4>?@GLMNSTUZ[`aefglmnru{\x7f\x80\x85\x86\x8a\x8b\x8f\xa1\xa2\xa3\xa4\xa5\xa6\xa9\xaa\xabU$null\xda\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1a\x1f VisHomeV$class]postalAddress_\x10\x16compoundSecondaryNames[countryCode]addressStringWversion]compoundNames_\x10\x12geoServiceProviderWmapItem\x08\x80+\x80"\x80\x00\x80 \x80)\x10\r\x80\x00\x80*\x80\x02\xd4\x0e"#$%&\'(_\x10\x0ffinalPlaceInfos_\x10\x10sortedPlaceInfos_\x10\x10backupPlaceInfos\x80!\x80\x1a\x80\x03\x80\x19\xd2*\x0e+3ZNS.objects\xa7,-./012\x80\x04\x80\x08\x80\x0b\x80\x0e\x80\x10\x80\x12\x80\x15\x80\x18\xd55\x0e6789:;<=_\x10\x11dominantOrderTypeTareaTnameYplaceType\x10\x00\x80\x07#\x00\x00\x00\x00\x00\x00\x00\x00\x80\x05\x80\x06_\x10\x0f2038 18th St NW\x10\x11\xd2ABCDZ$classnameX$classes_\x10"PLRevGeoMapItemAdditionalPlaceInfo\xa2EF_\x10"PLRevGeoMapItemAdditionalPlaceInfoXNSObject\xd55\x0e6789:IJK\x80\x07#A/M\x81\xe0\x00\x00\x00\x80\t\x80\n\\Adams Morgan\x10\x06\xd55\x0e6789:PQR\x80\x07#AIo;@\x00\x00\x00\x80\x0c\x80\rZWashington\x10\x04\xd55\x0e6789:WXR\x80\x07#A\xa4\x91\xc0@\x00\x00\x00\x80\x0f\x80\rZWashington\xd55\x0e6789:]^R\x80\x07#A\xa5 \xd9`\x00\x00\x00\x80\x11\x80\rZWashington\xd55\x0e6789:]cd\x80\x07\x80\x13\x80\x14_\x10\x14District of Columbia\x10\x02\xd55\x0e6789:ijk\x80\x07#B\xa2\xc3\xf5`\x00\x00\x00\x80\x16\x80\x17]United States\x10\x01\xd2ABop^NSMutableArray\xa3oqFWNSArray\xd2*\x0es3\xa0\x80\x18\xd2*\x0ev3\xa3wxy\x80\x1b\x80\x1d\x80\x1f\x80\x18\xd55\x0e678f:;}=\x80\x07\x80\x1c\x80\x06Z18th St NW\xd55\x0e678\x81:;\x83=\x10\x0b\x80\x07\x80\x1e\x80\x06RDC\xd55\x0e678\x1d:;\x1b=\x80\x07\x80 \x80\x06RUS\xd2AB\x8c\x8d_\x10\x0fPLRevGeoMapItem\xa2\x8eF_\x10\x0fPLRevGeoMapItem\xd9\x90\x0e\x91\x92\x93\x94\x95\x96\x97\x83\x99\x9a\x9b\x9c\x9d\x1a\x9f\x1bV_stateU_cityW_street[_postalCodeX_country_\x10\x16_subAdministrativeArea\\_subLocality_\x10\x0f_ISOCountryCode\x80\x1e\x80(\x80%\x80#\x80&\x80\'\x80\x00\x80$\x80 _\x10\x0f2038 18th St NW\\Adams MorganZWashingtonU20009]United States\xd2AB\xa7\xa8_\x10\x0fCNPostalAddress\xa2\xa7F_\x1052038 18th St NW, Washington, DC  20009, United StatesT7618\xd2AB\xac\xad_\x10\x14PLRevGeoLocationInfo\xa2\xaeF_\x10\x14PLRevGeoLocationInfo\x00\x08\x00\x11\x00\x1a\x00$\x00)\x002\x007\x00I\x00L\x00Q\x00S\x00\x82\x00\x88\x00\x9d\x00\xa4\x00\xab\x00\xb9\x00\xd2\x00\xde\x00\xec\x00\xf4\x01\x02\x01\x17\x01\x1f\x01 \x01"\x01$\x01&\x01(\x01*\x01,\x01.\x010\x012\x01;\x01M\x01`\x01s\x01u\x01w\x01y\x01{\x01\x80\x01\x8b\x01\x93\x01\x95\x01\x97\x01\x99\x01\x9b\x01\x9d\x01\x9f\x01\xa1\x01\xa3\x01\xae\x01\xc2\x01\xc7\x01\xcc\x01\xd6\x01\xd8\x01\xda\x01\xe3\x01\xe5\x01\xe7\x01\xf9\x01\xfb\x02\x00\x02\x0b\x02\x14\x029\x02<\x02a\x02j\x02u\x02w\x02\x80\x02\x82\x02\x84\x02\x91\x02\x93\x02\x9e\x02\xa0\x02\xa9\x02\xab\x02\xad\x02\xb8\x02\xba\x02\xc5\x02\xc7\x02\xd0\x02\xd2\x02\xd4\x02\xdf\x02\xea\x02\xec\x02\xf5\x02\xf7\x02\xf9\x03\x04\x03\x0f\x03\x11\x03\x13\x03\x15\x03,\x03.\x039\x03;\x03D\x03F\x03H\x03V\x03X\x03]\x03l\x03p\x03x\x03}\x03~\x03\x80\x03\x85\x03\x89\x03\x8b\x03\x8d\x03\x8f\x03\x91\x03\x9c\x03\x9e\x03\xa0\x03\xa2\x03\xad\x03\xb8\x03\xba\x03\xbc\x03\xbe\x03\xc0\x03\xc3\x03\xce\x03\xd0\x03\xd2\x03\xd4\x03\xd7\x03\xdc\x03\xee\x03\xf1\x04\x03\x04\x16\x04\x1d\x04#\x04+\x047\x04@\x04Y\x04f\x04x\x04z\x04|\x04~\x04\x80\x04\x82\x04\x84\x04\x86\x04\x88\x04\x8a\x04\x9c\x04\xa9\x04\xb4\x04\xba\x04\xc8\x04\xcd\x04\xdf\x04\xe2\x05\x1a\x05\x1f\x05$\x05;\x05>\x00\x00\x00\x00\x00\x00\x02\x01\x00\x00\x00\x00\x00\x00\x00\xaf\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05U'  # noqa: E501
REVERSE_GEO_LOC_DATA_2 = b'bplist00\xd4\x01\x02\x03\x04\x05\x06\x07\nX$versionY$archiverT$topX$objects\x12\x00\x01\x86\xa0_\x10\x0fNSKeyedArchiver\xd1\x08\tTroot\x80\x01\xaf\x10+\x0b\x0c!)5?@AHMNOTUZ_`afglmnstuy|\x82\x86\x87\x8b\x8c\x90\x91\x95\xa7\xa8\xa9\xaa\xad\xae\xafU$null\xda\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1a\x1f VisHomeV$class]postalAddress_\x10\x16compoundSecondaryNames[countryCode]addressStringWversion]compoundNames_\x10\x12geoServiceProviderWmapItem\x08\x80*\x80#\x80\x00\x80!\x80(\x10\r\x80\x00\x80)\x80\x02\xd4\x0e"#$%&\'(_\x10\x0ffinalPlaceInfos_\x10\x10sortedPlaceInfos_\x10\x10backupPlaceInfos\x80"\x80\x1b\x80\x03\x80\x1a\xd2*\x0e+4ZNS.objects\xa8,-./0123\x80\x04\x80\x08\x80\x0b\x80\r\x80\x0e\x80\x11\x80\x13\x80\x16\x80\x19\xd56\x0e789:;<=>_\x10\x11dominantOrderTypeTareaTnameYplaceType\x10\x00\x80\x07#\x00\x00\x00\x00\x00\x00\x00\x00\x80\x05\x80\x06_\x10\x153700 Wailea Alanui Dr\x10\x11\xd2BCDEZ$classnameX$classes_\x10"PLRevGeoMapItemAdditionalPlaceInfo\xa2FG_\x10"PLRevGeoMapItemAdditionalPlaceInfoXNSObject\xd56\x0e789:;JKL\x80\x07#Az\xab?`\x00\x00\x00\x80\t\x80\nVWailea\x10\x04\xd56\x0e789:;QRL\x80\x07#A\x97K\xd2\xc0\x00\x00\x00\x80\x0c\x80\nUKihei\xd56\x0e789:;WRL\x80\x07#A\x97\xd0\x14\xc0\x00\x00\x00\x80\x0c\x80\n\xd56\x0e789:;\\]^\x80\x07#A\xdc+\x84\x00\x00\x00\x00\x80\x0f\x80\x10TMaui\x10\x0b\xd56\x0e789:;c]e\x80\x07#A\xf7A\xae@\x00\x00\x00\x80\x0f\x80\x12\x10\x03\xd56\x0e789:;ijk\x80\x07#B\x1a\x97\xca\xe0\x00\x00\x00\x80\x14\x80\x15WHawai\'i\x10\x02\xd56\x0e789:;pqr\x80\x07#B\xa2\xc3\xf5`\x00\x00\x00\x80\x17\x80\x18]United States\x10\x01\xd2BCvw^NSMutableArray\xa3vxGWNSArray\xd2*\x0ez4\xa0\x80\x19\xd2*\x0e}4\xa3~\x7f\x80\x80\x1c\x80\x1e\x80 \x80\x19\xd56\x0e789m;<\x84>\x80\x07\x80\x1d\x80\x06_\x10\x10Wailea Alanui Dr\xd56\x0e789`;<\x89>\x80\x07\x80\x1f\x80\x06RHI\xd56\x0e789\x1d;<\x1b>\x80\x07\x80!\x80\x06RUS\xd2BC\x92\x93_\x10\x0fPLRevGeoMapItem\xa2\x94G_\x10\x0fPLRevGeoMapItem\xd9\x96\x0e\x97\x98\x99\x9a\x9b\x9c\x9d\x89\x9fR\xa1\xa2\xa3]\x1a\x1bV_stateU_cityW_street[_postalCodeX_country_\x10\x16_subAdministrativeArea\\_subLocality_\x10\x0f_ISOCountryCode\x80\x1f\x80\'\x80\x0c\x80$\x80%\x80&\x80\x0f\x80\x00\x80!_\x10\x153700 Wailea Alanui DrU96753]United States\xd2BC\xab\xac_\x10\x0fCNPostalAddress\xa2\xabG_\x1063700 Wailea Alanui Dr, Kihei, HI  96753, United StatesT7618\xd2BC\xb0\xb1_\x10\x14PLRevGeoLocationInfo\xa2\xb2G_\x10\x14PLRevGeoLocationInfo\x00\x08\x00\x11\x00\x1a\x00$\x00)\x002\x007\x00I\x00L\x00Q\x00S\x00\x81\x00\x87\x00\x9c\x00\xa3\x00\xaa\x00\xb8\x00\xd1\x00\xdd\x00\xeb\x00\xf3\x01\x01\x01\x16\x01\x1e\x01\x1f\x01!\x01#\x01%\x01\'\x01)\x01+\x01-\x01/\x011\x01:\x01L\x01_\x01r\x01t\x01v\x01x\x01z\x01\x7f\x01\x8a\x01\x93\x01\x95\x01\x97\x01\x99\x01\x9b\x01\x9d\x01\x9f\x01\xa1\x01\xa3\x01\xa5\x01\xb0\x01\xc4\x01\xc9\x01\xce\x01\xd8\x01\xda\x01\xdc\x01\xe5\x01\xe7\x01\xe9\x02\x01\x02\x03\x02\x08\x02\x13\x02\x1c\x02A\x02D\x02i\x02r\x02}\x02\x7f\x02\x88\x02\x8a\x02\x8c\x02\x93\x02\x95\x02\xa0\x02\xa2\x02\xab\x02\xad\x02\xaf\x02\xb5\x02\xc0\x02\xc2\x02\xcb\x02\xcd\x02\xcf\x02\xda\x02\xdc\x02\xe5\x02\xe7\x02\xe9\x02\xee\x02\xf0\x02\xfb\x02\xfd\x03\x06\x03\x08\x03\n\x03\x0c\x03\x17\x03\x19\x03"\x03$\x03&\x03.\x030\x03;\x03=\x03F\x03H\x03J\x03X\x03Z\x03_\x03n\x03r\x03z\x03\x7f\x03\x80\x03\x82\x03\x87\x03\x8b\x03\x8d\x03\x8f\x03\x91\x03\x93\x03\x9e\x03\xa0\x03\xa2\x03\xa4\x03\xb7\x03\xc2\x03\xc4\x03\xc6\x03\xc8\x03\xcb\x03\xd6\x03\xd8\x03\xda\x03\xdc\x03\xdf\x03\xe4\x03\xf6\x03\xf9\x04\x0b\x04\x1e\x04%\x04+\x043\x04?\x04H\x04a\x04n\x04\x80\x04\x82\x04\x84\x04\x86\x04\x88\x04\x8a\x04\x8c\x04\x8e\x04\x90\x04\x92\x04\xaa\x04\xb0\x04\xbe\x04\xc3\x04\xd5\x04\xd8\x05\x11\x05\x16\x05\x1b\x052\x055\x00\x00\x00\x00\x00\x00\x02\x01\x00\x00\x00\x00\x00\x00\x00\xb3\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05L'  # noqa: E501

# below is just test data, not accurate representation of actual values
PLACE_4_INFO_1 = [
    (5, "St James's Park", 45, 0),
    (4, "Westminster", 16, 22097376),
    (3, "London", 4, 1596146816),
    (2, "England", 2, 180406091776),
    (1, "United Kingdom", 1, 414681432064),
]
PLACE_4_NAMES_1 = [
    "St James's Park",
    "Westminster",
    "London",
    "England",
    "United Kingdom",
]
PLACE_4_COUNTRY_1 = "GB"

PLACE_4_INFO_2 = [
    (957, "Adams Morgan", 43, 1025728.9375),
    (473, "District of Columbia", 2, 177237168),
    (794, "Washington", 16, 177237168),
    (409, "United States", 1, 10316422316032),
]
PLACE_4_NAMES_2 = [
    "Adams Morgan",
    "Washington",
    "District of Columbia",
    "United States",
]
PLACE_4_COUNTRY_2 = "US"


def test_placeInfo4():
    # test valid place data info returns a PlaceInfo object

    place = PlaceInfo4(PLACE_4_INFO_1, PLACE_4_COUNTRY_1)
    assert place is not None
    assert isinstance(place, PlaceInfo)
    assert place.name == "St James's Park, Westminster, United Kingdom"
    assert place.names.city == ["Westminster"]
    assert place.names.country == ["United Kingdom"]
    assert place.names.area_of_interest == ["St James's Park"]
    assert place.names.state_province == ["England"]
    assert place.names.sub_administrative_area == ["London"]
    assert place.names.region == []
    assert place.country_code == "GB"
    assert place.address_str is None
    assert place.address.city is None
    assert place.address.country is None
    assert place.address.postal_code is None
    assert place.address.state_province is None
    assert place.address.street is None
    assert place.address.sub_administrative_area is None
    assert place.address.sub_locality is None


def test_placeInfo4_eq():
    # test __eq__

    place1 = PlaceInfo4(PLACE_4_INFO_1, PLACE_4_COUNTRY_1)
    place2 = PlaceInfo4(PLACE_4_INFO_1, PLACE_4_COUNTRY_1)
    assert place1 == place2


def test_placeInfo4_ne():
    # test __ne__

    place1 = PlaceInfo4(PLACE_4_INFO_1, PLACE_4_COUNTRY_1)
    place2 = PlaceInfo4(PLACE_4_INFO_2, PLACE_4_COUNTRY_2)
    assert place1 != place2


def test_placeInfo4_ne2():
    # test __ne__ unlike objects

    place1 = PlaceInfo4(PLACE_4_INFO_1, PLACE_4_COUNTRY_1)
    place2 = "Foo"
    assert place1 != place2


def test_placeInfo4_ne3():
    # test __ne__ unlike objects

    place1 = PlaceInfo4(PLACE_4_INFO_2, PLACE_4_COUNTRY_2)
    place2 = PlaceInfo5(REVERSE_GEO_LOC_DATA_1)
    assert place1 != place2


def test_PlaceInfo5():
    # test valid place data info returns a PlaceInfo object

    place = PlaceInfo5(REVERSE_GEO_LOC_DATA_1)
    assert place is not None
    assert isinstance(place, PlaceInfo)
    assert not place.ishome
    assert place.name == "Washington, District of Columbia, United States"
    assert place.names.street_address == ["2038 18th St NW"]
    assert place.names.additional_city_info == ["Adams Morgan"]
    assert place.names.city == ["Washington", "Washington", "Washington"]
    assert place.names.state_province == ["District of Columbia"]
    assert place.names.country == ["United States"]
    assert place.country_code == "US"
    assert place.address_str == "2038 18th St NW, Washington, DC  20009, United States"
    assert place.address.city == "Washington"
    assert place.address.country == "United States"
    assert place.address.postal_code == "20009"
    assert place.address.state_province == "DC"
    assert place.address.street == "2038 18th St NW"
    assert place.address.sub_administrative_area is None
    assert place.address.sub_locality == "Adams Morgan"


def test_PlaceInfo5_eq():
    # test __eq__

    place1 = PlaceInfo5(REVERSE_GEO_LOC_DATA_1)
    place2 = PlaceInfo5(REVERSE_GEO_LOC_DATA_1)
    assert place1 == place2


def test_PlaceInfo5_ne():
    # test __ne__

    place1 = PlaceInfo5(REVERSE_GEO_LOC_DATA_1)
    place2 = PlaceInfo5(REVERSE_GEO_LOC_DATA_2)
    assert place1 != place2


def test_PlaceInfo5_ne2():
    # test __ne__ unlike objects

    place1 = PlaceInfo5(REVERSE_GEO_LOC_DATA_1)
    place2 = "Foo"
    assert place1 != place2


def test_PLRevGeoLocationInfo_1():
    # test PLRevGeoLocationInfo class

    place_1 = PlaceInfo5(REVERSE_GEO_LOC_DATA_1)
    plrevgeoloc_1 = place_1._plrevgeoloc
    assert type(plrevgeoloc_1) == PLRevGeoLocationInfo
    assert type(plrevgeoloc_1.postalAddress) == CNPostalAddress
    assert type(plrevgeoloc_1.mapItem) == PLRevGeoMapItem
    assert (
        type(plrevgeoloc_1.mapItem.sortedPlaceInfos[0])
        == PLRevGeoMapItemAdditionalPlaceInfo
    )

    assert (
        plrevgeoloc_1.addressString
        == "2038 18th St NW, Washington, DC  20009, United States"
    )
    assert plrevgeoloc_1.countryCode == "US"
    assert plrevgeoloc_1.version == 13
    assert plrevgeoloc_1.isHome is False
    assert plrevgeoloc_1.compoundNames is None
    assert plrevgeoloc_1.compoundSecondaryNames is None
    assert plrevgeoloc_1.geoServiceProvider == "7618"

    assert plrevgeoloc_1.postalAddress._street == "2038 18th St NW"
    assert plrevgeoloc_1.postalAddress._city == "Washington"
    assert plrevgeoloc_1.postalAddress._state == "DC"
    assert plrevgeoloc_1.postalAddress._ISOCountryCode == "US"

    assert len(plrevgeoloc_1.mapItem.sortedPlaceInfos) == 7
    assert plrevgeoloc_1.mapItem.sortedPlaceInfos[0].placeType == 17
    assert plrevgeoloc_1.mapItem.sortedPlaceInfos[0].name == "2038 18th St NW"
    assert plrevgeoloc_1.mapItem.sortedPlaceInfos[-1].placeType == 1
    assert plrevgeoloc_1.mapItem.sortedPlaceInfos[-1].name == "United States"


def test_PLRevGeoLocationInfo_2():
    # test PLRevGeoLocationInfo class archive/unarchive
    place_1 = PlaceInfo5(REVERSE_GEO_LOC_DATA_1)
    plrevgeoloc_1 = place_1._plrevgeoloc
    archived = archiver.archive(plrevgeoloc_1)
    place_1_unarchived = PlaceInfo5(archived)
    assert isinstance(place_1_unarchived, PlaceInfo)
    assert place_1_unarchived._plrevgeoloc == place_1._plrevgeoloc
