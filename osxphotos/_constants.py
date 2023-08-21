""" Constants used by osxphotos """

from __future__ import annotations

import logging
import os.path
import sqlite3
from datetime import datetime
from enum import Enum

logger: logging.Logger = logging.getLogger("osxphotos")

APP_NAME = "osxphotos"

OSXPHOTOS_URL = "https://github.com/RhetTbull/osxphotos"

# Time delta: add this to Photos times to get unix time
# Apple Epoch is Jan 1, 2001
TIME_DELTA = (datetime(2001, 1, 1, 0, 0) - datetime(1970, 1, 1, 0, 0)).total_seconds()

# which Photos library database versions have been tested
# Photos 2.0 (10.12.6) == 2622
# Photos 3.0 (10.13.6) == 3301
# Photos 4.0 (10.14.5) == 4016
# Photos 4.0 (10.14.6) == 4025
# Photos 5.0+ (10.15.0) == 6000 or 5001
_TESTED_DB_VERSIONS = ["6000", "5001", "4025", "4016", "3301", "2622"]

# database model versions (applies to Photos 5+)
# these come from PLModelVersion key in binary plist in Z_METADATA.Z_PLIST
# Photos 5 (10.15.1) == 13537
# Photos 5 (10.15.4, 10.15.5, 10.15.6) == 13703
# Photos 6 (10.16.0 Beta) == 14104
# Photos 7 (12.0.1) == 15323
# Photos 8 (13.0.0) == 16320
# Photos 9 (14.0.0 dev preview) = 17120
_TEST_MODEL_VERSIONS = ["13537", "13703", "14104", "15323", "16320", "17120"]

_PHOTOS_2_VERSION = "2622"

# only version 3 - 4 have RKVersion.selfPortrait
_PHOTOS_3_VERSION = "3301"

# versions 5.0 and later have a different database structure
_PHOTOS_4_VERSION = "4025"  # latest Mojave version on 10.14.6
_PHOTOS_5_VERSION = "5000"  # I've seen both 5001 and 6000.  6000 is most common on Catalina and up but there are some version 5001 database in the wild

# Ranges for model version by Photos version
_PHOTOS_5_MODEL_VERSION = [13000, 13999]
_PHOTOS_6_MODEL_VERSION = [14000, 14999]
_PHOTOS_7_MODEL_VERSION = [15000, 15999]  # Dev preview: 15134, 12.1: 15331
_PHOTOS_8_MODEL_VERSION = [16000, 16999]  # Ventura dev preview: 16119
_PHOTOS_9_MODEL_VERSION = [17000, 17999]  # Sonoma dev preview: 17120

# the preview versions of 12.0.0 had a difference schema for syndication info so need to check model version before processing
_PHOTOS_SYNDICATION_MODEL_VERSION = 15323  # 12.0.1

# shared iCloud library versions; dev preview doesn't contain same columns as release version
_PHOTOS_SHARED_LIBRARY_VERSION = 16320  # 13.0

