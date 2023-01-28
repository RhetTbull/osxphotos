"""__init__.py for osxphotos"""

from __future__ import annotations

import logging

from ._constants import AlbumSortOrder
from ._version import __version__
from .albuminfo import AlbumInfo, FolderInfo, ImportInfo, ProjectInfo
from .debug import is_debug, set_debug
from .exifinfo import ExifInfo
from .exiftool import ExifTool
from .export_db import ExportDB, ExportDBTemp
from .fileutil import FileUtil, FileUtilNoOp
from .momentinfo import MomentInfo
from .personinfo import PersonInfo
from .photoexporter import ExportOptions, ExportResults, PhotoExporter
from .photoinfo import PhotoInfo
from .photosalbum import PhotosAlbum, PhotosAlbumPhotoScript
from .photosdb import PhotosDB
from .photosdb._photosdb_process_comments import CommentInfo, LikeInfo
from .phototemplate import PhotoTemplate
from .placeinfo import PlaceInfo
from .queryoptions import QueryOptions
from .scoreinfo import ScoreInfo
from .searchinfo import SearchInfo

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s",
)

logger: logging.Logger = logging.getLogger("osxphotos")

if not is_debug():
    logging.disable(logging.DEBUG)

__all__ = [
    "AlbumInfo",
    "AlbumSortOrder",
    "CommentInfo",
    "ExifInfo",
    "ExifTool",
    "ExportDB",
    "ExportDBTemp",
    "ExportOptions",
    "ExportResults",
    "FileUtil",
    "FileUtilNoOp",
    "FolderInfo",
    "ImportInfo",
    "LikeInfo",
    "MomentInfo",
    "PersonInfo",
    "PhotoExporter",
    "PhotoInfo",
    "PhotoTemplate",
    "PhotosAlbum",
    "PhotosAlbumPhotoScript",
    "PhotosDB",
    "PlaceInfo",
    "ProjectInfo",
    "QueryOptions",
    "ScoreInfo",
    "SearchInfo",
    "__version__",
    "is_debug",
    "logger",
    "set_debug",
]
