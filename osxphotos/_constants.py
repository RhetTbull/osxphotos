"""
Constants used by osxphotos 
"""

import os.path
from datetime import datetime

# Time delta: add this to Photos times to get unix time
# Apple Epoch is Jan 1, 2001
TIME_DELTA = (datetime(2001, 1, 1, 0, 0) - datetime(1970, 1, 1, 0, 0)).total_seconds()

# Unicode format to use for comparing strings
UNICODE_FORMAT = "NFC"

# which Photos library database versions have been tested
# Photos 2.0 (10.12.6) == 2622
# Photos 3.0 (10.13.6) == 3301
# Photos 4.0 (10.14.5) == 4016
# Photos 4.0 (10.14.6) == 4025
# Photos 5.0 (10.15.0) == 6000
_TESTED_DB_VERSIONS = ["6000", "4025", "4016", "3301", "2622"]

# database model versions (applies to Photos 5, Photos 6)
# these come from PLModelVersion key in binary plist in Z_METADATA.Z_PLIST
# Photos 5 (10.15.1) == 13537
# Photos 5 (10.15.4, 10.15.5, 10.15.6) == 13703
# Photos 6 (10.16.0 Beta) == 14104
_TEST_MODEL_VERSIONS = ["13537", "13703", "14104"]

# only version 3 - 4 have RKVersion.selfPortrait
_PHOTOS_3_VERSION = "3301"

# versions 5.0 and later have a different database structure
_PHOTOS_4_VERSION = "4025"  # latest Mojove version on 10.14.6
_PHOTOS_5_VERSION = "6000"  # seems to be current on 10.15.1 through 10.15.6

# Ranges for model version by Photos version
_PHOTOS_5_MODEL_VERSION = [13000, 13999]
_PHOTOS_6_MODEL_VERSION = [14000, 14999]

# some table names differ between Photos 5 and Photos 6
_DB_TABLE_NAMES = {
    5: {
        "ASSET": "ZGENERICASSET",
        "KEYWORD_JOIN": "Z_1KEYWORDS.Z_37KEYWORDS",
        "ALBUM_JOIN": "Z_26ASSETS.Z_34ASSETS",
        "ALBUM_SORT_ORDER": "Z_26ASSETS.Z_FOK_34ASSETS",
        "IMPORT_FOK": "ZGENERICASSET.Z_FOK_IMPORTSESSION",
        "DEPTH_STATE": "ZGENERICASSET.ZDEPTHSTATES",
    },
    6: {
        "ASSET": "ZASSET",
        "KEYWORD_JOIN": "Z_1KEYWORDS.Z_36KEYWORDS",
        "ALBUM_JOIN": "Z_26ASSETS.Z_3ASSETS",
        "ALBUM_SORT_ORDER": "Z_26ASSETS.Z_FOK_3ASSETS",
        "IMPORT_FOK": "null",
        "DEPTH_STATE": "ZASSET.ZDEPTHTYPE",
    },
}

# which major version operating systems have been tested
_TESTED_OS_VERSIONS = ["12", "13", "14", "15", "16"]

# Photos 5 has persons who are empty string if unidentified face
_UNKNOWN_PERSON = "_UNKNOWN_"

# photos with no reverse geolocation info (place)
_UNKNOWN_PLACE = "_UNKNOWN_"

_EXIF_TOOL_URL = "https://exiftool.org/"

# Where are shared iCloud photos located?
_PHOTOS_5_SHARED_PHOTO_PATH = "resources/cloudsharing/data"

# What type of file? Based on ZGENERICASSET.ZKIND in Photos 5 database
_PHOTO_TYPE = 0
_MOVIE_TYPE = 1

# Name of XMP template file
_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
_XMP_TEMPLATE_NAME = "xmp_sidecar.mako"

# Constants used for processing folders and albums
_PHOTOS_5_ALBUM_KIND = 2  # normal user album
_PHOTOS_5_SHARED_ALBUM_KIND = 1505  # shared album
_PHOTOS_5_FOLDER_KIND = 4000  # user folder
_PHOTOS_5_ROOT_FOLDER_KIND = 3999  # root folder
_PHOTOS_5_IMPORT_SESSION_ALBUM_KIND = 1506  # import session

_PHOTOS_4_ALBUM_KIND = 3  # RKAlbum.albumSubclass
_PHOTOS_4_TOP_LEVEL_ALBUM = "TopLevelAlbums"
_PHOTOS_4_ROOT_FOLDER = "LibraryFolder"

# EXIF related constants
# max keyword length for IPTC:Keyword, reference
# https://www.iptc.org/std/photometadata/documentation/userguide/
_MAX_IPTC_KEYWORD_LEN = 64

# Sentinel value for detecting if a template in keyword_template doesn't match
# If anyone has a keyword matching this, then too bad...
_OSXPHOTOS_NONE_SENTINEL = "OSXPhotosXYZZY42_Sentinel$"

# SearchInfo categories for Photos 5, corresponds to categories in database/search/psi.sqlite
SEARCH_CATEGORY_LABEL = 2024

# Max filename length on MacOS
MAX_FILENAME_LEN = 255

# Max directory name length on MacOS
MAX_DIRNAME_LEN = 255