# some table names differ between Photos 5 and later versions
_DB_TABLE_NAMES = {
    5: {
        "ASSET": "ZGENERICASSET",
        "KEYWORD_JOIN": "Z_1KEYWORDS.Z_37KEYWORDS",
        "ALBUM_JOIN": "Z_26ASSETS.Z_34ASSETS",
        "ALBUM_SORT_ORDER": "Z_26ASSETS.Z_FOK_34ASSETS",
        "IMPORT_FOK": "ZGENERICASSET.Z_FOK_IMPORTSESSION",
        "DEPTH_STATE": "ZGENERICASSET.ZDEPTHSTATES",
        "UTI_ORIGINAL": "ZINTERNALRESOURCE.ZUNIFORMTYPEIDENTIFIER",
        "ASSET_ALBUM_JOIN": "Z_26ASSETS.Z_26ALBUMS",
        "ASSET_ALBUM_TABLE": "Z_26ASSETS",
        "HDR_TYPE": "ZCUSTOMRENDEREDVALUE",
        "DETECTED_FACE_PERSON_FK": "ZDETECTEDFACE.ZPERSON",
        "DETECTED_FACE_ASSET_FK": "ZDETECTEDFACE.ZASSET",
    },
    6: {
        "ASSET": "ZASSET",
        "KEYWORD_JOIN": "Z_1KEYWORDS.Z_36KEYWORDS",
        "ALBUM_JOIN": "Z_26ASSETS.Z_3ASSETS",
        "ALBUM_SORT_ORDER": "Z_26ASSETS.Z_FOK_3ASSETS",
        "IMPORT_FOK": "null",
        "DEPTH_STATE": "ZASSET.ZDEPTHTYPE",
        "UTI_ORIGINAL": "ZINTERNALRESOURCE.ZUNIFORMTYPEIDENTIFIER",
        "ASSET_ALBUM_JOIN": "Z_26ASSETS.Z_26ALBUMS",
        "ASSET_ALBUM_TABLE": "Z_26ASSETS",
        "HDR_TYPE": "ZCUSTOMRENDEREDVALUE",
        "DETECTED_FACE_PERSON_FK": "ZDETECTEDFACE.ZPERSON",
        "DETECTED_FACE_ASSET_FK": "ZDETECTEDFACE.ZASSET",
    },
    7: {
        "ASSET": "ZASSET",
        "KEYWORD_JOIN": "Z_1KEYWORDS.Z_38KEYWORDS",
        "ALBUM_JOIN": "Z_27ASSETS.Z_3ASSETS",
        "ALBUM_SORT_ORDER": "Z_27ASSETS.Z_FOK_3ASSETS",
        "IMPORT_FOK": "null",
        "DEPTH_STATE": "ZASSET.ZDEPTHTYPE",
        "UTI_ORIGINAL": "ZINTERNALRESOURCE.ZCOMPACTUTI",
        "ASSET_ALBUM_JOIN": "Z_27ASSETS.Z_27ALBUMS",
        "ASSET_ALBUM_TABLE": "Z_27ASSETS",
        "HDR_TYPE": "ZHDRTYPE",
        "DETECTED_FACE_PERSON_FK": "ZDETECTEDFACE.ZPERSON",
        "DETECTED_FACE_ASSET_FK": "ZDETECTEDFACE.ZASSET",
    },
    8: {
        "ASSET": "ZASSET",
        "KEYWORD_JOIN": "Z_1KEYWORDS.Z_40KEYWORDS",
        "ALBUM_JOIN": "Z_28ASSETS.Z_3ASSETS",
        "ALBUM_SORT_ORDER": "Z_28ASSETS.Z_FOK_3ASSETS",
        "IMPORT_FOK": "null",
        "DEPTH_STATE": "ZASSET.ZDEPTHTYPE",
        "UTI_ORIGINAL": "ZINTERNALRESOURCE.ZCOMPACTUTI",
        "ASSET_ALBUM_JOIN": "Z_28ASSETS.Z_28ALBUMS",
        "ASSET_ALBUM_TABLE": "Z_28ASSETS",
        "HDR_TYPE": "ZHDRTYPE",
        "DETECTED_FACE_PERSON_FK": "ZDETECTEDFACE.ZPERSON",
        "DETECTED_FACE_ASSET_FK": "ZDETECTEDFACE.ZASSET",
    },
    9: {
        "ASSET": "ZASSET",
        "KEYWORD_JOIN": "Z_1KEYWORDS.Z_40KEYWORDS",
        "ALBUM_JOIN": "Z_28ASSETS.Z_3ASSETS",
        "ALBUM_SORT_ORDER": "Z_28ASSETS.Z_FOK_3ASSETS",
        "IMPORT_FOK": "null",
        "DEPTH_STATE": "ZASSET.ZDEPTHTYPE",
        "UTI_ORIGINAL": "ZINTERNALRESOURCE.ZCOMPACTUTI",
        "ASSET_ALBUM_JOIN": "Z_28ASSETS.Z_28ALBUMS",
        "ASSET_ALBUM_TABLE": "Z_28ASSETS",
        "HDR_TYPE": "ZHDRTYPE",
        "DETECTED_FACE_PERSON_FK": "ZDETECTEDFACE.ZPERSONFORFACE",
        "DETECTED_FACE_ASSET_FK": "ZDETECTEDFACE.ZASSETFORFACE",
    },
}

