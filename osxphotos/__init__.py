import logging

from ._version import __version__
from .photoinfo import PhotoInfo
from .photosdb import PhotosDB
from .utils import _set_debug, _debug, _get_logger

# TODO: find edited photos: see https://github.com/orangeturtle739/photos-export/blob/master/extract_photos.py
# TODO: Add test for imageTimeZoneOffsetSeconds = None
# TODO: Fix command line so multiple --keyword, etc. are AND (instead of OR as they are in .photos())
#       Or fix the help text to match behavior
# TODO: Add test for __str__ and to_json
# TODO: fix docstrings
# TODO: Add special albums and magic albums
# TODO: cleanup os.path and pathlib code (import pathlib and also from pathlib import Path)

