""" 
    PlaceInfo class
    Provides reverse geolocation info for photos 
    
    See https://developer.apple.com/documentation/corelocation/clplacemark
    for additional documentation on reverse geolocation data
"""
from abc import ABC, abstractmethod
from collections import namedtuple  # pylint: disable=syntax-error

import yaml
from bpylist import archiver

from ._constants import UNICODE_FORMAT
from .utils import normalize_unicode

# postal address information, returned by PlaceInfo.address
PostalAddress = namedtuple(
    "PostalAddress",
    [
        "street",
        "sub_locality",
        "city",
        "sub_administrative_area",
        "state_province",
        "postal_code",
        "country",
        "iso_country_code",
    ],
)

# PlaceNames tuple returned by PlaceInfo.names
# order of fields 0 - 17 is mapped to placeType value in
# PLRevGeoLocationInfo.mapInfo.sortedPlaceInfos
# field 18 is combined bodies of water (ocean + inland_water)
# and maps to Photos <= 4, RKPlace.type == 44
# (Photos <= 4 doesn't have ocean or inland_water types)
# The fields named "field0", etc. appear to be unused
PlaceNames = namedtuple(
    "PlaceNames",
    [
        "field0",
        "country",  # The name of the country associated with the placemark.
        "state_province",  # administrativeArea, The state or province associated with the placemark.
        "sub_administrative_area",  # Additional administrative area information for the placemark.
        "city",  # locality, The city associated with the placemark.
        "field5",
        "additional_city_info",  # subLocality, Additional city-level information for the placemark.
        "ocean",  # The name of the ocean associated with the placemark.
        "area_of_interest",  # areasOfInterest, The relevant areas of interest associated with the placemark.
        "inland_water",  # The name of the inland water body associated with the placemark.
        "field10",
        "region",  # The geographic region associated with the placemark.
        "sub_throughfare",  # Additional street-level information for the placemark.
        "field13",
        "postal_code",  # The postal code associated with the placemark.
        "field15",
        "field16",
        "street_address",  # throughfare, The street address associated with the placemark.
        "body_of_water",  # RKPlace.type == 44, appears to be any body of water (ocean or inland)
    ],
)

