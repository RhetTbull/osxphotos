"""__init__.py for osxphotos"""

from __future__ import annotations

import logging

from ._constants import AlbumSortOrder
from ._version import __version__
from .albuminfo import AlbumInfo, FolderInfo, ImportInfo, ProjectInfo
from .debug import is_debug, set_debug
from .exifinfo import ExifInfo
from .exiftool import ExifTool
from .exifwriter import ExifWriter
from .export_db import ExportDB, ExportDBTemp
from .exportoptions import ExportOptions, ExportResults
from .fileutil import FileUtil, FileUtilNoOp
from .iphoto import (
    iPhotoAlbumInfo,
    iPhotoDB,
    iPhotoFaceInfo,
    iPhotoFolderInfo,
    iPhotoPersonInfo,
    iPhotoPhotoInfo,
)
from .momentinfo import MomentInfo
from .personinfo import FaceInfo, PersonInfo
from .photoexporter import PhotoExporter
from .photoinfo import PhotoInfo
from .photoquery import QueryOptions
from .photosdb import PhotosDB
from .photosdb._photosdb_process_comments import CommentInfo, LikeInfo
from .phototables import PhotoTables
from .phototemplate import PhotoTemplate
from .placeinfo import PlaceInfo
from .platform import is_macos
from .scoreinfo import ScoreInfo
from .searchinfo import SearchInfo
from .sidecars import SidecarWriter

if is_macos:
    from .photosalbum import PhotosAlbum, PhotosAlbumPhotoScript

# configure logging; every module in osxphotos should use this logger
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
    "ExifWriter",
    "ExportDB",
    "ExportDBTemp",
    "ExportOptions",
    "ExportResults",
    "FaceInfo",
    "FileUtil",
    "FileUtilNoOp",
    "FolderInfo",
    "ImportInfo",
    "LikeInfo",
    "MomentInfo",
    "PersonInfo",
    "PhotoExporter",
    "PhotoInfo",
    "PhotoTables",
    "PhotoTemplate",
    "PhotosAlbum",
    "PhotosAlbumPhotoScript",
    "PhotosDB",
    "PlaceInfo",
    "ProjectInfo",
    "QueryOptions",
    "ScoreInfo",
    "SearchInfo",
    "SidecarWriter",
    "__version__",
    "iPhotoAlbumInfo",
    "iPhotoDB",
    "iPhotoFaceInfo",
    "iPhotoFolderInfo",
    "iPhotoPersonInfo",
    "iPhotoPhotoInfo",
    "is_debug",
    "logger",
    "set_debug",
]
