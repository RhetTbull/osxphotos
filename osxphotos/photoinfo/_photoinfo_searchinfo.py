""" Methods and class for PhotoInfo exposing SearchInfo data such as labels 
    Adds the following properties to PhotoInfo (valid only for Photos 5):
        search_info: returns a SearchInfo object
        search_info_normalized: returns a SearchInfo object with properties that produce normalized results
        labels: returns list of labels
        labels_normalized: returns list of normalized labels
"""

from .._constants import (
    _PHOTOS_4_VERSION,
    SEARCH_CATEGORY_CITY,
    SEARCH_CATEGORY_LABEL,
    SEARCH_CATEGORY_NEIGHBORHOOD,
    SEARCH_CATEGORY_PLACE_NAME,
    SEARCH_CATEGORY_STREET,
    SEARCH_CATEGORY_ALL_LOCALITY,
    SEARCH_CATEGORY_COUNTRY,
    SEARCH_CATEGORY_STATE,
    SEARCH_CATEGORY_STATE_ABBREVIATION,
    SEARCH_CATEGORY_BODY_OF_WATER,
    SEARCH_CATEGORY_MONTH,
    SEARCH_CATEGORY_YEAR,
    SEARCH_CATEGORY_HOLIDAY,
    SEARCH_CATEGORY_ACTIVITY,
    SEARCH_CATEGORY_SEASON,
    SEARCH_CATEGORY_VENUE,
    SEARCH_CATEGORY_VENUE_TYPE,
    SEARCH_CATEGORY_MEDIA_TYPES,
)


@property
def search_info(self):
    """ returns SearchInfo object for photo 
        only valid on Photos 5, on older libraries, returns None
    """
    if self._db._db_version <= _PHOTOS_4_VERSION:
        return None

    # memoize SearchInfo object
    try:
        return self._search_info
    except AttributeError:
        self._search_info = SearchInfo(self)
        return self._search_info


@property
def search_info_normalized(self):
    """ returns SearchInfo object for photo that produces normalized results
        only valid on Photos 5, on older libraries, returns None
    """
    if self._db._db_version <= _PHOTOS_4_VERSION:
        return None

    # memoize SearchInfo object
    try:
        return self._search_info_normalized
    except AttributeError:
        self._search_info_normalized = SearchInfo(self, normalized=True)
        return self._search_info_normalized


@property
def labels(self):
    """ returns list of labels applied to photo by Photos image categorization
        only valid on Photos 5, on older libraries returns empty list 
    """
    if self._db._db_version <= _PHOTOS_4_VERSION:
        return []

    return self.search_info.labels


@property
def labels_normalized(self):
    """ returns normalized list of labels applied to photo by Photos image categorization
        only valid on Photos 5, on older libraries returns empty list 
    """
    if self._db._db_version <= _PHOTOS_4_VERSION:
        return []

    return self.search_info_normalized.labels


class SearchInfo:
    """ Info about search terms such as machine learning labels that Photos knows about a photo """

    def __init__(self, photo, normalized=False):
        """ photo: PhotoInfo object
            normalized: if True, all properties return normalized (lower case) results """

        if photo._db._db_version <= _PHOTOS_4_VERSION:
            raise NotImplementedError(
                f"search info not implemented for this database version"
            )

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
        """ return list of labels associated with Photo """
        return self._get_text_for_category(SEARCH_CATEGORY_LABEL)

    @property
    def place_names(self):
        """ returns list of place names """
        return self._get_text_for_category(SEARCH_CATEGORY_PLACE_NAME)

    @property
    def streets(self):
        """ returns list of street names """
        return self._get_text_for_category(SEARCH_CATEGORY_STREET)

    @property
    def neighborhoods(self):
        """ returns list of neighborhoods """
        return self._get_text_for_category(SEARCH_CATEGORY_NEIGHBORHOOD)

    @property
    def locality_names(self):
        """ returns list of other locality names """
        locality = []
        for category in SEARCH_CATEGORY_ALL_LOCALITY:
            locality += self._get_text_for_category(category)
        return locality

    @property
    def city(self):
        """ returns city/town """
        city = self._get_text_for_category(SEARCH_CATEGORY_CITY)
        return city[0] if city else ""

    @property
    def state(self):
        """ returns state name """
        state = self._get_text_for_category(SEARCH_CATEGORY_STATE)
        return state[0] if state else ""

    @property
    def state_abbreviation(self):
        """ returns state abbreviation """
        abbrev = self._get_text_for_category(SEARCH_CATEGORY_STATE_ABBREVIATION)
        return abbrev[0] if abbrev else ""

    @property
    def country(self):
        """ returns country name """
        country = self._get_text_for_category(SEARCH_CATEGORY_COUNTRY)
        return country[0] if country else ""

    @property
    def month(self):
        """ returns month name """
        month = self._get_text_for_category(SEARCH_CATEGORY_MONTH)
        return month[0] if month else ""

    @property
    def year(self):
        """ returns year """
        year = self._get_text_for_category(SEARCH_CATEGORY_YEAR)
        return year[0] if year else ""

    @property
    def bodies_of_water(self):
        """ returns list of body of water names """
        return self._get_text_for_category(SEARCH_CATEGORY_BODY_OF_WATER)

    @property
    def holidays(self):
        """ returns list of holiday names """
        return self._get_text_for_category(SEARCH_CATEGORY_HOLIDAY)

    @property
    def activities(self):
        """ returns list of activity names """
        return self._get_text_for_category(SEARCH_CATEGORY_ACTIVITY)

    @property
    def season(self):
        """ returns season name """
        season = self._get_text_for_category(SEARCH_CATEGORY_SEASON)
        return season[0] if season else ""

    @property
    def venues(self):
        """ returns list of venue names """
        return self._get_text_for_category(SEARCH_CATEGORY_VENUE)

    @property
    def venue_types(self):
        """ returns list of venue types """
        return self._get_text_for_category(SEARCH_CATEGORY_VENUE_TYPE)

    @property
    def media_types(self):
        """ returns list of media types (photo, video, panorama, etc) """
        types = []
        for category in SEARCH_CATEGORY_MEDIA_TYPES:
            types += self._get_text_for_category(category)
        return types

    @property
    def all(self):
        """ return all search info properties in a single list """
        all = (
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
        )
        if self.city:
            all += [self.city]
        if self.state:
            all += [self.state]
        if self.state_abbreviation:
            all += [self.state_abbreviation]
        if self.country:
            all += [self.country]
        if self.month:
            all += [self.month]
        if self.year:
            all += [self.year]
        if self.season:
            all += [self.season]

        return all

    def asdict(self):
        """ return dict of search info """
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
        }

    def _get_text_for_category(self, category):
        """ return list of text for a specified category ID """
        if self._db_searchinfo:
            content = "normalized_string" if self._normalized else "content_string"
            return [
                rec[content]
                for rec in self._db_searchinfo
                if rec["category"] == category
            ]
        else:
            return []
