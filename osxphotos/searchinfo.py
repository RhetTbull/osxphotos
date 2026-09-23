"""class for PhotoInfo exposing SearchInfo data such as labels"""

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
    def times_of_day(self):
        """returns list of times of day, e.g. "Morning" (Photos 8+ only)"""
        return self._get_text_for_category(self._categories.TIME_OF_DAY)

    @property
    def week_part(self):
        """returns part of week, "Weekday" or "Weekend" (Photos 8+ only)"""
        return self._get_first_text_for_category(self._categories.WEEKPART)

    @property
    def day_of_week(self):
        """returns day of week, e.g. "Monday" (macOS 27+ only)"""
        return self._get_first_text_for_category(self._categories.DAY_OF_WEEK)

    @property
    def home(self):
        """returns "Home" if photo was taken at the user's home location"""
        return self._get_first_text_for_category(self._categories.HOME)

    @property
    def areas_of_interest(self):
        """returns list of areas of interest, e.g. parks, airports, universities (Photos 8+ only)"""
        return self._get_text_for_category(self._categories.AREA_OF_INTEREST)

    @property
    def country_code(self):
        """returns country code, e.g. "US" (Photos 8+ only)"""
        return self._get_first_text_for_category(self._categories.COUNTRY_CODE)

    @property
    def region(self):
        """returns geographic region, e.g. "Northern America" (Photos 8+ only)"""
        return self._get_first_text_for_category(self._categories.REGION)

    @property
    def continent(self):
        """returns continent, e.g. "Americas" (Photos 8+ only)"""
        return self._get_first_text_for_category(self._categories.CONTINENT)

    @property
    def events(self):
        """returns list of event names, e.g. sporting events or concerts (Photos 8+ only)"""
        return self._get_text_for_category(self._categories.EVENT)

    @property
    def event_performers(self):
        """returns list of event performers or teams (Photos 8+ only)"""
        return self._get_text_for_category(self._categories.EVENT_PERFORMER)

    @property
    def event_types(self):
        """returns list of event types, e.g. "Football", "Music" (Photos 8+ only)"""
        return self._get_text_for_category(self._categories.EVENT_TYPE)

    @property
    def pets(self):
        """returns list of pet names (Photos 8+ only)"""
        return self._get_text_for_category(self._categories.PET)

    @property
    def age_groups(self):
        """returns list of age groups of people in the photo, e.g. "Adult", "Child" (macOS 27+ only)"""
        return self._get_text_for_category(self._categories.AGE_GROUP)

    @property
    def landmarks(self):
        """returns list of landmarks (Photos 8+ only)"""
        return self._get_text_for_category(self._categories.LANDMARK)

    @property
    def sounds(self):
        """returns list of sounds detected in video or Live Photo, e.g. "Laughter" (Photos 8+ only)"""
        return self._get_text_for_category(self._categories.SOUND)

    @property
    def human_actions(self):
        """returns list of human actions, e.g. "Dancing" (Photos 8+ only)"""
        return self._get_text_for_category(self._categories.HUMAN_ACTION)

    @property
    def document_types(self):
        """returns list of document types, e.g. "Receipts", "Handwriting" (Photos 8+ only)"""
        return self._get_text_for_category(self._categories.DOCUMENT_TYPE)

    @property
    def trip(self):
        """returns "Trips" if photo is part of a trip (Photos 8+ only)"""
        return self._get_first_text_for_category(self._categories.TRIP)

    @property
    def photographic_style(self):
        """returns photographic style, e.g. "Standard Style" (macOS 27+ only)"""
        return self._get_first_text_for_category(self._categories.PHOTOGRAPHIC_STYLE)

    @property
    def file_type(self):
        """returns file type description, e.g. "HEIF Image" (macOS 27+ only)"""
        return self._get_first_text_for_category(self._categories.FILE_TYPE)

    @property
    def captured_by_me(self):
        """returns "Captured by Me" if photo was captured by the user (macOS 27+ only)"""
        return self._get_first_text_for_category(self._categories.CAPTURED_BY_ME)

    @property
    def id_document_types(self):
        """returns list of identity document types detected in the photo, e.g. "Passport" (macOS 27+ only)
        Not included in all()"""
        return sorted(
            set(
                self._get_text_for_category(self._categories.ID_DOCUMENT_TYPE)
                + self._get_text_for_category(self._categories.ID_DOCUMENT_CARD_TYPE)
            )
        )

    @property
    def id_document_names(self):
        """returns list of names read from identity documents in the photo (macOS 27+ only)
        Not included in all()"""
        return self._get_text_for_category(self._categories.ID_DOCUMENT_NAME)

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
            + self.times_of_day
            + self.areas_of_interest
            + self.events
            + self.event_performers
            + self.event_types
            + self.pets
            + self.age_groups
            + self.landmarks
            + self.sounds
            + self.human_actions
            + self.document_types
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
        for value in (
            self.week_part,
            self.day_of_week,
            self.home,
            self.country_code,
            self.region,
            self.continent,
            self.trip,
            self.photographic_style,
            self.file_type,
            self.captured_by_me,
        ):
            if value:
                all_.append(value)

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
            "times_of_day": self.times_of_day,
            "week_part": self.week_part,
            "day_of_week": self.day_of_week,
            "home": self.home,
            "areas_of_interest": self.areas_of_interest,
            "country_code": self.country_code,
            "region": self.region,
            "continent": self.continent,
            "events": self.events,
            "event_performers": self.event_performers,
            "event_types": self.event_types,
            "pets": self.pets,
            "age_groups": self.age_groups,
            "landmarks": self.landmarks,
            "sounds": self.sounds,
            "human_actions": self.human_actions,
            "document_types": self.document_types,
            "trip": self.trip,
            "photographic_style": self.photographic_style,
            "file_type": self.file_type,
            "captured_by_me": self.captured_by_me,
            "id_document_types": self.id_document_types,
            "id_document_names": self.id_document_names,
        }

    def _get_first_text_for_category(self, category):
        """return first text value for a specified category ID or "" if none"""
        text = self._get_text_for_category(category)
        return text[0] if text else ""

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
