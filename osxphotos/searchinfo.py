""" class for PhotoInfo exposing SearchInfo data such as labels 
"""

from ._constants import _PHOTOS_4_VERSION, search_category_factory

__all__ = ["SearchInfo"]


class SearchInfo:
    """Info about search terms such as machine learning labels that Photos knows about a photo"""

    def __init__(self, photo, normalized=False):
        """photo: PhotoInfo object
        normalized: if True, all properties return normalized (lower case) results"""

        if photo._db._db_version <= _PHOTOS_4_VERSION:
            raise NotImplementedError(
                "search info not implemented for this database version"
            )

        self._categories = search_category_factory(photo._db._photos_ver)
        self._photo = photo
        self._normalized = normalized
        self.uuid = photo.uuid
        try:
            # get search info for this UUID
            # there might not be any search info data (e.g. if Photo was missing or photoanalysisd not run yet)
            self._db_searchinfo = photo._db._db_searchinfo_uuid[self.uuid]
        except KeyError:
            self._db_searchinfo = None

    @property
    def labels(self):
        """return list of labels associated with Photo"""
        return self._get_text_for_category(self._categories.LABEL)

    @property
    def place_names(self):
        """returns list of place names"""
        return self._get_text_for_category(self._categories.PLACE_NAME)

    @property
    def streets(self):
        """returns list of street names"""
        return self._get_text_for_category(self._categories.STREET)

    @property
    def neighborhoods(self):
        """returns list of neighborhoods"""
        return self._get_text_for_category(self._categories.NEIGHBORHOOD)

    @property
    def locality_names(self):
        """returns list of other locality names"""
        locality = []
        for category in self._categories.ALL_LOCALITY:
            locality += self._get_text_for_category(category)
        return locality

    @property
    def city(self):
        """returns city/town"""
        city = self._get_text_for_category(self._categories.CITY)
        return city[0] if city else ""

    @property
    def state(self):
        """returns state name"""
        state = self._get_text_for_category(self._categories.STATE)
        return state[0] if state else ""

    @property
    def state_abbreviation(self):
        """returns state abbreviation"""
        abbrev = self._get_text_for_category(self._categories.STATE_ABBREVIATION)
        return abbrev[0] if abbrev else ""

    @property
    def country(self):
        """returns country name"""
        country = self._get_text_for_category(self._categories.COUNTRY)
        return country[0] if country else ""

    @property
    def month(self):
        """returns month name"""
        month = self._get_text_for_category(self._categories.MONTH)
        return month[0] if month else ""

    @property
    def year(self):
        """returns year"""
        year = self._get_text_for_category(self._categories.YEAR)
        return year[0] if year else ""

    @property
    def bodies_of_water(self):
        """returns list of body of water names"""
        return self._get_text_for_category(self._categories.BODY_OF_WATER)

    @property
    def holidays(self):
        """returns list of holiday names"""
        return self._get_text_for_category(self._categories.HOLIDAY)

    @property
    def activities(self):
        """returns list of activity names"""
        return self._get_text_for_category(self._categories.ACTIVITY)

    @property
    def season(self):
        """returns season name"""
        season = self._get_text_for_category(self._categories.SEASON)
        return season[0] if season else ""

    @property
    def venues(self):
        """returns list of venue names"""
        return self._get_text_for_category(self._categories.VENUE)

    @property
    def venue_types(self):
        """returns list of venue types"""
        return self._get_text_for_category(self._categories.VENUE_TYPE)

    @property
    def media_types(self):
        """returns list of media types (photo, video, panorama, etc)"""
        types = []
        for category in self._categories.MEDIA_TYPES:
            types += self._get_text_for_category(category)
        return types

    @property
    def detected_text(self):
        """Returns text detected in the photo (macOS 13+ / Photos 8+ only)"""
        if self._photo._db._photos_ver < 8:
            return []
        return self._get_text_for_category(self._categories.DETECTED_TEXT)

    @property
    def text_found(self):
        """Returns True if photos has detected text (macOS 13+ / Photos 8+ only)"""
        if self._photo._db._photos_ver < 8:
            return []
        return self._get_text_for_category(self._categories.TEXT_FOUND)

    @property
    def camera(self):
        """returns camera name (macOS 13+ / Photos 8+ only)"""
        if self._photo._db._photos_ver < 8:
            return ""
        camera = self._get_text_for_category(self._categories.CAMERA)
        return camera[0] if camera else ""

    @property
    def source(self):
        """returns source of the photo (e.g. "Messages", "Safar", etc) (macOS 13+ / Photos 8+ only)"""
        if self._photo._db._photos_ver < 8:
            return ""
        source = self._get_text_for_category(self._categories.SOURCE)
        return source[0] if source else ""

    @property
    def all(self):
        """return all search info properties in a single list"""
        all_ = (
            self.labels
            + self.place_names
            + self.streets
            + self.neighborhoods
            + self.locality_names
            + self.bodies_of_water
            + self.holidays
            + self.activities
            + self.venues
            + self.venue_types
            + self.media_types
            + self.detected_text
        )
        if self.city:
            all_ += [self.city]
        if self.state:
            all_ += [self.state]
        if self.state_abbreviation:
            all_ += [self.state_abbreviation]
        if self.country:
            all_ += [self.country]
        if self.month:
            all_ += [self.month]
        if self.year:
            all_ += [self.year]
        if self.season:
            all_ += [self.season]
        if self.camera:
            all_ += [self.camera]

        return all_

    def asdict(self):
        """return dict of search info"""
        return {
            "labels": self.labels,
            "place_names": self.place_names,
            "streets": self.streets,
            "neighborhoods": self.neighborhoods,
            "city": self.city,
            "locality_names": self.locality_names,
            "state": self.state,
            "state_abbreviation": self.state_abbreviation,
            "country": self.country,
            "bodies_of_water": self.bodies_of_water,
            "month": self.month,
            "year": self.year,
            "holidays": self.holidays,
            "activities": self.activities,
            "season": self.season,
            "venues": self.venues,
            "venue_types": self.venue_types,
            "media_types": self.media_types,
            "detected_text": self.detected_text,
            "camera": self.camera,
            "source": self.source,
        }

    def _get_text_for_category(self, category):
        """return list of text for a specified category ID"""
        if self._db_searchinfo:
            content = "normalized_string" if self._normalized else "content_string"
            return sorted(
                [
                    rec[content]
                    for rec in self._db_searchinfo
                    if rec["category"] == category
                ]
            )
        else:
            return []
