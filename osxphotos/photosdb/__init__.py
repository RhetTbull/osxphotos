"""
PhotosDB class
Processes a Photos.app library database to extract information about photos
"""

from .photosdb import PhotosDB
from .photosdb_utils import (
    get_db_version,
    get_model_version,
    get_photos_version_from_model,
)