# which version operating systems have been tested
_TESTED_OS_VERSIONS = [
    ("10", "12"),
    ("10", "13"),
    ("10", "14"),
    ("10", "15"),
    ("10", "16"),
    ("11", "0"),
    ("11", "1"),
    ("11", "2"),
    ("11", "3"),
    ("11", "4"),
    ("11", "5"),
    ("11", "6"),
    ("11", "7"),
    ("12", "0"),
    ("12", "1"),
    ("12", "2"),
    ("12", "3"),
    ("12", "4"),
    ("12", "5"),
    ("12", "6"),
    ("13", "0"),
    ("13", "1"),
    ("13", "2"),
    ("13", "3"),
    ("13", "4"),
    ("13", "5"),
    ("14", "0"),
]

# Photos 5 has persons who are empty string if unidentified face
_UNKNOWN_PERSON = "_UNKNOWN_"

# photos with no reverse geolocation info (place)
_UNKNOWN_PLACE = "_UNKNOWN_"

_EXIF_TOOL_URL = "https://exiftool.org/"

# Where are shared iCloud photos located?
_PHOTOS_5_SHARED_PHOTO_PATH = "resources/cloudsharing/data"
_PHOTOS_8_SHARED_PHOTO_PATH = "scopes/cloudsharing/data"

# Where are shared iCloud derivatives located?
_PHOTOS_5_SHARED_DERIVATIVE_PATH = (
    "resources/cloudsharing/resources/derivatives/masters"
)
_PHOTOS_8_SHARED_DERIVATIVE_PATH = "scopes/cloudsharing/resources/derivatives/masters"

# What type of file? Based on ZGENERICASSET.ZKIND in Photos 5 database
_PHOTO_TYPE = 0
_MOVIE_TYPE = 1

# Name of XMP template file
_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
_XMP_TEMPLATE_NAME = "xmp_sidecar.mako"
_XMP_TEMPLATE_NAME_BETA = "xmp_sidecar_beta.mako"

# Constants used for processing folders and albums
_PHOTOS_5_ALBUM_KIND = 2  # normal user album
_PHOTOS_5_SHARED_ALBUM_KIND = 1505  # shared album
_PHOTOS_5_PROJECT_ALBUM_KIND = 1508  # My Projects (e.g. Calendar, Card, Slideshow)
_PHOTOS_5_FOLDER_KIND = 4000  # user folder
_PHOTOS_5_ROOT_FOLDER_KIND = 3999  # root folder
_PHOTOS_5_IMPORT_SESSION_ALBUM_KIND = 1506  # import session

_PHOTOS_4_ALBUM_KIND = 3  # RKAlbum.albumSubclass
_PHOTOS_4_ALBUM_TYPE_ALBUM = 1  # RKAlbum.albumType
_PHOTOS_4_ALBUM_TYPE_PROJECT = 9  # RKAlbum.albumType
_PHOTOS_4_ALBUM_TYPE_SLIDESHOW = 8  # RKAlbum.albumType
_PHOTOS_4_TOP_LEVEL_ALBUMS = [
    "TopLevelAlbums",
    "TopLevelKeepsakes",
    "TopLevelSlideshows",
]
_PHOTOS_4_ROOT_FOLDER = "LibraryFolder"

# EXIF related constants
# max keyword length for IPTC:Keyword, reference
# https://www.iptc.org/std/photometadata/documentation/userguide/
_MAX_IPTC_KEYWORD_LEN = 64

