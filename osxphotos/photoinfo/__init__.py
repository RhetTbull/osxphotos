"""
PhotoInfo class
Represents a single photo in the Photos library and provides access to the photo's attributes
PhotosDB.photos() returns a list of PhotoInfo objects
"""

from ._photoinfo_exifinfo import ExifInfo
from ._photoinfo_export import ExportResults
from ._photoinfo_scoreinfo import ScoreInfo
from .photoinfo import PhotoInfo