# The following classes represent Photo Library Reverse Geolocation Info as stored
# in ZADDITIONALASSETATTRIBUTES.ZREVERSELOCATIONDATA
# These classes are used by bpylist.archiver to unarchive the serialized objects
class PLRevGeoLocationInfo:
    """ The top level reverse geolocation object """

    def __init__(
        self,
        addressString,
        countryCode,
        mapItem,
        isHome,
        compoundNames,
        compoundSecondaryNames,
        version,
        geoServiceProvider,
        postalAddress,
    ):
        self.addressString = normalize_unicode(addressString)
        self.countryCode = countryCode
        self.mapItem = mapItem
        self.isHome = isHome
        self.compoundNames = normalize_unicode(compoundNames)
        self.compoundSecondaryNames = normalize_unicode(compoundSecondaryNames)
        self.version = version
        self.geoServiceProvider = geoServiceProvider
        self.postalAddress = postalAddress

    def __eq__(self, other):
        return all(
            getattr(self, field) == getattr(other, field)
            for field in [
                "addressString",
                "countryCode",
                "isHome",
                "compoundNames",
                "compoundSecondaryNames",
                "version",
                "geoServiceProvider",
                "postalAddress",
            ]
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return f"addressString: {self.addressString}, countryCode: {self.countryCode}, isHome: {self.isHome}, mapItem: {self.mapItem}, postalAddress: {self.postalAddress}"

    @staticmethod
    def encode_archive(obj, archive):
        archive.encode("addressString", obj.addressString)
        archive.encode("countryCode", obj.countryCode)
        archive.encode("mapItem", obj.mapItem)
        archive.encode("isHome", obj.isHome)
        archive.encode("compoundNames", obj.compoundNames)
        archive.encode("compoundSecondaryNames", obj.compoundSecondaryNames)
        archive.encode("version", obj.version)
        archive.encode("geoServiceProvider", obj.geoServiceProvider)
        archive.encode("postalAddress", obj.postalAddress)

    @staticmethod
    def decode_archive(archive):
        addressString = archive.decode("addressString")
        countryCode = archive.decode("countryCode")
        mapItem = archive.decode("mapItem")
        isHome = archive.decode("isHome")
        compoundNames = archive.decode("compoundNames")
        compoundSecondaryNames = archive.decode("compoundSecondaryNames")
        version = archive.decode("version")
        geoServiceProvider = archive.decode("geoServiceProvider")
        postalAddress = archive.decode("postalAddress")
        return PLRevGeoLocationInfo(
            addressString,
            countryCode,
            mapItem,
            isHome,
            compoundNames,
            compoundSecondaryNames,
            version,
            geoServiceProvider,
            postalAddress,
        )


class PLRevGeoMapItem:
    """ Stores the list of place names, organized by area """

    def __init__(self, sortedPlaceInfos, finalPlaceInfos):
        self.sortedPlaceInfos = sortedPlaceInfos
        self.finalPlaceInfos = finalPlaceInfos

    def __eq__(self, other):
        return all(
            getattr(self, field) == getattr(other, field)
            for field in ["sortedPlaceInfos", "finalPlaceInfos"]
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        sortedPlaceInfos = [str(place) for place in self.sortedPlaceInfos]
        finalPlaceInfos = [str(place) for place in self.finalPlaceInfos]
        return (
            f"finalPlaceInfos: {finalPlaceInfos}, sortedPlaceInfos: {sortedPlaceInfos}"
        )

    @staticmethod
    def encode_archive(obj, archive):
        archive.encode("sortedPlaceInfos", obj.sortedPlaceInfos)
        archive.encode("finalPlaceInfos", obj.finalPlaceInfos)

    @staticmethod
    def decode_archive(archive):
        sortedPlaceInfos = archive.decode("sortedPlaceInfos")
        finalPlaceInfos = archive.decode("finalPlaceInfos")
        return PLRevGeoMapItem(sortedPlaceInfos, finalPlaceInfos)


class PLRevGeoMapItemAdditionalPlaceInfo:
    """ Additional info about individual places """

    def __init__(self, area, name, placeType, dominantOrderType):
        self.area = area
        self.name = normalize_unicode(name)
        self.placeType = placeType
        self.dominantOrderType = dominantOrderType

    def __eq__(self, other):
        return all(
            getattr(self, field) == getattr(other, field)
            for field in ["area", "name", "placeType", "dominantOrderType"]
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return f"area: {self.area}, name: {self.name}, placeType: {self.placeType}"

    @staticmethod
    def encode_archive(obj, archive):
        archive.encode("area", obj.area)
        archive.encode("name", obj.name)
        archive.encode("placeType", obj.placeType)
        archive.encode("dominantOrderType", obj.dominantOrderType)

    @staticmethod
    def decode_archive(archive):
        area = archive.decode("area")
        name = archive.decode("name")
        placeType = archive.decode("placeType")
        dominantOrderType = archive.decode("dominantOrderType")
        return PLRevGeoMapItemAdditionalPlaceInfo(
            area, name, placeType, dominantOrderType
        )


class CNPostalAddress:
    """ postal address for the reverse geolocation info """

    def __init__(
        self,
        _ISOCountryCode,
        _city,
        _country,
        _postalCode,
        _state,
        _street,
        _subAdministrativeArea,
        _subLocality,
    ):
        self._ISOCountryCode = _ISOCountryCode
        self._city = normalize_unicode(_city)
        self._country = normalize_unicode(_country)
        self._postalCode = normalize_unicode(_postalCode)
        self._state = normalize_unicode(_state)
        self._street = normalize_unicode(_street)
        self._subAdministrativeArea = normalize_unicode(_subAdministrativeArea)
        self._subLocality = normalize_unicode(_subLocality)

    def __eq__(self, other):
        return all(
            getattr(self, field) == getattr(other, field)
            for field in [
                "_ISOCountryCode",
                "_city",
                "_country",
                "_postalCode",
                "_state",
                "_street",
                "_subAdministrativeArea",
                "_subLocality",
            ]
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return ", ".join(
            map(
                str,
                [
                    self._street,
                    self._city,
                    self._subLocality,
                    self._subAdministrativeArea,
                    self._state,
                    self._postalCode,
                    self._country,
                    self._ISOCountryCode,
                ],
            )
        )

    @staticmethod
    def encode_archive(obj, archive):
        archive.encode("_ISOCountryCode", obj._ISOCountryCode)
        archive.encode("_country", obj._country)
        archive.encode("_city", obj._city)
        archive.encode("_postalCode", obj._postalCode)
        archive.encode("_state", obj._state)
        archive.encode("_street", obj._street)
        archive.encode("_subAdministrativeArea", obj._subAdministrativeArea)
        archive.encode("_subLocality", obj._subLocality)

    @staticmethod
    def decode_archive(archive):
        _ISOCountryCode = archive.decode("_ISOCountryCode")
        _country = archive.decode("_country")
        _city = archive.decode("_city")
        _postalCode = archive.decode("_postalCode")
        _state = archive.decode("_state")
        _street = archive.decode("_street")
        _subAdministrativeArea = archive.decode("_subAdministrativeArea")
        _subLocality = archive.decode("_subLocality")

        return CNPostalAddress(
            _ISOCountryCode,
            _city,
            _country,
            _postalCode,
            _state,
            _street,
            _subAdministrativeArea,
            _subLocality,
        )


# register the classes with bpylist.archiver
archiver.update_class_map({"CNPostalAddress": CNPostalAddress})
archiver.update_class_map(
    {"PLRevGeoMapItemAdditionalPlaceInfo": PLRevGeoMapItemAdditionalPlaceInfo}
)
archiver.update_class_map({"PLRevGeoMapItem": PLRevGeoMapItem})
archiver.update_class_map({"PLRevGeoLocationInfo": PLRevGeoLocationInfo})


class PlaceInfo(ABC):
    @property
    @abstractmethod
    def address_str(self):
        pass

    @property
    @abstractmethod
    def country_code(self):
        pass

    @property
    @abstractmethod
    def ishome(self):
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def names(self):
        pass

    @property
    @abstractmethod
    def address(self):
        pass


class PlaceInfo4(PlaceInfo):
    """ Reverse geolocation place info for a photo (Photos <= 4) """

    def __init__(self, place_names, country_code):
        """ place_names: list of place name tuples in ascending order by area 
            tuple fields are: modelID, place name, place type, area, e.g.
            [(5, "St James's Park", 45, 0), 
            (4, 'Westminster', 16, 22097376), 
            (3, 'London', 4, 1596146816), 
            (2, 'England', 2, 180406091776), 
            (1, 'United Kingdom', 1, 414681432064)] 
            country_code: two letter country code for the country
        """
        self._place_names = place_names
        self._country_code = country_code
        self._process_place_info()

    @property
    def address_str(self):
        return None

    @property
    def country_code(self):
        return self._country_code

    @property
    def ishome(self):
        return None

    @property
    def name(self):
        return self._name

    @property
    def names(self):
        return self._names

    @property
    def address(self):
        return PostalAddress(None, None, None, None, None, None, None, None)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        else:
            return (
                self._place_names == other._place_names
                and self._country_code == other._country_code
            )

    def _process_place_info(self):
        """ Process place_names to set self._name and self._names """
        places = self._place_names

        # build a dictionary where key is placetype
        places_dict = {}
        for p in places:
            # places in format:
            # [(5, "St James's Park", 45, 0), ]
            #   0: modelID
            #   1: name
            #   2: type
            #   3: area
            try:
                places_dict[p[2]].append((normalize_unicode(p[1]), p[3]))
            except KeyError:
                places_dict[p[2]] = [(normalize_unicode(p[1]), p[3])]

        # build list to populate PlaceNames tuple
        # initialize with empty lists for each field in PlaceNames
        place_info = [[]] * 19

        # add the place names sorted by area (ascending)
        # in Photos <=4, possible place type values are:
        # 45: areasOfInterest (The relevant areas of interest associated with the placemark.)
        # 44: body of water (includes both inlandWater and ocean)
        # 43: subLocality (Additional city-level information for the placemark.
        # 16: locality (The city associated with the placemark.)
        # 4: subAdministrativeArea (Additional administrative area information for the placemark.)
        # 2: administrativeArea (The state or province associated with the placemark.)
        # 1: country
        # mapping = mapping from PlaceNames to field in places_dict
        # PlaceNames fields map to the placeType value in Photos5 (0..17)
        # but place type in Photos <=4 has different values
        # hence (3, 4) means PlaceNames[3] = places_dict[4] (sub_administrative_area)
        mapping = [(1, 1), (2, 2), (3, 4), (4, 16), (18, 44), (8, 45)]
        for field5, field4 in mapping:
            try:
                place_info[field5] = [
                    p[0]
                    for p in sorted(places_dict[field4], key=lambda place: place[1])
                ]
            except KeyError:
                pass

        place_names = PlaceNames(*place_info)
        self._names = place_names

        # build the name as it appears in Photos
        # the length of the name is at most 3 fields and appears to be based on available
        # reverse geolocation data in the following order (left to right, joined by ',')
        # always has country if available then either area of interest and city OR
        # city and state
        # e.g. 4, 2, 1 OR 8, 4, 1
        # 8 (45): area_of_interest
        # 4 (16): locality / city
        # 2 (2): administrative area (state/province)
        # 1 (1): country
        name_list = []
        if place_names[8]:
            name_list.append(place_names[8][0])
            if place_names[4]:
                name_list.append(place_names[4][0])
        elif place_names[4]:
            name_list.append(place_names[4][0])
            if place_names[2]:
                name_list.append(place_names[2][0])
        elif place_names[2]:
            name_list.append(place_names[2][0])

        # add country
        if place_names[1]:
            name_list.append(place_names[1][0])

        name = ", ".join(name_list)
        self._name = name if name != "" else None

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        info = {
            "name": self.name,
            "names": self.names,
            "country_code": self.country_code,
        }
        return "PlaceInfo(" + ", ".join([f"{k}='{v}'" for k, v in info.items()]) + ")"

    def asdict(self):
        return {
            "name": self.name,
            "names": self.names._asdict(),
            "country_code": self.country_code,
        }


class PlaceInfo5(PlaceInfo):
    """ Reverse geolocation place info for a photo (Photos >= 5) """

    def __init__(self, revgeoloc_bplist):
        """ revgeoloc_bplist: a binary plist blob containing 
                a serialized PLRevGeoLocationInfo object """
        self._bplist = revgeoloc_bplist
        self._plrevgeoloc = archiver.unarchive(revgeoloc_bplist)
        self._process_place_info()

    @property
    def address_str(self):
        """ returns the postal address as a string """
        return self._plrevgeoloc.addressString

    @property
    def country_code(self):
        """ returns the country code """
        return self._plrevgeoloc.countryCode

    @property
    def ishome(self):
        """ returns True if place is user's home address """
        return self._plrevgeoloc.isHome

    @property
    def name(self):
        """ returns local place name """
        return self._name

    @property
    def names(self):
        """ returns PlaceNames tuple with detailed reverse geolocation place names """
        return self._names

    @property
    def address(self):
        addr = self._plrevgeoloc.postalAddress
        if addr is not None:
            postal_address = PostalAddress(
                street=addr._street,
                sub_locality=addr._subLocality,
                city=addr._city,
                sub_administrative_area=addr._subAdministrativeArea,
                state_province=addr._state,
                postal_code=addr._postalCode,
                country=addr._country,
                iso_country_code=addr._ISOCountryCode,
            )
        else:
            postal_address = PostalAddress(
                None, None, None, None, None, None, None, None
            )

        return postal_address

    def _process_place_info(self):
        """ Process sortedPlaceInfos to set self._name and self._names """
        places = self._plrevgeoloc.mapItem.sortedPlaceInfos

        # build a dictionary where key is placetype
        places_dict = {}
        for p in places:
            try:
                places_dict[p.placeType].append((p.name, p.area))
            except KeyError:
                places_dict[p.placeType] = [(p.name, p.area)]

        # build list to populate PlaceNames tuple
        place_info = []
        for field in range(18):
            try:
                # add the place names sorted by area (ascending)
                place_info.append(
                    [
                        p[0]
                        for p in sorted(places_dict[field], key=lambda place: place[1])
                    ]
                )
            except:
                place_info.append([])

        # fill in body_of_water for compatibility with Photos <= 4
        place_info.append(place_info[7] + place_info[9])

        place_names = PlaceNames(*place_info)
        self._names = place_names

        # build the name as it appears in Photos
        # the length of the name is variable and appears to be based on available
        # reverse geolocation data in the following order (left to right, joined by ',')
        # 8: area_of_interest
        # 11: region (I've only seen this applied to islands)
        # 4: locality / city
        # 2: administrative area (state/province)
        # 1: country
        # 9: inland_water
        # 7: ocean
        name = ", ".join(
            [
                p[0]
                for p in [
                    place_names[8],  # area of interest
                    place_names[11],  # region (I've only seen this applied to islands)
                    place_names[4],  # locality / city
                    place_names[2],  # administrative area (state/province)
                    place_names[1],  # country
                    place_names[9],  # inland_water
                    place_names[7],  # ocean
                ]
                if p and p[0]
            ]
        )
        self._name = name if name != "" else None

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        else:
            return self._plrevgeoloc == other._plrevgeoloc

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        info = {
            "name": self.name,
            "names": self.names,
            "country_code": self.country_code,
            "ishome": self.ishome,
            "address_str": self.address_str,
            "address": str(self.address),
        }
        return "PlaceInfo(" + ", ".join([f"{k}='{v}'" for k, v in info.items()]) + ")"

    def asdict(self):
        return {
            "name": self.name,
            "names": self.names._asdict(),
            "country_code": self.country_code,
            "ishome": self.ishome,
            "address_str": self.address_str,
            "address": self.address._asdict() if self.address is not None else None,
        }