# Sentinel value for detecting if a template in keyword_template doesn't match
# If anyone has a keyword matching this, then too bad...
_OSXPHOTOS_NONE_SENTINEL = "OSXPhotosXYZZY42_Sentinel$"

# Lock file extension for reserving filenames when exporting
_OSXPHOTOS_LOCK_EXTENSION = ".osxphotos.lock"


class SearchCategory:
    """SearchInfo categories for Photos 5+; corresponds to categories in database/search/psi.sqlite:groups.category

    Note: This is a simple enum class; the values are not meant to be changed.
    Would be great if Python enums actually let you access the value directly.
    """

    LABEL = 2024
    PLACE_NAME = 1
    STREET = 2
    NEIGHBORHOOD = 3
    LOCALITY_4 = 4
    SUB_LOCALITY_5 = 5
    SUB_LOCALITY_6 = 6
    CITY = 7
    LOCALITY_8 = 8
    NAMED_AREA = 9
    ALL_LOCALITY = [
        LOCALITY_4,
        SUB_LOCALITY_5,
        SUB_LOCALITY_6,
        LOCALITY_8,
        NAMED_AREA,
    ]
    STATE = 10
    STATE_ABBREVIATION = 11
    COUNTRY = 12
    BODY_OF_WATER = 14
    MONTH = 1014
    YEAR = 1015
    KEYWORDS = 2016
    TITLE = 2017
    DESCRIPTION = 2018
    HOME = 2020
    WORK = 2036
    PERSON = 2021
    ACTIVITY = 2027
    HOLIDAY = 2029
    SEASON = 2030
    VENUE = 2038
    VENUE_TYPE = 2039
    PHOTO_TYPE_VIDEO = 2044
    PHOTO_TYPE_SLOMO = 2045
    PHOTO_TYPE_LIVE = 2046
    PHOTO_TYPE_SCREENSHOT = 2047
    PHOTO_TYPE_PANORAMA = 2048
    PHOTO_TYPE_TIMELAPSE = 2049
    PHOTO_TYPE_BURSTS = 2052
    PHOTO_TYPE_PORTRAIT = 2053
    PHOTO_TYPE_SELFIES = 2054
    PHOTO_TYPE_FAVORITES = 2055
    PHOTO_TYPE_ANIMATED = None  # Photos 8+ only
    MEDIA_TYPES = [
        PHOTO_TYPE_VIDEO,
        PHOTO_TYPE_SLOMO,
        PHOTO_TYPE_LIVE,
        PHOTO_TYPE_SCREENSHOT,
        PHOTO_TYPE_PANORAMA,
        PHOTO_TYPE_TIMELAPSE,
        PHOTO_TYPE_BURSTS,
        PHOTO_TYPE_PORTRAIT,
        PHOTO_TYPE_SELFIES,
        PHOTO_TYPE_FAVORITES,
    ]
    PHOTO_NAME = 2056
    CAMERA = None  # Photos 8+ only
    TEXT_FOUND = None  # Photos 8+ only
    DETECTED_TEXT = None  # Photos 8+ only
    SOURCE = None  # Photos 8+ only

    @classmethod
    def categories(cls) -> dict[int, str]:
        """Return categories as dict of value: name"""
        # a bit of a hack to basically reverse the enum
        return {
            value: name
            for name, value in cls.__dict__.items()
            if name is not None
            and not name.startswith("__")
            and not callable(name)
            and name.isupper()
            and not isinstance(value, (list, dict, tuple))
        }


