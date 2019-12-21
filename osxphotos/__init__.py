import logging

from ._version import __version__
from .photoinfo import PhotoInfo
from .photosdb import PhotosDB

# TODO: find edited photos: see https://github.com/orangeturtle739/photos-export/blob/master/extract_photos.py
# TODO: Add test for imageTimeZoneOffsetSeconds = None
# TODO: Fix command line so multiple --keyword, etc. are AND (instead of OR as they are in .photos())
#       Or fix the help text to match behavior
# TODO: Add test for __str__ and to_json
# TODO: fix docstrings
# TODO: Add special albums and magic albums
# TODO: cleanup os.path and pathlib code (import pathlib and also from pathlib import Path)


# set _DEBUG = True to enable debug output
_DEBUG = False

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s",
)

if not _DEBUG:
    logging.disable(logging.DEBUG)


def _debug(debug):
    """ Enable or disable debug logging """
    if debug:
        logging.disable(logging.NOTSET)
    else:
        logging.disable(logging.DEBUG)
