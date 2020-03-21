""" 
    PlaceInfo class
    Provides reverse geolocation info for photos 
"""
from abc import ABC, abstractmethod
from collections import namedtuple

from bpylist import archiver

# postal address information, returned by PlaceInfo.address
PostalAddress = namedtuple(
    "PostalAddress",
    [
        "street",
        "sub_locality",
        "city",
        "sub_administrative_area",
        "state",
        "postal_code",
        "country",
        "iso_country_code",
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
        self.addressString = addressString
        self.countryCode = countryCode
        self.mapItem = mapItem
        self.isHome = isHome
        self.compoundNames = compoundNames
        self.compoundSecondaryNames = compoundSecondaryNames
        self.version = version
        self.geoServiceProvider = geoServiceProvider
        self.postalAddress = postalAddress

    def __eq__(self, other):
        for field in [
            "addressString",
            "countryCode",
            "isHome",
            "compoundNames",
            "compoundSecondaryNames",
            "version",
            "geoServiceProvider",
            "postalAddress",
        ]:
            if getattr(self, field) != getattr(other, field):
                return False
        return True

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
        for field in ["sortedPlaceInfos", "finalPlaceInfos"]:
            if getattr(self, field) != getattr(other, field):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        sortedPlaceInfos = []
        finalPlaceInfos = []
        for place in self.sortedPlaceInfos:
            sortedPlaceInfos.append(str(place))
        for place in self.finalPlaceInfos:
            finalPlaceInfos.append(str(place))
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
        self.name = name
        self.placeType = placeType
        self.dominantOrderType = dominantOrderType

    def __eq__(self, other):
        for field in ["area", "name", "placeType", "dominantOrderType"]:
            if getattr(self, field) != getattr(other, field):
                return False
        return True

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
        self._city = _city
        self._country = _country
        self._postalCode = _postalCode
        self._state = _state
        self._street = _street
        self._subAdministrativeArea = _subAdministrativeArea
        self._subLocality = _subLocality

    def __eq__(self, other):
        for field in [
            "_ISOCountryCode",
            "_city",
            "_country",
            "_postalCode",
            "_state",
            "_street",
            "_subAdministrativeArea",
            "_subLocality",
        ]:
            if getattr(self, field) != getattr(other, field):
                return False
        return True

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
        """ place_names: list of place names in ascending order by area """
        self._place_names = place_names
        self._country_code = country_code

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
        return self._place_names[0]

    @property
    def names(self):
        return self._place_names

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

    def __ne__(self, other):
        return not self.__eq__(other)


class PlaceInfo5(PlaceInfo):
    """ Reverse geolocation place info for a photo (Photos >= 5) """

    def __init__(self, revgeoloc_bplist):
        """ revgeoloc_bplist: a binary plist blob containing 
                a serialized PLRevGeoLocationInfo object """
        self._bplist = revgeoloc_bplist
        # todo: check for None?
        self._plrevgeoloc = archiver.unarchive(revgeoloc_bplist)

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
        name = (
            self._plrevgeoloc.mapItem.sortedPlaceInfos[0].name
            if self._plrevgeoloc.mapItem.sortedPlaceInfos
            else None
        )
        return name

    @property
    def names(self):
        """ returns list of all place names in reverse order by area
            e.g. most local is at index 0, least local (usually country) is at index -1 """
        names = []
        # todo: strip duplicates
        for name in self._plrevgeoloc.mapItem.sortedPlaceInfos:
            names.append(name.name)
        return names

    @property
    def address(self):
        addr = self._plrevgeoloc.postalAddress
        address = PostalAddress(
            street=addr._street,
            sub_locality=addr._subLocality,
            city=addr._city,
            sub_administrative_area=addr._subAdministrativeArea,
            state=addr._state,
            postal_code=addr._postalCode,
            country=addr._country,
            iso_country_code=addr._ISOCountryCode,
        )
        return address

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        else:
            return self._plrevgeoloc == other._plrevgeoloc

    def __ne__(self, other):
        return not self.__eq__(other)