class SearchCategory_Photos8(SearchCategory):
    """Search categories for Photos 8"""

    # Many of the category values changed in Ventura / Photos 8
    # and some new categories were added
    CITY = 5
    LOCALITY_4 = 4
    SUB_LOCALITY_5 = None
    SUB_LOCALITY_6 = 6
    LOCALITY_8 = 8
    NAMED_AREA = 7
    ALL_LOCALITY = [
        LOCALITY_4,
        SUB_LOCALITY_6,
        LOCALITY_8,
        NAMED_AREA,
    ]
    HOME = 1000
    WORK = 1001
    LABEL = 1500
    MONTH = 1100
    YEAR = 1101
    HOLIDAY = 1103
    SEASON = 1104
    KEYWORDS = 1200
    TITLE = 1201
    DESCRIPTION = 1202
    DETECTED_TEXT = 1203  # new in Photos 8
    TEXT_FOUND = 1205  # new in Photos 8
    PERSON = 1300
    ACTIVITY = 1600
    VENUE = 1700
    VENUE_TYPE = 1701
    PHOTO_TYPE_VIDEO = 1901
    PHOTO_TYPE_SELFIES = 1915
    PHOTO_TYPE_LIVE = 1906
    PHOTO_TYPE_PORTRAIT = 1914
    PHOTO_TYPE_FAVORITES = 2000
    PHOTO_TYPE_PANORAMA = 1908
    PHOTO_TYPE_TIMELAPSE = 1909
    PHOTO_TYPE_SLOMO = 1905
    PHOTO_TYPE_BURSTS = 1913
    PHOTO_TYPE_SCREENSHOT = 1907
    PHOTO_TYPE_ANIMATED = 1912
    PHOTO_TYPE_RAW = 1902
    MEDIA_TYPES = [
        PHOTO_TYPE_VIDEO,
        PHOTO_TYPE_SLOMO,
        PHOTO_TYPE_LIVE,
        PHOTO_TYPE_SCREENSHOT,
        PHOTO_TYPE_PANORAMA,
        PHOTO_TYPE_TIMELAPSE,
        PHOTO_TYPE_BURSTS,
        PHOTO_TYPE_PORTRAIT,
        PHOTO_TYPE_SELFIES,
        PHOTO_TYPE_FAVORITES,
        PHOTO_TYPE_ANIMATED,
    ]
    PHOTO_NAME = 2100
    CAMERA = 2300  # new in Photos 8
    SOURCE = 2200  # new in Photos 8, shows the app/software source for the photo, e.g. Messages, Safari, etc.

    @classmethod
    def categories(cls) -> dict[int, str]:
        """Return categories as dict of value: name"""
        # need to get the categories from the base class and update with the new values
        classdict = SearchCategory.__dict__.copy()
        classdict |= cls.__dict__.copy()
        return {
            value: name
            for name, value in classdict.items()
            if name is not None
            and not name.startswith("__")
            and not callable(name)
            and name.isupper()
            and not isinstance(value, (list, dict, tuple))
        }


def search_category_factory(version: int) -> SearchCategory:
    """Return SearchCategory class for Photos version"""
    return SearchCategory_Photos8 if version >= 8 else SearchCategory


# Max filename length on MacOS
MAX_FILENAME_LEN = 255 - len(_OSXPHOTOS_LOCK_EXTENSION)

# Max directory name length on MacOS
MAX_DIRNAME_LEN = 255

# Default JPEG quality when converting to JPEG
DEFAULT_JPEG_QUALITY = 1.0

# Default suffix to add to edited images
DEFAULT_EDITED_SUFFIX = "_edited"

# Default suffix to add to original images
DEFAULT_ORIGINAL_SUFFIX = ""

# Default suffix to add to preview images
DEFAULT_PREVIEW_SUFFIX = "_preview"

# Bit masks for --sidecar
SIDECAR_JSON = 0x1
SIDECAR_EXIFTOOL = 0x2
SIDECAR_XMP = 0x4

# supported attributes for --xattr-template
EXTENDED_ATTRIBUTE_NAMES = [
    "authors",
    "comment",
    "copyright",
    "creator",
    "description",
    "findercomment",
    "headline",
    "participants",
    "projects",
    "starrating",
    "subject",
    "title",
    "version",
]
EXTENDED_ATTRIBUTE_NAMES_QUOTED = [f"'{x}'" for x in EXTENDED_ATTRIBUTE_NAMES]


# name of export DB
OSXPHOTOS_EXPORT_DB = ".osxphotos_export.db"

