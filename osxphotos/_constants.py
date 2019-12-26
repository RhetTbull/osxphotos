"""
Constants used by osxphotos 
"""

# which Photos library database versions have been tested
# Photos 2.0 (10.12.6) == 2622
# Photos 3.0 (10.13.6) == 3301
# Photos 4.0 (10.14.5) == 4016
# Photos 4.0 (10.14.6) == 4025
# Photos 5.0 (10.15.0) == 6000
# TODO: Should this also use compatibleBackToVersion from LiGlobals?
_TESTED_DB_VERSIONS = ["6000", "4025", "4016", "3301", "2622"]

# versions later than this have a different database structure
_PHOTOS_5_VERSION = "6000"

# which major version operating systems have been tested
_TESTED_OS_VERSIONS = ["12", "13", "14", "15"]

# Photos 5 has persons who are empty string if unidentified face
_UNKNOWN_PERSON = "_UNKNOWN_"

_EXIF_TOOL_URL = "https://exiftool.org/"

# Where are shared iCloud photos located?
_PHOTOS_5_SHARED_PHOTO_PATH = "resources/cloudsharing/data"