# bit flags for burst images ("burstPickType")
BURST_PICK_TYPE_NONE = 0b0  # 0: sometimes used for single images with a burst UUID
BURST_NOT_SELECTED = 0b10  # 2: burst image is not selected
BURST_DEFAULT_PICK = 0b100  # 4: burst image is the one Photos picked to be key image before any selections made
BURST_SELECTED = 0b1000  # 8: burst image is selected
BURST_KEY = 0b10000  # 16: burst image is the key photo (top of burst stack)
BURST_UNKNOWN = 0b100000  # 32: this is almost always set with BURST_DEFAULT_PICK and never if BURST_DEFAULT_PICK is not set.  I think this has something to do with what algorithm Photos used to pick the default image

LIVE_VIDEO_EXTENSIONS = [".mov"]

# categories that --post-command can be used with; these map to ExportResults fields
POST_COMMAND_CATEGORIES = {
    "exported": "All exported files",
    "new": "When used with '--update', all newly exported files",
    "updated": "When used with '--update', all files which were previously exported but updated this time",
    "skipped": "When used with '--update', all files which were skipped (because they were previously exported and didn't change)",
    "missing": "All files which were not exported because they were missing from the Photos library",
    "exif_updated": "When used with '--exiftool', all files on which exiftool updated the metadata",
    "touched": "When used with '--touch-file', all files where the date was touched",
    "converted_to_jpeg": "When used with '--convert-to-jpeg', all files which were converted to jpeg",
    "sidecar_json_written": "When used with '--sidecar json', all JSON sidecar files which were written",
    "sidecar_json_skipped": "When used with '--sidecar json' and '--update', all JSON sidecar files which were skipped",
    "sidecar_exiftool_written": "When used with '--sidecar exiftool', all exiftool sidecar files which were written",
    "sidecar_exiftool_skipped": "When used with '--sidecar exiftool' and '--update, all exiftool sidecar files which were skipped",
    "sidecar_xmp_written": "When used with '--sidecar xmp', all XMP sidecar files which were written",
    "sidecar_xmp_skipped": "When used with '--sidecar xmp' and '--update', all XMP sidecar files which were skipped",
    "error": "All files which produced an error during export",
    # "deleted_files": "When used with '--cleanup', all files deleted during the export",
    # "deleted_directories": "When used with '--cleanup', all directories deleted during the export",
}


class AlbumSortOrder(Enum):
    """Album Sort Order"""

    UNKNOWN = 0
    MANUAL = 1
    NEWEST_FIRST = 2
    OLDEST_FIRST = 3
    TITLE = 5


TEXT_DETECTION_CONFIDENCE_THRESHOLD = 0.75

# stat sort order for cProfile: https://docs.python.org/3/library/profile.html#pstats.Stats.sort_stats
PROFILE_SORT_KEYS = [
    "calls",
    "cumulative",
    "cumtime",
    "file",
    "filename",
    "module",
    "ncalls",
    "pcalls",
    "line",
    "name",
    "nfl",
    "stdname",
    "time",
    "tottime",
]

UUID_PATTERN = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
# Reference: https://docs.python.org/3/library/sqlite3.html?highlight=sqlite3%20threadsafety#sqlite3.threadsafety
# and https://docs.python.org/3/library/sqlite3.html?highlight=sqlite3%20threadsafety#sqlite3.connect
# 3: serialized mode; Threads may share the module, connections and cursors
# 3 is the default in the python.org python 3.11 distribution
# earlier versions of python.org python 3.x default to 1 which means threads may not share
# sqlite3 connections and thus PhotoInfo.export() cannot be used in a multithreaded environment
# pass SQLITE_CHECK_SAME_THREAD to sqlite3.connect() to enable multithreaded access on systems that support it
SQLITE_CHECK_SAME_THREAD = not sqlite3.threadsafety == 3
logger.debug(f"{SQLITE_CHECK_SAME_THREAD=}, {sqlite3.threadsafety=}")
