""" Test the command line interface (CLI) """
import csv
import datetime
import glob
import json
import locale
import os
import os.path
import pathlib
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
from tempfile import TemporaryDirectory

import pytest
from bitmath import contextlib
from click.testing import CliRunner

import osxphotos
from osxphotos._constants import OSXPHOTOS_EXPORT_DB
from osxphotos._version import __version__
from osxphotos.cli import (
    about,
    albums,
    cli_main,
    export,
    exportdb,
    keywords,
    labels,
    persons,
    places,
    query,
)
from osxphotos.exiftool import ExifTool, get_exiftool_path
from osxphotos.fileutil import FileUtil
from osxphotos.platform import is_macos
from osxphotos.unicode import normalize_fs_path, normalize_unicode
from osxphotos.utils import noop

if is_macos:
    from osxmetadata import OSXMetaData, Tag

from .conftest import copy_photos_library_to_path
from .locale_util import setlocale


def _normalize_fs_paths(paths):
    """Small helper to prepare path strings for test"""
    return [normalize_fs_path(p) for p in paths]


CLI_PHOTOS_DB = "tests/Test-10.15.7.photoslibrary"
LIVE_PHOTOS_DB = "tests/Test-Cloud-10.15.1.photoslibrary"
RAW_PHOTOS_DB = "tests/Test-RAW-10.15.1.photoslibrary"
COMMENTS_PHOTOS_DB = "tests/Test-Cloud-10.15.6.photoslibrary"
PLACES_PHOTOS_DB = "tests/Test-Places-Catalina-10_15_1.photoslibrary"
PLACES_PHOTOS_DB_13 = "tests/Test-Places-High-Sierra-10.13.6.photoslibrary"
PHOTOS_DB_15_7 = "tests/Test-10.15.7.photoslibrary"
PHOTOS_DB_TOUCH = PHOTOS_DB_15_7
PHOTOS_DB_14_6 = "tests/Test-10.14.6.photoslibrary"
PHOTOS_DB_MOVIES = "tests/Test-Movie-5_0.photoslibrary"
IPHOTO_LIBRARY = "tests/Test-iPhoto-9.6.1.photolibrary"

# my personal library which some tests require
LOCAL_PHOTOSDB = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")

UUID_SKIP_LIVE_PHOTOKIT = {
    "54A01B04-16D7-4FDE-8860-19F2A641E433": ["IMG_3203_edited.jpeg"],
    "1F3DF341-B822-4531-999E-724D642FD8E7": ["IMG_4179.jpeg"],
}

UUID_DOWNLOAD_MISSING = "C6C712C5-9316-408D-A3C3-125661422DA9"  # IMG_8844.JPG

UUID_FILE = "tests/uuid_from_file.txt"
SKIP_UUID_FILE = "tests/skip_uuid_from_file.txt"

CLI_OUTPUT_QUERY_UUID = '[{"uuid": "D79B8D77-BFFC-460B-9312-034F2877D35B", "filename": "D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg", "original_filename": "Pumkins2.jpg", "date": "2018-09-28T16:07:07-04:00", "description": "Girl holding pumpkin", "title": "I found one!", "keywords": ["Kids"], "albums": ["Pumpkin Farm", "Test Album", "Multi Keyword"], "persons": ["Katie"], "path": "/tests/Test-10.15.7.photoslibrary/originals/D/D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg", "ismissing": false, "hasadjustments": false, "external_edit": false, "favorite": false, "hidden": false, "latitude": 41.256566, "longitude": -95.940257, "path_edited": null, "shared": false, "isphoto": true, "ismovie": false, "uti": "public.jpeg", "burst": false, "live_photo": false, "path_live_photo": null, "iscloudasset": false, "incloud": null}]'  # noqa: E501

CLI_EXPORT_FILENAMES = _normalize_fs_paths(
    [
        "[2020-08-29] AAF035 (1).jpg",
        "[2020-08-29] AAF035 (2).jpg",
        "[2020-08-29] AAF035 (3).jpg",
        "[2020-08-29] AAF035.jpg",
        "DSC03584.dng",
        "Frítest (1).jpg",
        "Frítest (2).jpg",
        "Frítest (3).jpg",
        "Frítest_edited (1).jpeg",
        "Frítest_edited.jpeg",
        "Frítest.jpg",
        "IMG_1693.tif",
        "IMG_1994.cr2",
        "IMG_1994.JPG",
        "IMG_1997.cr2",
        "IMG_1997.JPG",
        "IMG_3092_edited.jpeg",
        "IMG_3092.heic",
        "IMG_4547.jpg",
        "Jellyfish.MOV",
        "Jellyfish1.mp4",
        "Pumkins1.jpg",
        "Pumkins2.jpg",
        "Pumpkins3.jpg",
        "screenshot-really-a-png.jpeg",
        "St James Park_edited.jpeg",
        "St James Park.jpg",
        "Tulips_edited.jpeg",
        "Tulips.jpg",
        "wedding_edited.jpeg",
        "wedding.jpg",
        "winebottle (1).jpeg",
        "winebottle.jpeg",
    ]
)


CLI_EXPORT_FILENAMES_DRY_RUN = _normalize_fs_paths(
    [
        "[2020-08-29] AAF035.jpg",
        "DSC03584.dng",
        "Frítest_edited.jpeg",
        "Frítest.jpg",
        "IMG_1693.tif",
        "IMG_1994.cr2",
        "IMG_1994.JPG",
        "IMG_1997.cr2",
        "IMG_1997.JPG",
        "IMG_3092_edited.jpeg",
        "IMG_3092.heic",
        "IMG_4547.jpg",
        "Jellyfish.MOV",
        "Jellyfish1.mp4",
        "Pumkins1.jpg",
        "Pumkins2.jpg",
        "Pumpkins3.jpg",
        "screenshot-really-a-png.jpeg",
        "St James Park_edited.jpeg",
        "St James Park.jpg",
        "Tulips_edited.jpeg",
        "Tulips.jpg",
        "wedding_edited.jpeg",
        "wedding.jpg",
        "winebottle.jpeg",
        "winebottle.jpeg",
    ]
)

CLI_EXPORT_IGNORE_SIGNATURE_FILENAMES = _normalize_fs_paths(
    ["Tulips.jpg", "wedding.jpg"]
)

CLI_EXPORT_FILENAMES_ALBUM = _normalize_fs_paths(
    ["Pumkins1.jpg", "Pumkins2.jpg", "Pumpkins3.jpg"]
)

CLI_EXPORT_FILENAMES_ALBUM_UNICODE = _normalize_fs_paths(["IMG_4547.jpg"])

CLI_EXPORT_FILENAMES_DELETED_TWIN = _normalize_fs_paths(
    ["wedding.jpg", "wedding_edited.jpeg"]
)

CLI_EXPORT_EDITED_SUFFIX = "_bearbeiten"
CLI_EXPORT_EDITED_SUFFIX_TEMPLATE = "{edited?_edited,}"
CLI_EXPORT_ORIGINAL_SUFFIX = "_original"
CLI_EXPORT_ORIGINAL_SUFFIX_TEMPLATE = "{edited?_original,}"
CLI_EXPORT_PREVIEW_SUFFIX = "_lowres"

CLI_EXPORT_FILENAMES_EDITED_SUFFIX = _normalize_fs_paths(
    [
        "[2020-08-29] AAF035 (1).jpg",
        "[2020-08-29] AAF035 (2).jpg",
        "[2020-08-29] AAF035 (3).jpg",
        "[2020-08-29] AAF035.jpg",
        "DSC03584.dng",
        "Frítest (1).jpg",
        "Frítest (2).jpg",
        "Frítest (3).jpg",
        "Frítest_bearbeiten (1).jpeg",
        "Frítest_bearbeiten.jpeg",
        "Frítest.jpg",
        "IMG_1693.tif",
        "IMG_1994.cr2",
        "IMG_1994.JPG",
        "IMG_1997.cr2",
        "IMG_1997.JPG",
        "IMG_3092_bearbeiten.jpeg",
        "IMG_3092.heic",
        "IMG_4547.jpg",
        "Jellyfish.MOV",
        "Jellyfish1.mp4",
        "Pumkins1.jpg",
        "Pumkins2.jpg",
        "Pumpkins3.jpg",
        "screenshot-really-a-png.jpeg",
        "St James Park_bearbeiten.jpeg",
        "St James Park.jpg",
        "Tulips_bearbeiten.jpeg",
        "Tulips.jpg",
        "wedding_bearbeiten.jpeg",
        "wedding.jpg",
        "winebottle (1).jpeg",
        "winebottle.jpeg",
    ]
)

CLI_EXPORT_FILENAMES_EDITED_SUFFIX_TEMPLATE = _normalize_fs_paths(
    [
        "[2020-08-29] AAF035 (1).jpg",
        "[2020-08-29] AAF035 (2).jpg",
        "[2020-08-29] AAF035 (3).jpg",
        "[2020-08-29] AAF035.jpg",
        "DSC03584.dng",
        "Frítest (1).jpg",
        "Frítest (2).jpg",
        "Frítest (3).jpg",
        "Frítest_edited (1).jpeg",
        "Frítest_edited.jpeg",
        "Frítest.jpg",
        "IMG_1693.tif",
        "IMG_1994.cr2",
        "IMG_1994.JPG",
        "IMG_1997.cr2",
        "IMG_1997.JPG",
        "IMG_3092_edited.jpeg",
        "IMG_3092.heic",
        "IMG_4547.jpg",
        "Jellyfish.MOV",
        "Jellyfish1.mp4",
        "Pumkins1.jpg",
        "Pumkins2.jpg",
        "Pumpkins3.jpg",
        "screenshot-really-a-png.jpeg",
        "St James Park_edited.jpeg",
        "St James Park.jpg",
        "Tulips_edited.jpeg",
        "Tulips.jpg",
        "wedding_edited.jpeg",
        "wedding.jpg",
        "winebottle (1).jpeg",
        "winebottle.jpeg",
    ]
)

CLI_EXPORT_FILENAMES_ORIGINAL_SUFFIX = _normalize_fs_paths(
    [
        "[2020-08-29] AAF035_original (1).jpg",
        "[2020-08-29] AAF035_original (2).jpg",
        "[2020-08-29] AAF035_original (3).jpg",
        "[2020-08-29] AAF035_original.jpg",
        "DSC03584_original.dng",
        "Frítest_edited (1).jpeg",
        "Frítest_edited.jpeg",
        "Frítest_original (1).jpg",
        "Frítest_original (2).jpg",
        "Frítest_original (3).jpg",
        "Frítest_original.jpg",
        "IMG_1693_original.tif",
        "IMG_1994_original.cr2",
        "IMG_1994_original.JPG",
        "IMG_1997_original.cr2",
        "IMG_1997_original.JPG",
        "IMG_3092_edited.jpeg",
        "IMG_3092_original.heic",
        "IMG_4547_original.jpg",
        "Jellyfish_original.MOV",
        "Jellyfish1_original.mp4",
        "Pumkins1_original.jpg",
        "Pumkins2_original.jpg",
        "Pumpkins3_original.jpg",
        "screenshot-really-a-png_original.jpeg",
        "St James Park_edited.jpeg",
        "St James Park_original.jpg",
        "Tulips_edited.jpeg",
        "Tulips_original.jpg",
        "wedding_edited.jpeg",
        "wedding_original.jpg",
        "winebottle_original (1).jpeg",
        "winebottle_original.jpeg",
    ]
)

CLI_EXPORT_FILENAMES_ORIGINAL_SUFFIX_TEMPLATE = _normalize_fs_paths(
    [
        "[2020-08-29] AAF035 (1).jpg",
        "[2020-08-29] AAF035 (2).jpg",
        "[2020-08-29] AAF035 (3).jpg",
        "[2020-08-29] AAF035.jpg",
        "DSC03584.dng",
        "Frítest (1).jpg",
        "Frítest_edited (1).jpeg",
        "Frítest_edited.jpeg",
        "Frítest_original (1).jpg",
        "Frítest_original.jpg",
        "Frítest.jpg",
        "IMG_1693.tif",
        "IMG_1994.cr2",
        "IMG_1994.JPG",
        "IMG_1997.cr2",
        "IMG_1997.JPG",
        "IMG_3092_edited.jpeg",
        "IMG_3092_original.heic",
        "IMG_4547.jpg",
        "Jellyfish.MOV",
        "Jellyfish1.mp4",
        "Pumkins1.jpg",
        "Pumkins2.jpg",
        "Pumpkins3.jpg",
        "screenshot-really-a-png.jpeg",
        "St James Park_edited.jpeg",
        "St James Park_original.jpg",
        "Tulips_edited.jpeg",
        "Tulips_original.jpg",
        "wedding_edited.jpeg",
        "wedding_original.jpg",
        "winebottle (1).jpeg",
        "winebottle.jpeg",
    ]
)

CLI_EXPORT_FILENAMES_CURRENT = [
    "1793FAAB-DE75-4E25-886C-2BD66C780D6A_edited.jpeg",  # Frítest.jpg
    "1793FAAB-DE75-4E25-886C-2BD66C780D6A.jpeg",  # Frítest.jpg
    "1EB2B765-0765-43BA-A90C-0D0580E6172C.jpeg",
    "2DFD33F1-A5D8-486F-A3A9-98C07995535A.jpeg",
    "35329C57-B963-48D6-BB75-6AFF9370CBBC.mov",
    "3DD2C897-F19E-4CA6-8C22-B027D5A71907.jpeg",
    "4D521201-92AC-43E5-8F7C-59BC41C37A96.cr2",
    "4D521201-92AC-43E5-8F7C-59BC41C37A96.jpeg",
    "52083079-73D5-4921-AC1B-FE76F279133F.jpeg",
    "54E76FCB-D353-4557-9997-0A457BCB4D48.jpeg",
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4_edited.jpeg",
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4.jpeg",
    "7783E8E6-9CAC-40F3-BE22-81FB7051C266_edited.jpeg",
    "7783E8E6-9CAC-40F3-BE22-81FB7051C266.heic",
    "7F74DD34-5920-4DA3-B284-479887A34F66.jpeg",
    "7FD37B5F-6FAA-4DB1-8A29-BF9C37E38091.jpeg",
    "8846E3E6-8AC8-4857-8448-E3D025784410.tiff",
    "A8266C97-9BAF-4AF4-99F3-0013832869B8.jpeg",  # Frítest.jpg
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91.cr2",
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91.jpeg",
    "B13F4485-94E0-41CD-AF71-913095D62E31.jpeg",  # Frítest.jpg
    "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068.dng",
    "D1359D09-1373-4F3B-B0E3-1A4DE573E4A3.mp4",
    "D1D4040D-D141-44E8-93EA-E403D9F63E07_edited.jpeg",  # Frítest.jpg
    "D1D4040D-D141-44E8-93EA-E403D9F63E07.jpeg",  # Frítest.jpg
    "D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg",
    "DC99FBDD-7A52-4100-A5BB-344131646C30_edited.jpeg",
    "DC99FBDD-7A52-4100-A5BB-344131646C30.jpeg",
    "E2078879-A29C-4D6F-BACB-E3BBE6C3EB91.jpeg",
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51_edited.jpeg",
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51.jpeg",
    "F12384F6-CD17-4151-ACBA-AE0E3688539E.jpeg",
    "F207D5DE-EFAD-4217-8424-0764AAC971D0.jpeg",
]

CLI_EXPORT_FILENAMES_CONVERT_TO_JPEG = _normalize_fs_paths(
    [
        "[2020-08-29] AAF035 (1).jpg",
        "[2020-08-29] AAF035 (2).jpg",
        "[2020-08-29] AAF035 (3).jpg",
        "[2020-08-29] AAF035.jpg",
        "DSC03584.jpeg",
        "Frítest (1).jpg",
        "Frítest (2).jpg",
        "Frítest (3).jpg",
        "Frítest_edited (1).jpeg",
        "Frítest_edited.jpeg",
        "Frítest.jpg",
        "IMG_1693.jpeg",
        "IMG_1994.cr2",
        "IMG_1994.JPG",
        "IMG_1997.cr2",
        "IMG_1997.JPG",
        "IMG_3092_edited.jpeg",
        "IMG_3092.jpeg",
        "IMG_4547.jpg",
        "Jellyfish.MOV",
        "Jellyfish1.mp4",
        "Pumkins1.jpg",
        "Pumkins2.jpg",
        "Pumpkins3.jpg",
        "screenshot-really-a-png.jpeg",
        "St James Park_edited.jpeg",
        "St James Park.jpg",
        "Tulips_edited.jpeg",
        "Tulips.jpg",
        "wedding_edited.jpeg",
        "wedding.jpg",
        "winebottle (1).jpeg",
        "winebottle.jpeg",
    ]
)

CLI_EXPORT_FILENAMES_CONVERT_TO_JPEG_SKIP_RAW = _normalize_fs_paths(
    [
        "[2020-08-29] AAF035 (1).jpg",
        "[2020-08-29] AAF035 (2).jpg",
        "[2020-08-29] AAF035 (3).jpg",
        "[2020-08-29] AAF035.jpg",
        "DSC03584.jpeg",
        "Frítest (1).jpg",
        "Frítest (2).jpg",
        "Frítest (3).jpg",
        "Frítest_edited (1).jpeg",
        "Frítest_edited.jpeg",
        "Frítest.jpg",
        "IMG_1693.jpeg",
        "IMG_1994.JPG",
        "IMG_1997.JPG",
        "IMG_3092_edited.jpeg",
        "IMG_3092.jpeg",
        "IMG_4547.jpg",
        "Jellyfish.MOV",
        "Jellyfish1.mp4",
        "Pumkins1.jpg",
        "Pumkins2.jpg",
        "Pumpkins3.jpg",
        "screenshot-really-a-png.jpeg",
        "St James Park_edited.jpeg",
        "St James Park.jpg",
        "Tulips_edited.jpeg",
        "Tulips.jpg",
        "wedding_edited.jpeg",
        "wedding.jpg",
        "winebottle (1).jpeg",
        "winebottle.jpeg",
    ]
)

CLI_EXPORT_CONVERT_TO_JPEG_LARGE_FILE = "DSC03584.jpeg"

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES1 = _normalize_fs_paths(
    [
        "2019/April/wedding.jpg",
        "2019/July/Tulips.jpg",
        "2018/October/St James Park.jpg",
        "2018/September/Pumpkins3.jpg",
        "2018/September/Pumkins2.jpg",
        "2018/September/Pumkins1.jpg",
    ]
)

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_LOCALE = _normalize_fs_paths(
    [
        "2019/September/IMG_9975.JPEG",
        "2020/Februar/IMG_1064.JPEG",
        "2016/März/IMG_3984.JPEG",
    ]
)

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_ALBUM1 = _normalize_fs_paths(
    [
        "Multi Keyword/wedding.jpg",
        "_/Tulips.jpg",
        "_/St James Park.jpg",
        "Pumpkin Farm/Pumpkins3.jpg",
        "Pumpkin Farm/Pumkins2.jpg",
        "Pumpkin Farm/Pumkins1.jpg",
        "Test Album/Pumkins1.jpg",
    ]
)

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_ALBUM2 = _normalize_fs_paths(
    [
        "Multi Keyword/wedding.jpg",
        "NOALBUM/Tulips.jpg",
        "NOALBUM/St James Park.jpg",
        "Pumpkin Farm/Pumpkins3.jpg",
        "Pumpkin Farm/Pumkins2.jpg",
        "Pumpkin Farm/Pumkins1.jpg",
        "Test Album/Pumkins1.jpg",
    ]
)

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES2 = _normalize_fs_paths(
    [
        "St James's Park, Great Britain, Westminster, England, United Kingdom/St James Park.jpg",
        "_/Pumpkins3.jpg",
        "Omaha, Nebraska, United States/Pumkins2.jpg",
        "_/Pumkins1.jpg",
        "_/Tulips.jpg",
        "_/wedding.jpg",
    ]
)

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES3 = _normalize_fs_paths(
    [
        "2019/{foo}/wedding.jpg",
        "2019/{foo}/Tulips.jpg",
        "2018/{foo}/St James Park.jpg",
        "2018/{foo}/Pumpkins3.jpg",
        "2018/{foo}/Pumkins2.jpg",
        "2018/{foo}/Pumkins1.jpg",
    ]
)


CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES1 = _normalize_fs_paths(
    [
        "2019-wedding.jpg",
        "2019-wedding_edited.jpeg",
        "2019-Tulips.jpg",
        "2018-St James Park.jpg",
        "2018-St James Park_edited.jpeg",
        "2018-Pumpkins3.jpg",
        "2018-Pumkins2.jpg",
        "2018-Pumkins1.jpg",
    ]
)

CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES2 = _normalize_fs_paths(
    [
        "Folder1_SubFolder2_AlbumInFolder-IMG_4547.jpg",
        "Folder1_SubFolder2_AlbumInFolder-wedding.jpg",
        "Folder1_SubFolder2_AlbumInFolder-wedding_edited.jpeg",
        "Folder2_Raw-DSC03584.dng",
        "Folder2_Raw-IMG_1994.cr2",
        "Folder2_Raw-IMG_1994.JPG",
        "Folder2_Raw-IMG_1997.cr2",
        "Folder2_Raw-IMG_1997.JPG",
        "None-St James Park.jpg",
        "None-St James Park_edited.jpeg",
        "None-Tulips.jpg",
        "None-Tulips_edited.jpeg",
        "Pumpkin Farm-Pumkins1.jpg",
        "Pumpkin Farm-Pumkins2.jpg",
        "Pumpkin Farm-Pumpkins3.jpg",
        "Test Album-Pumkins1.jpg",
        "Test Album-Pumkins2.jpg",
        "None-IMG_1693.tif",
        "I have a deleted twin-wedding.jpg",
        "I have a deleted twin-wedding_edited.jpeg",
    ]
)

CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES_PATHSEP = _normalize_fs_paths(
    [
        "2018-10 - Sponsion, Museum, Frühstück, Römermuseum/IMG_4547.jpg",
        "Folder1/SubFolder2/AlbumInFolder/IMG_4547.jpg",
        "2019-10:11 Paris Clermont/IMG_4547.jpg",
    ]
)


CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES_KEYWORD_PATHSEP = _normalize_fs_paths(
    ["foo:bar/foo:bar_IMG_3092.heic"]
)

CLI_EXPORTED_FILENAME_TEMPLATE_LONG_DESCRIPTION = [
    "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo"
    " ligula eget dolor. Aenean massa. Cum sociis natoque penatibus et magnis "
    "dis parturient montes, nascetu. Donec quam felis, ultricies nec, "
    "pellentesque eu, pretium q.tif"
]

CLI_EXPORT_UUID = "D79B8D77-BFFC-460B-9312-034F2877D35B"  # Pumkins2.jpg
CLI_EXPORT_UUID_STATUE = "3DD2C897-F19E-4CA6-8C22-B027D5A71907"
CLI_EXPORT_UUID_KEYWORD_PATHSEP = "7783E8E6-9CAC-40F3-BE22-81FB7051C266"
CLI_EXPORT_UUID_LONG_DESCRIPTION = "8846E3E6-8AC8-4857-8448-E3D025784410"
CLI_EXPORT_UUID_MISSING = "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A"  # IMG_2000.JPG

CLI_EXPORT_UUID_FILENAME = "Pumkins2.jpg"
CLI_EXPORT_UUID_FILENAME_PREVIEW = "Pumkins2_preview.jpeg"
CLI_EXPORT_UUID_FILENAME_PREVIEW_TEMPLATE = "Pumkins2_lowres.jpeg"

CLI_EXPORT_BY_DATE_TOUCH_UUID = [
    "1EB2B765-0765-43BA-A90C-0D0580E6172C",  # Pumpkins3.jpg
    "F12384F6-CD17-4151-ACBA-AE0E3688539E",  # Pumkins1.jpg
]
CLI_EXPORT_BY_DATE_TOUCH_TIMES = [1538165373, 1538163349]
CLI_EXPORT_BY_DATE_NEED_TOUCH = _normalize_fs_paths(
    [
        "2018/09/28/Pumkins2.jpg",
        "2018/10/13/St James Park.jpg",
    ]
)
CLI_EXPORT_BY_DATE_NEED_TOUCH_UUID = [
    "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "DC99FBDD-7A52-4100-A5BB-344131646C30",
]
CLI_EXPORT_BY_DATE_NEED_TOUCH_TIMES = [1538165227, 1539436692]
CLI_EXPORT_BY_DATE = _normalize_fs_paths(
    [
        "2018/09/28/Pumpkins3.jpg",
        "2018/09/28/Pumkins1.jpg",
    ]
)

CLI_EXPORT_SIDECAR_FILENAMES = _normalize_fs_paths(
    [
        "Pumkins2.jpg",
        "Pumkins2.jpg.json",
        "Pumkins2.jpg.xmp",
    ]
)
CLI_EXPORT_SIDECAR_DROP_EXT_FILENAMES = _normalize_fs_paths(
    [
        "Pumkins2.jpg",
        "Pumkins2.json",
        "Pumkins2.xmp",
    ]
)

CLI_EXPORT_AAE_UUID = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"
CLI_EXPORT_AAE_FILENAMES = [
    "wedding.jpg",
    "wedding.AAE",
    "wedding_edited.jpeg",
]

CLI_EXPORT_LIVE = [
    "51F2BEF7-431A-4D31-8AC1-3284A57826AE.jpeg",
    "51F2BEF7-431A-4D31-8AC1-3284A57826AE.mov",
]

CLI_EXPORT_LIVE_ORIGINAL = _normalize_fs_paths(
    [
        "IMG_0728.JPG",
        "IMG_0728.mov",
    ]
)

CLI_EXPORT_RAW = ["441DFE2A-A69B-4C79-A69B-3F51D1B9B29C.cr2"]
CLI_EXPORT_RAW_ORIGINAL = _normalize_fs_paths(["IMG_0476_2.CR2"])
CLI_EXPORT_RAW_EDITED = [
    "441DFE2A-A69B-4C79-A69B-3F51D1B9B29C.cr2",
    "441DFE2A-A69B-4C79-A69B-3F51D1B9B29C_edited.jpeg",
]
CLI_EXPORT_RAW_EDITED_ORIGINAL = _normalize_fs_paths(
    [
        "IMG_0476_2.CR2",
        "IMG_0476_2_edited.jpeg",
    ]
)

CLI_UUID_DICT_15_7 = {
    "intrash": "71E3E212-00EB-430D-8A63-5E294B268554",
    "template": "F12384F6-CD17-4151-ACBA-AE0E3688539E",
}

CLI_TEMPLATE_SIDECAR_FILENAME = normalize_fs_path("Pumkins1.jpg.json")
CLI_TEMPLATE_FILENAME = normalize_fs_path("Pumkins1.jpg")

CLI_UUID_DICT_14_6 = {"intrash": "3tljdX43R8+k6peNHVrJNQ"}

PHOTOS_NOT_IN_TRASH_LEN_14_6 = 12
PHOTOS_IN_TRASH_LEN_14_6 = 1
PHOTOS_MISSING_14_6 = 1

PHOTOS_NOT_IN_TRASH_LEN_15_7 = 27
PHOTOS_IN_TRASH_LEN_15_7 = 2
PHOTOS_MISSING_15_7 = 2
PHOTOS_EDITED_15_7 = 6
PHOTOS_NOT_MISSING_15_7 = PHOTOS_NOT_IN_TRASH_LEN_15_7 - PHOTOS_MISSING_15_7

CLI_PLACES_JSON = """{"places": {"_UNKNOWN_": 1, "Maui, Wailea, Hawai'i, United States": 1, "Washington, District of Columbia, United States": 1}}"""

CLI_EXIFTOOL = {
    "D79B8D77-BFFC-460B-9312-034F2877D35B": {
        "File:FileName": "Pumkins2.jpg",
        "IPTC:Keywords": "Kids",
        "XMP:TagsList": "Kids",
        "XMP:Title": "I found one!",
        "EXIF:ImageDescription": "Girl holding pumpkin",
        "EXIF:Make": "Canon",
        "XMP:Description": "Girl holding pumpkin",
        "XMP:PersonInImage": "Katie",
        "XMP:Subject": "Kids",
        "EXIF:GPSLatitudeRef": "N",
        "EXIF:GPSLongitudeRef": "W",
        "EXIF:GPSLatitude": 41.256566,
        "EXIF:GPSLongitude": 95.940257,
    }
}

CLI_EXIFTOOL_MERGE = {
    "1EB2B765-0765-43BA-A90C-0D0580E6172C": {
        "File:FileName": "Pumpkins3.jpg",
        "IPTC:Keywords": "Kids",
        "XMP:TagsList": "Kids",
        "EXIF:ImageDescription": "Kids in pumpkin field",
        "XMP:Description": "Kids in pumpkin field",
        "XMP:PersonInImage": ["Katie", "Suzy", "Tim"],
        "XMP:Subject": "Kids",
    },
    "D79B8D77-BFFC-460B-9312-034F2877D35B": {
        "File:FileName": "Pumkins2.jpg",
        "XMP:Title": "I found one!",
        "EXIF:ImageDescription": "Girl holding pumpkin",
        "XMP:Description": "Girl holding pumpkin",
        "XMP:PersonInImage": "Katie",
        "IPTC:Keywords": ["Kids", "keyword1", "keyword2", "subject1", "tagslist1"],
        "XMP:TagsList": ["Kids", "keyword1", "keyword2", "subject1", "tagslist1"],
        "XMP:Subject": ["Kids", "keyword1", "keyword2", "subject1", "tagslist1"],
    },
}


CLI_EXIFTOOL_QUICKTIME = {
    "35329C57-B963-48D6-BB75-6AFF9370CBBC": {
        "File:FileName": "Jellyfish.MOV",
        "XMP:Description": "Jellyfish Video",
        "XMP:Title": "Jellyfish",
        "XMP:TagsList": "Travel",
        "XMP:Subject": "Travel",
        "QuickTime:GPSCoordinates": "34.053345 -118.242349",
        "QuickTime:CreationDate": "2020:01:05 14:13:13-08:00",
        "QuickTime:CreateDate": "2020:01:05 22:13:13",
        "QuickTime:ModifyDate": "2020:01:05 22:13:13",
    },
    "D1359D09-1373-4F3B-B0E3-1A4DE573E4A3": {
        "File:FileName": "Jellyfish1.mp4",
        "XMP:Description": "Jellyfish Video",
        "XMP:Title": "Jellyfish1",
        "XMP:TagsList": "Travel",
        "XMP:Subject": "Travel",
        "QuickTime:GPSCoordinates": "34.053345 -118.242349",
        "QuickTime:CreationDate": "2020:12:04 21:21:52-08:00",
        "QuickTime:CreateDate": "2020:12:05 05:21:52",
        "QuickTime:ModifyDate": "2020:12:05 05:21:52",
    },
}

CLI_EXIFTOOL_IGNORE_DATE_MODIFIED = {
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": {
        "File:FileName": "wedding.jpg",
        "EXIF:ImageDescription": "Bride Wedding day",
        "XMP:Description": "Bride Wedding day",
        "XMP:TagsList": ["Maria", "wedding"],
        "IPTC:Keywords": ["Maria", "wedding"],
        "XMP:PersonInImage": "Maria",
        "XMP:Subject": ["Maria", "wedding"],
        "EXIF:DateTimeOriginal": "2019:04:15 14:40:24",
        "EXIF:CreateDate": "2019:04:15 14:40:24",
        "EXIF:OffsetTimeOriginal": "-04:00",
        "IPTC:DigitalCreationDate": "2019:04:15",
        "IPTC:DateCreated": "2019:04:15",
        "EXIF:ModifyDate": "2019:04:15 14:40:24",
    }
}

CLI_EXIFTOOL_ERROR = ["E2078879-A29C-4D6F-BACB-E3BBE6C3EB91"]

CLI_NOT_REALLY_A_JPEG = "E2078879-A29C-4D6F-BACB-E3BBE6C3EB91"

CLI_EXIFTOOL_DUPLICATE_KEYWORDS = {
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": "wedding.jpg"
}

CLI_FINDER_TAGS = {
    "D79B8D77-BFFC-460B-9312-034F2877D35B": {
        "File:FileName": "Pumkins2.jpg",
        "IPTC:Keywords": "Kids",
        "XMP:TagsList": "Kids",
        "XMP:Title": "I found one!",
        "EXIF:ImageDescription": "Girl holding pumpkin",
        "XMP:Description": "Girl holding pumpkin",
        "XMP:PersonInImage": "Katie",
        "XMP:Subject": "Kids",
    },
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": {
        "File:FileName": "wedding.jpg",
        "IPTC:Keywords": ["Maria", "wedding"],
        "XMP:TagsList": ["Maria", "wedding"],
        "XMP:Title": None,
        "EXIF:ImageDescription": "Bride Wedding day",
        "XMP:Description": "Bride Wedding day",
        "XMP:PersonInImage": "Maria",
        "XMP:Subject": ["Maria", "wedding"],
    },
}

CLI_EXPORT_YEAR_2017 = ["IMG_4547.jpg"]

LABELS_JSON = {
    "labels": {
        "Water": 2,
        "Underwater": 2,
        "Jellyfish": 2,
        "Animal": 2,
        "Wine Bottle": 2,
        "Drink": 2,
        "Wine": 2,
        "Vase": 1,
        "Flower": 1,
        "Plant": 1,
        "Flower Arrangement": 1,
        "Bouquet": 1,
        "Art": 1,
        "Container": 1,
        "Camera": 1,
        "Document": 1,
    }
}

KEYWORDS_JSON = {
    "keywords": {
        "Kids": 4,
        "wedding": 3,
        "Travel": 2,
        "Wine": 2,
        "Val d'Isère": 2,
        "Drink": 2,
        "Wine Bottle": 2,
        "Cloudy": 2,
        "Sky": 2,
        "Cord": 2,
        "Outdoor": 2,
        "Sunset Sunrise": 2,
        "Table": 2,
        "Furniture": 2,
        "Food": 2,
        "Pizza": 2,
        "UK": 1,
        "England": 1,
        "London": 1,
        "United Kingdom": 1,
        "London 2018": 1,
        "St. James's Park": 1,
        "flowers": 1,
        "foo/bar": 1,
        "Maria": 1,
        "Birthday": 0,
        "Digital Nomad": 0,
        "Family": 0,
        "Indoor": 0,
        "Reiseblogger": 0,
        "Stock Photography": 0,
        "Top Shot": 0,
        "Vacation": 0,
        "close up": 0,
        "colorful": 0,
        "design": 0,
        "display": 0,
        "fake": 0,
        "flower": 0,
        "kids": 0,
        "outdoor": 0,
        "photography": 0,
        "plastic": 0,
        "raw-only": 0,
        "stock photo": 0,
        "vibrant": 0,
        "we": 0,
    }
}

ALBUMS_JSON = {
    "albums": {
        "Raw": 4,
        "Pumpkin Farm": 3,
        "Test Album": 2,
        "AlbumInFolder": 2,
        "Multi Keyword": 2,
        "I have a deleted twin": 1,
        "2018-10 - Sponsion, Museum, Frühstück, Römermuseum": 1,
        "2019-10/11 Paris Clermont": 1,
        "EmptyAlbum": 0,
        "Sorted Manual": 3,
        "Sorted Newest First": 3,
        "Sorted Oldest First": 3,
        "Sorted Title": 3,
        "Água": 3,
    },
    "shared albums": {},
}

ALBUMS_STR = """albums:
  Raw: 4
  Pumpkin Farm: 3
  Test Album: 2
  AlbumInFolder: 2
  Multi Keyword: 2
  I have a deleted twin: 1
  2018-10 - Sponsion, Museum, Frühstück, Römermuseum: 1
  2019-10/11 Paris Clermont: 1
  EmptyAlbum: 0
  Água: 3
shared albums: {}
"""

PERSONS_JSON = {"persons": {"Katie": 3, "Suzy": 2, "_UNKNOWN_": 1, "Maria": 2}}

UUID_EXPECTED_FROM_FILE = [
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91",
]

UUID_NOT_FROM_FILE = "D79B8D77-BFFC-460B-9312-034F2877D35B"

CLI_EXPORT_UUID_FROM_FILE_FILENAMES = [
    "IMG_1994.JPG",
    "IMG_1994.cr2",
    "Tulips.jpg",
    "Tulips_edited.jpeg",
    "wedding.jpg",
    "wedding_edited.jpeg",
]

CLI_EXPORT_SKIP_UUID = [
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
]
CLI_EXPORT_SKIP_UUID_FILENAMES = [
    "Tulips.jpg",
    "Tulips_edited.jpeg",
    "wedding.jpg",
    "wedding_edited.jpeg",
]

UUID_HAS_COMMENTS = [
    "4E4944A0-3E5C-4028-9600-A8709F2FA1DB",
    "4AD7C8EF-2991-4519-9D3A-7F44A6F031BE",
    "7572C53E-1D6A-410C-A2B1-18CCA3B5AD9F",
]
UUID_NO_COMMENTS = ["4F835581-5AB9-4DEC-9971-3E64A0894B04"]
UUID_HAS_LIKES = [
    "C008048F-8767-4992-85B8-13E798F6DC3C",
    "65BADBD7-A50C-4956-96BA-1BB61155DA17",
    "4AD7C8EF-2991-4519-9D3A-7F44A6F031BE",
]
UUID_NO_LIKES = [
    "45099D34-A414-464F-94A2-60D6823679C8",
    "1C1C8F1F-826B-4A24-B1CB-56628946A834",
]

UUID_JPEGS_DICT = {
    "4D521201-92AC-43E5-8F7C-59BC41C37A96": ["IMG_1997", "JPG"],
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": ["wedding", "jpg"],
    "E2078879-A29C-4D6F-BACB-E3BBE6C3EB91": ["screenshot-really-a-png", "jpeg"],
}


UUID_JPEGS_DICT_NOT_JPEG = {
    "7783E8E6-9CAC-40F3-BE22-81FB7051C266": ["IMG_3092", "heic"],
    "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068": ["DSC03584", "dng"],
    "8846E3E6-8AC8-4857-8448-E3D025784410": ["IMG_1693", "tif"],
}

UUID_MOVIES_NOT_JPEGS_DICT = {
    "423C0683-672D-4DDD-979C-23A6A53D7256": ["IMG_0670B_NOGPS", "MOV"]
}

UUID_HEIC = {"7783E8E6-9CAC-40F3-BE22-81FB7051C266": "IMG_3092"}

UUID_IS_REFERENCE = [
    "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A",
    "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
]

UUID_EDITED = [
    "D1D4040D-D141-44E8-93EA-E403D9F63E07",
    "7783E8E6-9CAC-40F3-BE22-81FB7051C266",
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "1793FAAB-DE75-4E25-886C-2BD66C780D6A",
    "DC99FBDD-7A52-4100-A5BB-344131646C30",
]

UUID_NOT_EDITED = [
    "F12384F6-CD17-4151-ACBA-AE0E3688539E",
    "7F74DD34-5920-4DA3-B284-479887A34F66",
    "4D521201-92AC-43E5-8F7C-59BC41C37A96",
    "54E76FCB-D353-4557-9997-0A457BCB4D48",
    "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A",
    "F207D5DE-EFAD-4217-8424-0764AAC971D0",
    "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068",
    "52083079-73D5-4921-AC1B-FE76F279133F",
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91",
    "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
    "7FD37B5F-6FAA-4DB1-8A29-BF9C37E38091",
    "B13F4485-94E0-41CD-AF71-913095D62E31",
    "A8266C97-9BAF-4AF4-99F3-0013832869B8",
    "1EB2B765-0765-43BA-A90C-0D0580E6172C",
    "E2078879-A29C-4D6F-BACB-E3BBE6C3EB91",
    "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "8846E3E6-8AC8-4857-8448-E3D025784410",
    "D1359D09-1373-4F3B-B0E3-1A4DE573E4A3",
    "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "35329C57-B963-48D6-BB75-6AFF9370CBBC",
    "2DFD33F1-A5D8-486F-A3A9-98C07995535A",
]

UUID_IN_ALBUM = [
    "1EB2B765-0765-43BA-A90C-0D0580E6172C",
    "2DFD33F1-A5D8-486F-A3A9-98C07995535A",
    "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
    "4D521201-92AC-43E5-8F7C-59BC41C37A96",
    "54E76FCB-D353-4557-9997-0A457BCB4D48",
    "7783E8E6-9CAC-40F3-BE22-81FB7051C266",
    "7FD37B5F-6FAA-4DB1-8A29-BF9C37E38091",
    "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A",
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91",
    "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068",
    "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "F12384F6-CD17-4151-ACBA-AE0E3688539E",
]

UUID_NOT_IN_ALBUM = [
    "1793FAAB-DE75-4E25-886C-2BD66C780D6A",  # Frítest.jpg
    "35329C57-B963-48D6-BB75-6AFF9370CBBC",
    "52083079-73D5-4921-AC1B-FE76F279133F",
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "7F74DD34-5920-4DA3-B284-479887A34F66",
    "8846E3E6-8AC8-4857-8448-E3D025784410",
    "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "A8266C97-9BAF-4AF4-99F3-0013832869B8",  # Frítest.jpg
    "B13F4485-94E0-41CD-AF71-913095D62E31",  # Frítest.jpg
    "D1359D09-1373-4F3B-B0E3-1A4DE573E4A3",
    "D1D4040D-D141-44E8-93EA-E403D9F63E07",  # Frítest.jpg
    "DC99FBDD-7A52-4100-A5BB-344131646C30",
    "E2078879-A29C-4D6F-BACB-E3BBE6C3EB91",
    "F207D5DE-EFAD-4217-8424-0764AAC971D0",
]

UUID_DUPLICATES = [
    "2DFD33F1-A5D8-486F-A3A9-98C07995535A",
    "52083079-73D5-4921-AC1B-FE76F279133F",
    "54E76FCB-D353-4557-9997-0A457BCB4D48",
    "7F74DD34-5920-4DA3-B284-479887A34F66",
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91",
    "F207D5DE-EFAD-4217-8424-0764AAC971D0",
]

UUID_LOCATION = "D79B8D77-BFFC-460B-9312-034F2877D35B"  # Pumkins2.jpg
UUID_NO_LOCATION = "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4"  # Tulips.jpg"

UUID_DICT_MISSING = {
    "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A": "IMG_2000.jpeg",  # missing
    "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C": "Pumpkins4.jpeg",  # missing
    "D79B8D77-BFFC-460B-9312-034F2877D35B": "Pumkins2.jpg",  # not missing
}

UUID_DICT_FOLDER_ALBUM_SEQ = {
    "7783E8E6-9CAC-40F3-BE22-81FB7051C266": {
        "directory": "{folder_album}",
        "album": "Sorted Oldest First",
        "filename": "{album?{folder_album_seq.1}_,}{original_name}",
        "result": "3_IMG_3092.heic",
    },
    "3DD2C897-F19E-4CA6-8C22-B027D5A71907": {
        "directory": "{album}",
        "album": "Sorted Oldest First",
        "filename": "{album?{album_seq}_,}{original_name}",
        "result": "0_IMG_4547.jpg",
    },
}

UUID_EMPTY_TITLE = "7783E8E6-9CAC-40F3-BE22-81FB7051C266"  # IMG_3092.heic
FILENAME_EMPTY_TITLE = "IMG_3092.heic"
DESCRIPTION_TEMPLATE_EMPTY_TITLE = "{title,No Title} and {descr,No Descr}"
DESCRIPTION_VALUE_EMPTY_TITLE = "No Title and No Descr"
DESCRIPTION_TEMPLATE_TITLE_CONDITIONAL = "{title?true,false}"
DESCRIPTION_VALUE_TITLE_CONDITIONAL = "false"


UUID_UNICODE_TITLE = [
    "B13F4485-94E0-41CD-AF71-913095D62E31",  # Frítest.jpg
    "1793FAAB-DE75-4E25-886C-2BD66C780D6A",  # Frítest.jpg
    "A8266C97-9BAF-4AF4-99F3-0013832869B8",  # Frítest.jpg
    "D1D4040D-D141-44E8-93EA-E403D9F63E07",  # Frítest.jpg
]

EXPORT_UNICODE_TITLE_FILENAMES = _normalize_fs_paths(
    [
        "Frítest.jpg",
        "Frítest (1).jpg",
        "Frítest (2).jpg",
        "Frítest (3).jpg",
    ]
)

# data for --report
UUID_REPORT = [
    {
        "uuid": "4D521201-92AC-43E5-8F7C-59BC41C37A96",
        "filenames": ["IMG_1997.JPG", "IMG_1997.cr2"],
    },
    {
        "uuid": "7783E8E6-9CAC-40F3-BE22-81FB7051C266",
        "filenames": ["IMG_3092.heic", "IMG_3092_edited.jpeg"],
    },
]

# data for --exif
QUERY_EXIF_DATA = [("EXIF:Make", "FUJIFILM", ["6191423D-8DB8-4D4C-92BE-9BBBA308AAC4"])]
QUERY_EXIF_DATA_CASE_INSENSITIVE = [
    ("Make", "Fujifilm", ["6191423D-8DB8-4D4C-92BE-9BBBA308AAC4"])
]
EXPORT_EXIF_DATA = [("EXIF:Make", "FUJIFILM", ["Tulips.jpg", "Tulips_edited.jpeg"])]

UUID_LIVE_EDITED = "136A78FA-1B90-46CC-88A7-CCA3331F0353"  # IMG_4813.HEIC
CLI_EXPORT_LIVE_EDITED = _normalize_fs_paths(
    [
        "IMG_4813.HEIC",
        "IMG_4813.mov",
        "IMG_4813_edited.jpeg",
        "IMG_4813_edited.mov",
    ]
)

UUID_FAVORITE = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"
FILE_FAVORITE = "wedding.jpg"
UUID_NOT_FAVORITE = "1EB2B765-0765-43BA-A90C-0D0580E6172C"
FILE_NOT_FAVORITE = "Pumpkins3.jpg"

# number of photos in test library with Make=Canon
EXIF_MAKE_CANON = 7


@pytest.fixture(scope="module")
def local_photosdb():
    """Return a PhotosDB object for the local Photos library"""
    if "OSXPHOTOS_TEST_EXPORT_V2" not in os.environ:
        pytest.skip("OSXPHOTOS_TEST_EXPORT_V2 not set")
    return osxphotos.PhotosDB(dbfile=LOCAL_PHOTOSDB)


def modify_file(filename):
    """appends data to a file to modify it"""
    with open(filename, "ab") as fd:
        fd.write(b"foo")


@pytest.fixture(autouse=True)
def reset_globals():
    """reset globals in cli that tests may have changed"""
    yield
    osxphotos.cli.VERBOSE = False


# determine if exiftool installed so exiftool tests can be skipped
try:
    exiftool = get_exiftool_path()
except:
    exiftool = None


def touch_all_photos_in_db(dbpath):
    """touch date on all photos in a library
        helper function for --touch-file tests

    Args:
        dbpath: path to photos library to touch
    """
    ts = int(time.time())
    for photo in osxphotos.PhotosDB(dbpath).photos():
        if photo.path is not None:
            os.utime(photo.path, (ts, ts))
        if photo.path_edited is not None:
            os.utime(photo.path_edited, (ts, ts))
        if photo.path_raw is not None:
            os.utime(photo.path_raw, (ts, ts))
        if photo.path_live_photo is not None:
            os.utime(photo.path_live_photo, (ts, ts))


def setup_touch_tests():
    """perform setup needed for --touch-file tests"""

    # touch all photos so they do not match PhotoInfo.date
    touch_all_photos_in_db(PHOTOS_DB_TOUCH)

    # adjust a couple of the photos so they're file times *are* correct
    photos = osxphotos.PhotosDB(PHOTOS_DB_TOUCH).photos_by_uuid(
        CLI_EXPORT_BY_DATE_TOUCH_UUID
    )
    for photo in photos:
        ts = int(photo.date.timestamp())
        if photo.path is not None:
            os.utime(photo.path, (ts, ts))
        if photo.path_edited is not None:
            os.utime(photo.path_edited, (ts, ts))
        if photo.path_raw is not None:
            os.utime(photo.path_raw, (ts, ts))
        if photo.path_live_photo is not None:
            os.utime(photo.path_live_photo, (ts, ts))


def test_osxphotos():
    runner = CliRunner()
    result = runner.invoke(cli_main, [])

    assert result.exit_code == 0
    assert "Print information about osxphotos" in result.output


def test_osxphotos_help_1():
    # test help command no topic

    runner = CliRunner()
    result = runner.invoke(cli_main, ["help"])
    assert result.exit_code == 0
    assert "Print information about osxphotos" in result.output


def test_osxphotos_help_2():
    # test help command valid topic

    runner = CliRunner()
    result = runner.invoke(cli_main, ["help", "persons"])
    assert result.exit_code == 0
    assert "Print out persons (faces) found in the Photos library." in result.output


def test_osxphotos_help_3():
    # test help command invalid topic

    runner = CliRunner()
    result = runner.invoke(cli_main, ["help", "foo"])
    assert result.exit_code == 0
    assert "Invalid command: foo" in result.output


def test_about():
    """Test about"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(about, [])
    assert result.exit_code == 0
    assert "MIT License" in result.output


def test_query_uuid():
    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--uuid",
            "D79B8D77-BFFC-460B-9312-034F2877D35B",
        ],
    )
    assert result.exit_code == 0

    json_expected = json.loads(CLI_OUTPUT_QUERY_UUID)[0]
    json_got = json.loads(result.output)[0]

    assert list(json_expected.keys()).sort() == list(json_got.keys()).sort()

    # check values expected vs got
    # path needs special handling as path is set to full path which will differ system to system
    for key_ in json_expected:
        assert key_ in json_got
        if key_ != "path":
            if isinstance(json_expected[key_], list):
                assert sorted(json_expected[key_]) == sorted(json_got[key_])
            else:
                assert json_expected[key_] == json_got[key_]
        else:
            assert json_expected[key_] in json_got[key_]


def test_query_uuid_from_file_1():
    """Test query with --uuid-from-file"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--uuid-from-file",
            UUID_FILE,
        ],
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(UUID_EXPECTED_FROM_FILE) == sorted(uuid_got)


def test_query_uuid_from_file_stdin():
    """Test query with --uuid-from-file reading from stdin"""

    runner = CliRunner()
    cwd = os.getcwd()
    input_text = open(UUID_FILE, "r").read()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--uuid-from-file", "-"],
        input=input_text,
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(UUID_EXPECTED_FROM_FILE) == sorted(uuid_got)


def test_query_has_comment():
    """Test query with --has-comment"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, COMMENTS_PHOTOS_DB), "--has-comment"],
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(uuid_got) == sorted(UUID_HAS_COMMENTS)


def test_query_no_comment():
    """Test query with --no-comment"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, COMMENTS_PHOTOS_DB), "--no-comment"]
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    for uuid in UUID_NO_COMMENTS:
        assert uuid in uuid_got
    for uuid in uuid_got:
        assert uuid not in UUID_HAS_COMMENTS


def test_query_has_likes():
    """Test query with --has-likes"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, COMMENTS_PHOTOS_DB), "--has-likes"]
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(uuid_got) == sorted(UUID_HAS_LIKES)


def test_query_no_likes():
    """Test query with --no-likes"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, COMMENTS_PHOTOS_DB), "--no-likes"]
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    for uuid in UUID_NO_LIKES:
        assert uuid in uuid_got
    for uuid in uuid_got:
        assert uuid not in UUID_HAS_LIKES


def test_query_is_reference():
    """Test query with --is-reference"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--is-reference"]
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(uuid_got) == sorted(UUID_IS_REFERENCE)


def test_query_edited():
    """Test query with --edited"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, CLI_PHOTOS_DB), "--edited"]
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(uuid_got) == sorted(UUID_EDITED)


def test_query_not_edited():
    """Test query with --not-edited"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, CLI_PHOTOS_DB), "--not-edited"]
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(uuid_got) == sorted(UUID_NOT_EDITED)


def test_query_in_album():
    """Test query with --in-album"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--in-album"]
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(uuid_got) == sorted(UUID_IN_ALBUM)


def test_query_not_in_album():
    """Test query with --not-in-album"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--not-in-album"]
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(uuid_got) == sorted(UUID_NOT_IN_ALBUM)


def test_query_duplicate():
    """Test query with --duplicate"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, CLI_PHOTOS_DB), "--duplicate"],
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(uuid_got) == sorted(UUID_DUPLICATES)


def test_query_location():
    """Test query with --location"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, CLI_PHOTOS_DB), "--location"],
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert UUID_LOCATION in uuid_got
    assert UUID_NO_LOCATION not in uuid_got


def test_query_no_location():
    """Test query with --no-location"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, CLI_PHOTOS_DB), "--no-location"],
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert UUID_NO_LOCATION in uuid_got
    assert UUID_LOCATION not in uuid_got


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
@pytest.mark.parametrize("exiftag,exifvalue,uuid_expected", QUERY_EXIF_DATA)
def test_query_exif(exiftag, exifvalue, uuid_expected):
    """Test query with --exif"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--exif",
            exiftag,
            exifvalue,
        ],
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(uuid_got) == sorted(uuid_expected)


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
@pytest.mark.parametrize(
    "exiftag,exifvalue,uuid_expected", QUERY_EXIF_DATA_CASE_INSENSITIVE
)
def test_query_exif_case_insensitive(exiftag, exifvalue, uuid_expected):
    """Test query with --exif -i"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--exif",
            exiftag,
            exifvalue,
            "-i",
        ],
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(uuid_got) == sorted(uuid_expected)


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_query_exif_multiple():
    """Test query with multiple --exif options, #873"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--exif",
            "Make",
            "Canon",
            "--exif",
            "Model",
            "Canon PowerShot G10",
        ],
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    assert len(json_got) == EXIF_MAKE_CANON


def test_export():
    """test basic export"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)


def test_export_alt_copy():
    """test basic export with --alt-copy"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--alt-copy", "-V"]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)


def test_export_tmpdir():
    """test basic export with --tmpdir"""
    runner = CliRunner()
    cwd = os.getcwd()
    tmpdir = TemporaryDirectory()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--tmpdir", tmpdir.name],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)


def test_export_uuid_from_file():
    """Test export with --uuid-from-file"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--uuid-from-file",
                os.path.join(cwd, UUID_FILE),
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_UUID_FROM_FILE_FILENAMES)


def test_export_skip_uuid_from_file():
    """Test export with --skip-uuid-from-file"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--skip-uuid-from-file",
                os.path.join(cwd, SKIP_UUID_FILE),
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        for skipped_file in CLI_EXPORT_SKIP_UUID_FILENAMES:
            assert skipped_file not in files


def test_export_skip_uuid():
    """Test export with --skip-uuid"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    uuid_option = []
    for uuid in CLI_EXPORT_SKIP_UUID:
        uuid_option.append("--skip-uuid")
        uuid_option.append(uuid)

    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                *uuid_option,
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        for skipped_file in CLI_EXPORT_SKIP_UUID_FILENAMES:
            assert skipped_file not in files


def test_export_year():
    """test export with --year"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--year",
                "2017",
                "--skip-edited",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_YEAR_2017)


def test_export_preview():
    """test export with --preview"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--preview",
                "--uuid",
                CLI_EXPORT_UUID,
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert CLI_EXPORT_UUID_FILENAME_PREVIEW in files


def test_export_preview_file_exists():
    """test export with --preview when preview images already exist, issue #516"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--preview",
                "--uuid",
                CLI_EXPORT_UUID_MISSING,
            ],
        )
        assert result.exit_code == 0

        # export again
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--preview",
                "--uuid",
                CLI_EXPORT_UUID_MISSING,
            ],
        )
        assert result.exit_code == 0
        assert "Error exporting photo" not in result.output


def test_export_preview_suffix():
    """test export with --preview and --preview-suffix"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--preview",
                "--preview-suffix",
                CLI_EXPORT_PREVIEW_SUFFIX,
                "--uuid",
                CLI_EXPORT_UUID,
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert CLI_EXPORT_UUID_FILENAME_PREVIEW_TEMPLATE in files


def test_export_preview_if_missing():
    """test export with --preview_if_missing"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        uuid_options = []
        for uuid in UUID_DICT_MISSING:
            uuid_options.extend(["--uuid", uuid])
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--preview-if-missing",
                "--preview-suffix",
                "",
                *uuid_options,
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        expected_files = list(UUID_DICT_MISSING.values())
        assert sorted(files) == sorted(expected_files)


def test_export_preview_overwrite():
    """test export with --preview and --overwrite (#526)"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--preview",
                "--uuid",
                CLI_EXPORT_UUID,
            ],
        )
        assert result.exit_code == 0

        # export again
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--preview",
                "--uuid",
                CLI_EXPORT_UUID,
                "--overwrite",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == 2  # preview + original


def test_export_preview_update():
    """test export with --preview and --update (#526)"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--preview",
                "--uuid",
                CLI_EXPORT_UUID,
            ],
        )
        assert result.exit_code == 0

        # export again
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--preview",
                "--uuid",
                CLI_EXPORT_UUID,
                "--update",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == 2  # preview + original


@contextlib.contextmanager
def isolated_filesystem_here():
    cwd = os.getcwd()
    tempdir = tempfile.mkdtemp(dir=cwd)  # type: ignore[type-var]
    os.chdir(tempdir)

    try:
        yield tempdir
    finally:
        os.chdir(cwd)
        shutil.rmtree(tempdir)


def test_export_as_hardlink():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with isolated_filesystem_here():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--export-as-hardlink", "-V"],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)


def test_export_as_hardlink_samefile():
    # test that --export-as-hardlink actually creates a hardlink
    # src and dest should be same file

    runner = CliRunner()
    cwd = os.getcwd()
    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    # pylint: disable=not-context-manager
    with isolated_filesystem_here():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                f"--uuid={CLI_EXPORT_UUID}",
                "--export-as-hardlink",
                "-V",
            ],
        )
        assert result.exit_code == 0
        assert os.path.exists(CLI_EXPORT_UUID_FILENAME)
        assert os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)


def test_export_using_hardlinks_incompat_options():
    # test that error shown if --export-as-hardlink used with --exiftool

    runner = CliRunner()
    cwd = os.getcwd()
    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    # pylint: disable=not-context-manager
    with isolated_filesystem_here():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                f"--uuid={CLI_EXPORT_UUID}",
                "--export-as-hardlink",
                "--exiftool",
                "-V",
            ],
        )
        assert result.exit_code == 1
        assert "Incompatible export options" in result.output


def test_export_current_name():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "--current-name", "-V"]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_CURRENT)


def test_export_skip_edited():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--skip-edited", "-V"]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert "St James Park_edited.jpeg" not in files


def test_export_edited():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--edited", "-V"]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        # make sure edited versions did get exported
        assert "wedding_edited.jpeg" in files
        assert "Tulips_edited.jpeg" in files
        assert "St James Park_edited.jpeg" in files


def test_export_not_edited():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--not-edited", "-V"]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        # make sure not edited files were exported
        assert "Pumkins1.jpg" in files
        assert "Pumkins2.jpg" in files
        assert "Jellyfish1.mp4" in files

        # make sure edited versions did not get exported
        assert "wedding_edited.jpeg" not in files
        assert "Tulips_edited.jpeg" not in files
        assert "St James Park_edited.jpeg" not in files


def test_export_skip_original_if_edited():
    """test export with --skip-original-if-edited"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_15_7), ".", "--skip-original-if-edited", "-V"],
        )
        assert result.exit_code == 0
        assert "Skipping original version of wedding.jpg" in result.output
        assert "Skipping original version of Tulips.jpg" in result.output
        assert "Skipping original version of St James Park.jpg" in result.output
        files = glob.glob("*")

        # make sure originals of edited version not exported
        assert "wedding.jpg" not in files
        assert "Tulips.jpg" not in files
        assert "St James Park.jpg" not in files

        # make sure edited versions did get exported
        assert "wedding_edited.jpeg" in files
        assert "Tulips_edited.jpeg" in files
        assert "St James Park_edited.jpeg" in files

        # make sure other originals did get exported
        assert "Pumkins2.jpg" in files


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            assert sorted(files) == sorted([CLI_EXIFTOOL[uuid]["File:FileName"]])

            exif = ExifTool(CLI_EXIFTOOL[uuid]["File:FileName"]).asdict()
            for key in CLI_EXIFTOOL[uuid]:
                if type(exif[key]) == list:
                    assert sorted(exif[key]) == sorted(CLI_EXIFTOOL[uuid][key])
                else:
                    assert exif[key] == CLI_EXIFTOOL[uuid][key]


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_tmpdir():
    """test --exiftool with --tmpdir"""
    runner = CliRunner()
    cwd = os.getcwd()
    tmpdir = TemporaryDirectory()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--uuid",
                    f"{uuid}",
                    "--tmpdir",
                    tmpdir.name,
                ],
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            assert sorted(files) == sorted([CLI_EXIFTOOL[uuid]["File:FileName"]])

            exif = ExifTool(CLI_EXIFTOOL[uuid]["File:FileName"]).asdict()
            for key in CLI_EXIFTOOL[uuid]:
                if type(exif[key]) == list:
                    assert sorted(exif[key]) == sorted(CLI_EXIFTOOL[uuid][key])
                else:
                    assert exif[key] == CLI_EXIFTOOL[uuid][key]


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_template_change():
    """Test --exiftool when template changes with --update, #630"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL:
            # export with --exiftool
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0

            # export with --update, should be no change
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--update",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0
            assert "exported: 0" in result.output

            # export with --update and template change, should export
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--keyword-template",
                    "FOO",
                    "--update",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0
            assert "updated EXIF data: 1" in result.output

            # export with --update, nothing should export
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--keyword-template",
                    "FOO",
                    "--update",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0
            assert "exported: 0" in result.output
            assert "updated EXIF data: 0" in result.output


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_path():
    """test --exiftool with --exiftool-path"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--uuid",
                    f"{uuid}",
                    "--exiftool-path",
                    exiftool,
                ],
            )
            assert result.exit_code == 0
            assert f"exiftool path: {exiftool}" in result.output
            files = glob.glob("*")
            assert sorted(files) == sorted([CLI_EXIFTOOL[uuid]["File:FileName"]])

            exif = ExifTool(CLI_EXIFTOOL[uuid]["File:FileName"]).asdict()
            for key in CLI_EXIFTOOL[uuid]:
                if type(exif[key]) == list:
                    assert sorted(exif[key]) == sorted(CLI_EXIFTOOL[uuid][key])
                else:
                    assert exif[key] == CLI_EXIFTOOL[uuid][key]


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_path_render_template():
    """test --exiftool-path with {exiftool:} template rendering"""

    exiftool_source = osxphotos.exiftool.get_exiftool_path()

    # monkey patch get_exiftool_path so it returns None
    get_exiftool_path = osxphotos.exiftool.get_exiftool_path
    osxphotos.exiftool.get_exiftool_path = noop

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--filename",
                    "{original_name}_{exiftool:EXIF:Make}",
                    "--uuid",
                    f"{uuid}",
                    "--exiftool-path",
                    exiftool,
                ],
            )
            assert result.exit_code == 0
            assert re.search(r"Exported.*Canon", result.output)

    osxphotos.exiftool.get_exiftool_path = get_exiftool_path


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_ignore_date_modified():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL_IGNORE_DATE_MODIFIED:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--ignore-date-modified",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0

            exif = ExifTool(
                CLI_EXIFTOOL_IGNORE_DATE_MODIFIED[uuid]["File:FileName"]
            ).asdict()
            for key in CLI_EXIFTOOL_IGNORE_DATE_MODIFIED[uuid]:
                if type(exif[key]) == list:
                    assert sorted(exif[key]) == sorted(
                        CLI_EXIFTOOL_IGNORE_DATE_MODIFIED[uuid][key]
                    )
                else:
                    assert exif[key] == CLI_EXIFTOOL_IGNORE_DATE_MODIFIED[uuid][key]


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_quicktime():
    """test --exiftol correctly writes QuickTime tags"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL_QUICKTIME:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            assert sorted(files) == sorted(
                [CLI_EXIFTOOL_QUICKTIME[uuid]["File:FileName"]]
            )

            exif = ExifTool(CLI_EXIFTOOL_QUICKTIME[uuid]["File:FileName"]).asdict()
            for key in CLI_EXIFTOOL_QUICKTIME[uuid]:
                assert exif[key] == CLI_EXIFTOOL_QUICKTIME[uuid][key]

            # clean up exported files to avoid name conflicts
            for filename in files:
                os.unlink(filename)


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_duplicate_keywords():
    """ensure duplicate keywords are removed"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL_DUPLICATE_KEYWORDS:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            exif = ExifTool(CLI_EXIFTOOL_DUPLICATE_KEYWORDS[uuid])
            exifdict = exif.asdict()
            assert sorted(exifdict["IPTC:Keywords"]) == ["Maria", "wedding"]
            assert sorted(exifdict["XMP:Subject"]) == ["Maria", "wedding"]


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_error():
    """ " test --exiftool catching error"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            assert sorted(files) == sorted([CLI_EXIFTOOL[uuid]["File:FileName"]])

            exif = ExifTool(CLI_EXIFTOOL[uuid]["File:FileName"]).asdict()
            for key in CLI_EXIFTOOL[uuid]:
                if type(exif[key]) == list:
                    assert sorted(exif[key]) == sorted(CLI_EXIFTOOL[uuid][key])
                else:
                    assert exif[key] == CLI_EXIFTOOL[uuid][key]


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_option():
    """test --exiftool-option"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # first export with --exiftool, one file produces a warning
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V", "--exiftool"]
        )
        assert result.exit_code == 0
        assert "exiftool warning" in result.output

        # run again with exiftool-option = "-m" (ignore minor warnings)
        # shouldn't see the warning this time
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--exiftool",
                "--exiftool-option",
                "-m",
            ],
        )
        assert result.exit_code == 0
        assert "exiftool warning" not in result.output


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_merge():
    """test --exiftool-merge-keywords and --exiftool-merge-persons"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL_MERGE:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--exiftool",
                    "--uuid",
                    f"{uuid}",
                    "--exiftool-merge-keywords",
                    "--exiftool-merge-persons",
                ],
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            assert CLI_EXIFTOOL_MERGE[uuid]["File:FileName"] in files

            exif = ExifTool(CLI_EXIFTOOL_MERGE[uuid]["File:FileName"]).asdict()
            for key in CLI_EXIFTOOL_MERGE[uuid]:
                if type(exif[key]) == list:
                    assert sorted(exif[key]) == sorted(CLI_EXIFTOOL_MERGE[uuid][key])
                else:
                    assert exif[key] == CLI_EXIFTOOL_MERGE[uuid][key]


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_merge_sidecar():
    """test --exiftool-merge-keywords and --exiftool-merge-persons with --sidecar"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL_MERGE:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--sidecar",
                    "json",
                    "--uuid",
                    f"{uuid}",
                    "--exiftool-merge-keywords",
                    "--exiftool-merge-persons",
                ],
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            json_file = f"{CLI_EXIFTOOL_MERGE[uuid]['File:FileName']}.json"
            assert json_file in files

            with open(json_file, "r") as fp:
                exif = json.load(fp)[0]

            for key in CLI_EXIFTOOL_MERGE[uuid]:
                if key == "File:FileName":
                    continue
                if type(exif[key]) == list:
                    expected = (
                        CLI_EXIFTOOL_MERGE[uuid][key]
                        if type(CLI_EXIFTOOL_MERGE[uuid][key]) == list
                        else [CLI_EXIFTOOL_MERGE[uuid][key]]
                    )
                    assert sorted(exif[key]) == sorted(expected)
                else:
                    assert exif[key] == CLI_EXIFTOOL_MERGE[uuid][key]


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_merge_sidecar_xmp():
    """test --exiftool-merge-keywords and --exiftool-merge-persons with --sidecar xmp"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL_MERGE:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--sidecar",
                    "xmp",
                    "--uuid",
                    f"{uuid}",
                    "--exiftool-merge-keywords",
                    "--exiftool-merge-persons",
                ],
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            xmp_file = f"{CLI_EXIFTOOL_MERGE[uuid]['File:FileName']}.xmp"
            assert xmp_file in files


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_favorite_rating():
    """Test --exiftol --favorite-rating"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--exiftool",
                "--uuid",
                UUID_FAVORITE,
                "--uuid",
                UUID_NOT_FAVORITE,
                "--favorite-rating",
            ],
        )
        assert result.exit_code == 0
        assert ExifTool(FILE_FAVORITE).asdict()["XMP:Rating"] == 5
        assert ExifTool(FILE_NOT_FAVORITE).asdict()["XMP:Rating"] == 0


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_exiftool_update_errors():
    """Test export with --update-errors, #872"""
    runner = CliRunner()
    cwd = os.getcwd()

    # first, normal export with --exiftool
    # some of the files will have errors / warnings from exiftool
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--exiftool",
            ],
        )

        # now run update; none of files should be updated
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--exiftool",
                "--update",
            ],
        )
        assert result.exit_code == 0
        assert "updated: 0" in result.output

        # now run update-errors; only files with errors should be updated
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--exiftool",
                "--update",
                "--update-errors",
            ],
        )
        assert result.exit_code == 0
        assert "updated: 4" in result.output


def test_export_edited_suffix():
    """test export with --edited-suffix"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--edited-suffix",
                CLI_EXPORT_EDITED_SUFFIX,
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_EDITED_SUFFIX)


def test_export_edited_suffix_template():
    """test export with --edited-suffix template"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--edited-suffix",
                CLI_EXPORT_EDITED_SUFFIX_TEMPLATE,
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_EDITED_SUFFIX_TEMPLATE)


def test_export_original_suffix():
    """test export with --original-suffix"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--original-suffix",
                CLI_EXPORT_ORIGINAL_SUFFIX,
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_ORIGINAL_SUFFIX)


def test_export_original_suffix_template():
    """test export with --original-suffix template"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--original-suffix",
                CLI_EXPORT_ORIGINAL_SUFFIX_TEMPLATE,
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_ORIGINAL_SUFFIX_TEMPLATE)


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_CONVERT" not in os.environ,
    reason="Skip if running in Github actions, no GPU.",
)
def test_export_convert_to_jpeg():
    """test --convert-to-jpeg"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V", "--convert-to-jpeg"]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_CONVERT_TO_JPEG)
        large_file = pathlib.Path(CLI_EXPORT_CONVERT_TO_JPEG_LARGE_FILE)
        assert large_file.stat().st_size > 7000000


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_CONVERT" not in os.environ,
    reason="Skip if running in Github actions, no GPU.",
)
def test_export_convert_to_jpeg_quality():
    """test --convert-to-jpeg --jpeg-quality"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--convert-to-jpeg",
                "--jpeg-quality",
                "0.2",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_CONVERT_TO_JPEG)
        large_file = pathlib.Path(CLI_EXPORT_CONVERT_TO_JPEG_LARGE_FILE)
        assert large_file.stat().st_size < 1000000


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_CONVERT" not in os.environ,
    reason="Skip if running in Github actions, no GPU.",
)
def test_export_convert_to_jpeg_skip_raw():
    """test --convert-to-jpeg"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--convert-to-jpeg",
                "--skip-raw",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_CONVERT_TO_JPEG_SKIP_RAW)


def test_export_duplicate():
    """Test export with --duplicate"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--duplicate", "--skip-raw"],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == len(UUID_DUPLICATES)


def test_export_duplicate_unicode_filenames():
    # test issue #515

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    uuid = []
    for u in UUID_UNICODE_TITLE:
        uuid.append("--uuid")
        uuid.append(u)
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--convert-to-jpeg",
                "--edited-suffix",
                "",
                "--filename",
                "{title,{original_name}}",
                "--jpeg-ext",
                "jpg",
                "--person-keyword",
                "--skip-bursts",
                "--skip-live",
                "--skip-original-if-edited",
                "--touch-file",
                "--strip",
                *uuid,
                "-V",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 4" in result.output
        files = glob.glob("*")
        assert sorted(files) == sorted(EXPORT_UNICODE_TITLE_FILENAMES)


@pytest.mark.usefixtures("set_tz_pacific")
def test_query_from_to_date():
    """Test --from-date and --to-date #590"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--from-date=2018-09-28",
            "--to-date=2018-09-28T16:09:33.022000-04:00",
        ],
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert len(json_got) == 3


@pytest.mark.usefixtures("set_tz_jerusalem")
def test_query_from_to_date_alt_location():
    """Test --from-date and --to-date in a different timezone"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--from-date=2018-09-28",
            "--to-date=2018-09-28T23:00:00",
        ],
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert len(json_got) == 2


@pytest.mark.usefixtures("set_tz_pacific")
def test_query_from_to_date_timezone():
    """Test --from-date, --to-date with ISO 8601 timezone"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--from-date=2018-09-28T00:00:00-07:00",
            "--to-date=2018-09-28T23:00:00-07:00",
        ],
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert len(json_got) == 4


@pytest.mark.usefixtures("set_tz_pacific")
def test_query_from_to_time():
    """Test --from-time, --to-time"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--from-time=16:00",
            "--to-time=16:09:33.022000",
        ],
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert len(json_got) == 1


@pytest.mark.usefixtures("set_tz_pacific")
def test_query_year_single():
    """Test --year"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--year",
            2017,
        ],
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert len(json_got) == 1


@pytest.mark.usefixtures("set_tz_pacific")
def test_query_year_mulitple():
    """Test --year with multiple years"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--year",
            2017,
            "--year",
            2018,
        ],
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert len(json_got) == 6


@pytest.mark.usefixtures("set_tz_pacific")
def test_query_year_3():
    """Test --year with invalid year"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, CLI_PHOTOS_DB),
            "--year",
            3000,
        ],
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert len(json_got) == 0


def test_query_keyword_1():
    """Test query --keyword"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--keyword", "Kids"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 4


def test_query_keyword_2():
    """Test query --keyword with lower case keyword"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--keyword", "kids"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 0


def test_query_keyword_3():
    """Test query --keyword with lower case keyword and --ignore-case"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--keyword",
            "kids",
            "--ignore-case",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 4


def test_query_keyword_4():
    """Test query with more than one --keyword"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--keyword",
            "Kids",
            "--keyword",
            "wedding",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 6


def test_query_no_keyword():
    """Test query --no-keyword"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--no-keyword",
            "--added-before",
            "2022-05-05",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 11


def test_query_person_1():
    """Test query --person"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--person", "Katie"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 3


def test_query_person_2():
    """Test query --person with lower case person"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--person", "katie"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 0


def test_query_person_3():
    """Test query --person with lower case person and --ignore-case"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--person",
            "katie",
            "--ignore-case",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 3


def test_query_person_4():
    """Test query with multiple --person"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--person",
            "Katie",
            "--person",
            "Maria",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 4


def test_query_album_1():
    """Test query --album"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--album",
            "Pumpkin Farm",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 3


def test_query_album_2():
    """Test query --album with lower case album"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--album",
            "pumpkin farm",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 0


def test_query_album_3():
    """Test query --album with lower case album and --ignore-case"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--album",
            "pumpkin farm",
            "--ignore-case",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 3


def test_query_album_4():
    """Test query with multipl --album"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--album",
            "Pumpkin Farm",
            "--album",
            "Raw",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 7


def test_query_label_1():
    """Test query --label"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--label", "Bouquet"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 1


def test_query_label_2():
    """Test query --label with lower case label"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--label", "bouquet"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 0


def test_query_label_3():
    """Test query --label with lower case label and --ignore-case"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--label",
            "bouquet",
            "--ignore-case",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 1


def test_query_label_4():
    """Test query with more than one --label"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--label",
            "Bouquet",
            "--label",
            "Plant",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 1


def test_query_deleted_deleted_only():
    """Test query with --deleted and --deleted-only"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--deleted",
            "--deleted-only",
        ],
    )
    assert "Incompatible query options" in result.output


def test_query_deleted_1():
    """Test query with --deleted"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--deleted"]
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == PHOTOS_NOT_IN_TRASH_LEN_15_7 + PHOTOS_IN_TRASH_LEN_15_7


def test_query_deleted_2():
    """Test query with --deleted"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--deleted"]
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == PHOTOS_NOT_IN_TRASH_LEN_15_7 + PHOTOS_IN_TRASH_LEN_15_7


def test_query_deleted_3():
    """Test query with --deleted-only"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--deleted-only"]
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == PHOTOS_IN_TRASH_LEN_15_7
    assert json_got[0]["intrash"]


def test_query_deleted_4():
    """Test query with --deleted-only"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--deleted-only"]
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == PHOTOS_IN_TRASH_LEN_15_7
    assert json_got[0]["intrash"]


def test_export_aae():
    """Test export with --export-aae"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--export-aae",
                f"--uuid={CLI_EXPORT_AAE_UUID}",
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        assert sorted(files) == sorted(CLI_EXPORT_AAE_FILENAMES)


def test_export_aae_as_hardlink():
    """Test export with --export-aae and --export-as-hardlink"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with isolated_filesystem_here():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--export-aae",
                "--export-as-hardlink",
                f"--uuid={CLI_EXPORT_AAE_UUID}",
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        assert sorted(files) == sorted(CLI_EXPORT_AAE_FILENAMES)


def test_export_sidecar():
    """test --sidecar"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        assert sorted(files) == sorted(CLI_EXPORT_SIDECAR_FILENAMES)


def test_export_sidecar_favorite_rating():
    """test --sidecar --favorite-rating"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                f"--uuid={UUID_FAVORITE}",
                f"--uuid={UUID_NOT_FAVORITE}",
                "--favorite-rating",
                "-V",
            ],
        )
        assert result.exit_code == 0
        with open(f"{FILE_FAVORITE}.json") as fp:
            json_sidecar = json.load(fp)
            assert json_sidecar[0]["XMP:Rating"] == 5
        with open(f"{FILE_NOT_FAVORITE}.json") as fp:
            json_sidecar = json.load(fp)
            assert json_sidecar[0]["XMP:Rating"] == 0

        results = subprocess.run(
            ["grep", "xmp:Rating", f"{FILE_FAVORITE}.xmp"], capture_output=True
        )
        results_stdout = results.stdout.decode("utf-8")
        assert "<xmp:Rating>5</xmp:Rating>" in results_stdout

        results = subprocess.run(
            ["grep", "xmp:Rating", f"{FILE_NOT_FAVORITE}.xmp"], capture_output=True
        )
        results_stdout = results.stdout.decode("utf-8")
        assert "<xmp:Rating>0</xmp:Rating>" in results_stdout


def test_export_sidecar_drop_ext():
    """test --sidecar with --sidecar-drop-ext option"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                "--sidecar-drop-ext",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        assert sorted(files) == sorted(CLI_EXPORT_SIDECAR_DROP_EXT_FILENAMES)


def test_export_sidecar_exiftool():
    """test --sidecar exiftool"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=exiftool",
                "--sidecar=xmp",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
            ],
        )
        assert result.exit_code == 0
        assert "Writing exiftool sidecar" in result.output
        files = glob.glob("*.*")
        assert sorted(files) == sorted(CLI_EXPORT_SIDECAR_FILENAMES)


def test_export_sidecar_templates():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--sidecar=json",
                f"--uuid={CLI_UUID_DICT_15_7['template']}",
                "-V",
                "--keyword-template",
                "{person}",
                "--description-template",
                "{descr} {person} {keyword} {album}",
            ],
        )
        assert result.exit_code == 0
        assert os.path.isfile(CLI_TEMPLATE_SIDECAR_FILENAME)
        with open(CLI_TEMPLATE_SIDECAR_FILENAME, "r") as jsonfile:
            exifdata = json.load(jsonfile)
        # order of multi-value templates is indeterminate so verify substrings instead of equality
        for tag in ["XMP:Description", "EXIF:ImageDescription"]:
            value = exifdata[0][tag]
            assert value.startswith("Girls with pumpkins")
            assert "Katie" in value
            assert "Suzy" in value
            assert "Kids" in value
            assert "Pumpkin Farm" in value
            assert "Sorted Manual" in value
            assert "Sorted Newest First" in value
            assert "Sorted Oldest First" in value
            assert "Sorted Title" in value
            assert "Test Album" in value


def test_export_sidecar_templates_exiftool():
    """test --sidecar exiftool with templates"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--sidecar=exiftool",
                f"--uuid={CLI_UUID_DICT_15_7['template']}",
                "-V",
                "--keyword-template",
                "{person}",
                "--description-template",
                "{descr} {person} {keyword} {album}",
            ],
        )
        assert result.exit_code == 0
        assert os.path.isfile(CLI_TEMPLATE_SIDECAR_FILENAME)
        with open(CLI_TEMPLATE_SIDECAR_FILENAME, "r") as jsonfile:
            exifdata = json.load(jsonfile)
        # order of multi-value templates is indeterminate so verify substrings instead of equality
        for tag in ["Description", "ImageDescription"]:
            value = exifdata[0][tag]
            assert value.startswith("Girls with pumpkins")
            assert "Katie" in value
            assert "Suzy" in value
            assert "Kids" in value
            assert "Pumpkin Farm" in value
            assert "Sorted Manual" in value
            assert "Sorted Newest First" in value
            assert "Sorted Oldest First" in value
            assert "Sorted Title" in value
            assert "Test Album" in value


def test_export_sidecar_update():
    """test sidecar don't update if not changed and do update if changed"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
            ],
        )
        assert result.exit_code == 0
        assert "Writing XMP sidecar" in result.output
        assert "Writing JSON sidecar" in result.output

        # delete a sidecar file and run update
        fileutil = FileUtil()
        fileutil.unlink(CLI_EXPORT_SIDECAR_FILENAMES[1])

        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
                "--update",
            ],
        )
        assert result.exit_code == 0
        assert "Skipped up to date XMP sidecar" in result.output
        assert "Writing JSON sidecar" in result.output

        # run update again, no sidecar files should update
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
                "--update",
            ],
        )
        assert result.exit_code == 0
        assert "Skipped up to date XMP sidecar" in result.output
        assert "Skipped up to date JSON sidecar" in result.output

        # touch a file and export again
        ts = datetime.datetime.now().timestamp() + 1000
        fileutil.utime(CLI_EXPORT_SIDECAR_FILENAMES[2], (ts, ts))

        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
                "--update",
            ],
        )
        assert result.exit_code == 0
        assert "Writing XMP sidecar" in result.output
        assert "Skipped up to date JSON sidecar" in result.output

        # run update again, no sidecar files should update
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
                "--update",
            ],
        )
        assert result.exit_code == 0
        assert "Skipped up to date XMP sidecar" in result.output
        assert "Skipped up to date JSON sidecar" in result.output

        # run update again with updated metadata, forcing update
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
                "--update",
                "--keyword-template",
                "foo",
            ],
        )
        assert result.exit_code == 0
        assert "Writing XMP sidecar" in result.output
        assert "Writing JSON sidecar" in result.output


def test_export_sidecar_invalid():
    """test invalid combination of sidecars"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=exiftool",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
            ],
        )
        assert result.exit_code != 0
        assert "cannot use --sidecar json with --sidecar exiftool" in result.output


def test_export_live():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, LIVE_PHOTOS_DB), ".", "--live", "-V"]
        )
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_LIVE_ORIGINAL)


def test_export_skip_live():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, LIVE_PHOTOS_DB), ".", "--skip-live", "-V"]
        )
        files = glob.glob("*")
        assert "img_0728.mov" not in [f.lower() for f in files]


def test_export_raw():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, RAW_PHOTOS_DB),
                ".",
                "--current-name",
                "--skip-edited",
                "-V",
            ],
        )
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_RAW)


# TODO: Update this once RAW db is added
# def test_skip_raw():
#     runner = CliRunner()
#     cwd = os.getcwd()
#     # pylint: disable=not-context-manager
#     with runner.isolated_filesystem():
#         result = runner.invoke(
#             export, [os.path.join(cwd, RAW_PHOTOS_DB), ".", "--skip-raw", "-V"]
#         )
#         files = glob.glob("*")
#         for rawname in CLI_EXPORT_RAW:
#             assert rawname.lower() not in [f.lower() for f in files]


def test_export_raw_original():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, RAW_PHOTOS_DB), ".", "--skip-edited", "-V"]
        )
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_RAW_ORIGINAL)


def test_export_raw_edited():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, RAW_PHOTOS_DB), ".", "--current-name", "-V"]
        )
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_RAW_EDITED)


def test_export_raw_edited_original():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(export, [os.path.join(cwd, RAW_PHOTOS_DB), ".", "-V"])
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_RAW_EDITED_ORIGINAL)


def test_export_directory_template_1():
    # test export using directory template

    setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{created.year}/{created.month}",
            ],
        )
        assert result.exit_code == 0
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES1:
            assert os.path.isfile(os.path.join(workdir, filepath))


def test_export_directory_template_2():
    # test export using directory template with missing substitution value

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{place.name}",
            ],
        )
        assert result.exit_code == 0
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES2:
            assert os.path.isfile(os.path.join(workdir, filepath))


def test_export_directory_template_3():
    # test export using directory template with unmatched substitution value

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{created.year}/{foo}",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output


def test_export_directory_template_album_1():
    # test export using directory template with multiple albums

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--directory", "{album}"],
        )
        assert result.exit_code == 0
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_ALBUM1:
            assert os.path.isfile(os.path.join(workdir, filepath))


def test_export_directory_template_album_2():
    # test export using directory template with multiple albums
    # specify default value

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{album,NOALBUM}",
            ],
        )
        assert result.exit_code == 0
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_ALBUM2:
            assert os.path.isfile(os.path.join(workdir, filepath))


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_LOCALE" not in os.environ,
    reason="Skip if running in Github actions",
)
def test_export_directory_template_locale():
    # test export using directory template in user locale non-US

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # set locale environment
        os.environ["LC_ALL"] = "de_DE.UTF-8"
        setlocale(locale.LC_ALL, "")
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PLACES_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{created.year}/{created.month}",
            ],
        )
        assert result.exit_code == 0
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_LOCALE:
            assert os.path.isfile(os.path.join(workdir, filepath))


def test_export_filename_template_1():
    """export photos using filename template"""

    setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--filename",
                "{created.year}-{original_name}",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        for file in CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES1:
            assert file in files


def test_export_filename_template_2():
    """export photos using filename template with folder_album and path_sep"""

    setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--filename",
                "{folder_album,None}-{original_name}",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        for file in CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES2:
            assert file in files


def test_export_filename_template_strip():
    """export photos using filename template with --strip"""

    setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--filename",
                "{searchinfo.venue,} {created.year}-{original_name}",
                "--strip",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        for file in CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES1:
            assert file in files


def test_export_filename_template_pathsep_in_name_1():
    """export photos using filename template with folder_album and "/" in album name"""

    setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--directory",
                "{folder_album,None}",
                "--uuid",
                CLI_EXPORT_UUID_STATUE,
            ],
        )
        assert result.exit_code == 0
        for fname in CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES_PATHSEP:
            # assert fname in result.output
            assert pathlib.Path(fname).is_file()


def test_export_filename_template_pathsep_in_name_2():
    """export photos using filename template with keyword and "/" in keyword"""

    setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--directory",
                "{keyword}",
                "--filename",
                "{keyword}_{original_name}",
                "--uuid",
                CLI_EXPORT_UUID_KEYWORD_PATHSEP,
            ],
        )
        assert result.exit_code == 0
        for fname in CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES_KEYWORD_PATHSEP:
            assert pathlib.Path(fname).is_file()


def test_export_filename_template_long_description():
    """export photos using filename template with description that exceeds max length"""

    setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--filename",
                "{descr}",
                "--uuid",
                CLI_EXPORT_UUID_LONG_DESCRIPTION,
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        for fname in CLI_EXPORTED_FILENAME_TEMPLATE_LONG_DESCRIPTION:
            assert pathlib.Path(fname).is_file()


def test_export_filename_template_3():
    """test --filename with invalid template"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{foo}-{original_filename}",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output


def test_export_album():
    """Test export of an album"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_15_7), ".", "--album", "Pumpkin Farm", "-V"],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_ALBUM)


def test_export_album_unicode_name():
    """Test export of an album with non-English characters in name"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--album",
                "2018-10 - Sponsion, Museum, Frühstück, Römermuseum",
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_ALBUM_UNICODE)


def test_export_album_deleted_twin():
    """Test export of an album where album of same name has been deleted"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--album",
                "I have a deleted twin",
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_DELETED_TWIN)


def test_export_deleted_1():
    """Test export with --deleted"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        skip = ["--skip-edited", "--skip-bursts", "--skip-live", "--skip-raw"]
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "--deleted", *skip]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert (
            len(files)
            == PHOTOS_NOT_IN_TRASH_LEN_15_7
            + PHOTOS_IN_TRASH_LEN_15_7
            - PHOTOS_MISSING_15_7
        )


def test_export_deleted_2():
    """Test export with --deleted"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        skip = ["--skip-edited", "--skip-bursts", "--skip-live", "--skip-raw"]
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_14_6), ".", "--deleted", *skip]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert (
            len(files)
            == PHOTOS_NOT_IN_TRASH_LEN_14_6
            + PHOTOS_IN_TRASH_LEN_14_6
            - PHOTOS_MISSING_14_6
        )


def test_export_not_deleted_1():
    """Test export does not find intrash files without --deleted flag"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        skip = ["--skip-edited", "--skip-bursts", "--skip-live", "--skip-raw"]
        result = runner.invoke(export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", *skip])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == PHOTOS_NOT_IN_TRASH_LEN_15_7 - PHOTOS_MISSING_15_7


def test_export_not_deleted_2():
    """Test export does not find intrash files without --deleted flag"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        skip = ["--skip-edited", "--skip-bursts", "--skip-live", "--skip-raw"]
        result = runner.invoke(export, [os.path.join(cwd, PHOTOS_DB_14_6), ".", *skip])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == PHOTOS_NOT_IN_TRASH_LEN_14_6 - PHOTOS_MISSING_14_6


def test_export_deleted_only_1():
    """Test export with --deleted-only"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        skip = ["--skip-edited", "--skip-bursts", "--skip-live", "--skip-raw"]
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "--deleted-only", *skip]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == PHOTOS_IN_TRASH_LEN_15_7


def test_export_deleted_only_2():
    """Test export with --deleted-only"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        skip = ["--skip-edited", "--skip-bursts", "--skip-live", "--skip-raw"]
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_14_6), ".", "--deleted-only", *skip]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == PHOTOS_IN_TRASH_LEN_14_6


def test_export_error(monkeypatch):
    """Test that export catches errors thrown by export"""
    # Note: I often comment out the try/except block in cli.py::export_photo_with_template when
    # debugging to see exactly where the error is
    # this test verifies I've re-enabled that code

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager

    def throw_error(*args, **kwargs):
        raise ValueError("Argh!")

    monkeypatch.setattr(osxphotos.PhotoExporter, "export", throw_error)
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V", "--uuid", CLI_EXPORT_UUID],
        )
        assert result.exit_code == 0
        assert "Error exporting" in result.output


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
@pytest.mark.parametrize("exiftag,exifvalue,files_expected", EXPORT_EXIF_DATA)
def test_export_exif(exiftag, exifvalue, files_expected):
    """Test export --exif query"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--exif", exiftag, exifvalue, "-V"],
        )
        files = glob.glob("*")
        assert sorted(files) == sorted(files_expected)


def test_places():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            places, ["--db", os.path.join(cwd, PLACES_PHOTOS_DB), "--json"]
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)
        assert json_got == json.loads(CLI_PLACES_JSON)


def test_place_13():
    # test --place on 10.13

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [
                "--db",
                os.path.join(cwd, PLACES_PHOTOS_DB_13),
                "--json",
                "--place",
                "Adelaide",
            ],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "2L6X2hv3ROWRSCU3WRRAGQ"


def test_no_place_13():
    # test --no-place on 10.13

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            ["--db", os.path.join(cwd, PLACES_PHOTOS_DB_13), "--json", "--no-place"],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "pERZk5T1Sb+XcKDFRCsGpA"


def test_place_15_1():
    # test --place on 10.15

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [
                "--db",
                os.path.join(cwd, PLACES_PHOTOS_DB),
                "--json",
                "--place",
                "Washington",
            ],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "128FB4C6-0B16-4E7D-9108-FB2E90DA1546"


def test_place_15_2():
    # test --place on 10.15

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [
                "--db",
                os.path.join(cwd, PLACES_PHOTOS_DB),
                "--json",
                "--place",
                "United States",
            ],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 2  # single element
        uuid = [json_got[x]["uuid"] for x in (0, 1)]
        assert "128FB4C6-0B16-4E7D-9108-FB2E90DA1546" in uuid
        assert "FF7AFE2C-49B0-4C9B-B0D7-7E1F8B8F2F0C" in uuid


def test_no_place_15():
    # test --no-place on 10.15

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query, ["--db", os.path.join(cwd, PLACES_PHOTOS_DB), "--json", "--no-place"]
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "A9B73E13-A6F2-4915-8D67-7213B39BAE9F"


def test_no_folder_1_15():
    # test --folder on 10.15

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--json",
                "--folder",
                "Folder1",
            ],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 2  # single element
        for item in json_got:
            assert item["uuid"] in [
                "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
                "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
            ]
            for album in item["albums"]:
                assert album in [
                    "2019-10/11 Paris Clermont",
                    "2018-10 - Sponsion, Museum, Frühstück, Römermuseum",
                    "AlbumInFolder",
                    "I have a deleted twin",
                    "Multi Keyword",
                    "Sorted Manual",
                    "Sorted Newest First",
                    "Sorted Oldest First",
                    "Sorted Title",
                ]


def test_no_folder_2_15():
    # test --folder with --uuid on 10.15

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--json",
                "--folder",
                "Folder1",
                "--uuid",
                "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
            ],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        for item in json_got:
            assert item["uuid"] == "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"
            assert sorted(item["albums"]) == sorted(
                ["AlbumInFolder", "I have a deleted twin", "Multi Keyword"]
            )


def test_no_folder_1_14():
    # test --folder on 10.14

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_14_6),
                "--json",
                "--folder",
                "Folder1",
            ],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)
        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "15uNd7%8RguTEgNPKHfTWw"


def test_export_sidecar_keyword_template():
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--sidecar=json",
                "--sidecar=xmp",
                "--keyword-template",
                "{folder_album}",
                f"--uuid={CLI_EXPORT_UUID}",
                "-V",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        assert sorted(files) == sorted(CLI_EXPORT_SIDECAR_FILENAMES)

        json_expected = json.loads(
            """
            [{
                "SourceFile": "Pumkins2.jpg",
                "ExifTool:ExifToolVersion": "12.00",
                "File:FileName": "Pumkins2.jpg",
                "EXIF:ImageDescription": "Girl holding pumpkin",
                "XMP:Description": "Girl holding pumpkin",
                "IPTC:Caption-Abstract": "Girl holding pumpkin",
                "XMP:Title": "I found one!",
                "IPTC:ObjectName": "I found one!",
                "IPTC:Keywords": [
                    "Kids",
                    "Multi Keyword",
                    "Pumpkin Farm",
                    "Test Album"
                ],
                "XMP:Subject": [
                    "Kids",
                    "Multi Keyword",
                    "Pumpkin Farm",
                    "Test Album"
                ],
                "XMP:TagsList": [
                    "Kids",
                    "Multi Keyword",
                    "Pumpkin Farm",
                    "Test Album"
                ],
                "XMP:PersonInImage": [
                    "Katie"
                ],
                "XMP:RegionAppliedToDimensionsW": 1365,
                "XMP:RegionAppliedToDimensionsH": 2048,
                "XMP:RegionAppliedToDimensionsUnit": "pixel",
                "XMP:RegionName": [
                    "Katie"
                ],
                "XMP:RegionType": [
                    "Face"
                ],
                "XMP:RegionAreaX": [
                    0.5898191407322884
                ],
                "XMP:RegionAreaY": [
                    0.28164292871952057
                ],
                "XMP:RegionAreaW": [
                    0.22411711513996124
                ],
                "XMP:RegionAreaH": [
                    0.14937493269826518
                ],
                "XMP:RegionAreaUnit": [
                    "normalized"
                ],
                "XMP:RegionPersonDisplayName": [
                    "Katie"
                ],
                "EXIF:GPSLatitude": 41.256566,
                "EXIF:GPSLongitude": -95.940257,
                "EXIF:GPSLatitudeRef": "N",
                "EXIF:GPSLongitudeRef": "W",
                "EXIF:DateTimeOriginal": "2018:09:28 16:07:07",
                "EXIF:CreateDate": "2018:09:28 16:07:07",
                "EXIF:OffsetTimeOriginal": "-04:00",
                "IPTC:DateCreated": "2018:09:28",
                "IPTC:TimeCreated": "16:07:07-04:00",
                "EXIF:ModifyDate": "2018:09:28 16:07:07"
        }]"""
        )[0]

        with open("Pumkins2.jpg.json", "r") as json_file:
            json_got = json.load(json_file)[0]

        # some gymnastics to account for different sort order in different pythons
        for k, v in json_got.items():
            if type(v) in (list, tuple):
                assert sorted(json_expected[k]) == sorted(v)
            else:
                assert json_expected[k] == v

        for k, v in json_expected.items():
            if type(v) in (list, tuple):
                assert sorted(json_got[k]) == sorted(v)
            else:
                assert json_got[k] == v


def test_export_update_basic():
    """test export then update"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert os.path.isfile(OSXPHOTOS_EXPORT_DB)

        # update
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update"]
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: 0, updated: 0, skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, updated EXIF data: 0, missing: 3, error: 0"
            in result.output
        )


def test_export_force_update():
    """test export with --force-update"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert os.path.isfile(OSXPHOTOS_EXPORT_DB)

        src = os.path.join(cwd, CLI_PHOTOS_DB)
        dest = os.path.join(os.getcwd(), "export_force_update.photoslibrary")
        photos_db_path = copy_photos_library_to_path(src, dest)

        # update
        result = runner.invoke(
            export, [os.path.join(cwd, photos_db_path), ".", "--update"]
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: 0, updated: 0, skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, updated EXIF data: 0, missing: 3, error: 0"
            in result.output
        )

        # force update must be run once to set the metadata digest info
        # in practice, this means that first time user uses --force-update, most files will likely be re-exported
        result = runner.invoke(
            export, [os.path.join(cwd, photos_db_path), ".", "--force-update"]
        )
        assert result.exit_code == 0

        # update a file
        dbpath = os.path.join(photos_db_path, "database/Photos.sqlite")
        try:
            conn = sqlite3.connect(dbpath)
            c = conn.cursor()
        except sqlite3.Error as e:
            pytest.exit("An error occurred opening sqlite file")

        # photo is IMG_4547.jpg
        c.execute(
            "UPDATE ZADDITIONALASSETATTRIBUTES SET Z_OPT=9, ZTITLE='My Updated Title' WHERE Z_PK=8;"
        )
        conn.commit()

        # run --force-update to see if updated metadata forced update
        result = runner.invoke(
            export, [os.path.join(cwd, photos_db_path), ".", "--force-update"]
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: 0, updated: 1, skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7-1}, updated EXIF data: 0, missing: 3, error: 0"
            in result.output
        )

        # update, nothing should export
        result = runner.invoke(
            export, [os.path.join(cwd, photos_db_path), ".", "--update"]
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: 0, updated: 0, skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, updated EXIF data: 0, missing: 3, error: 0"
            in result.output
        )

        # run --force-update, nothing should export
        result = runner.invoke(
            export, [os.path.join(cwd, photos_db_path), ".", "--force-update"]
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: 0, updated: 0, skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, updated EXIF data: 0, missing: 3, error: 0"
            in result.output
        )


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_update_complex():
    """test complex --update scenario, #630"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert os.path.isfile(OSXPHOTOS_EXPORT_DB)

        src = os.path.join(cwd, CLI_PHOTOS_DB)
        dest = os.path.join(os.getcwd(), "export_complex_update.photoslibrary")
        photos_db_path = copy_photos_library_to_path(src, dest)

        tempdir = TemporaryDirectory()

        options = [
            "--verbose",
            "--update",
            "--cleanup",
            "--directory",
            "{created.year}/{created.month}",
            "--description-template",
            "Album:{album,}{newline}Description:{descr,}",
            "--exiftool",
            "--exiftool-merge-keywords",
            "--exiftool-merge-persons",
            "--keyword-template",
            "{keyword}",
            "--not-hidden",
            "--retry",
            "2",
            "--skip-original-if-edited",
            "--timestamp",
            "--strip",
            "--skip-uuid",
            CLI_NOT_REALLY_A_JPEG,
        ]
        # update
        result = runner.invoke(
            export, [os.path.join(cwd, photos_db_path), tempdir.name, *options]
        )
        assert result.exit_code == 0
        assert (
            f"exported: {PHOTOS_NOT_IN_TRASH_LEN_15_7-1}, updated: 0, skipped: 0, updated EXIF data: {PHOTOS_NOT_IN_TRASH_LEN_15_7-1}"
            in result.output
        )

        result = runner.invoke(
            export, [os.path.join(cwd, photos_db_path), tempdir.name, *options]
        )
        assert result.exit_code == 0
        assert "exported: 0" in result.output

        # update a file
        dbpath = os.path.join(photos_db_path, "database/Photos.sqlite")
        try:
            conn = sqlite3.connect(dbpath)
            c = conn.cursor()
        except sqlite3.Error as e:
            pytest.exit(f"An error occurred opening sqlite file")

        # photo is IMG_4547.jpg
        c.execute(
            "UPDATE ZADDITIONALASSETATTRIBUTES SET Z_OPT=9, ZTITLE='My Updated Title' WHERE Z_PK=8;"
        )
        conn.commit()

        # run --update to see if updated metadata forced update
        result = runner.invoke(
            export, [os.path.join(cwd, photos_db_path), tempdir.name, *options]
        )
        assert result.exit_code == 0
        assert (
            f"exported: 0, updated: 1, skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7-2}, updated EXIF data: 1"
            in result.output
        )

        # update, nothing should export
        result = runner.invoke(
            export, [os.path.join(cwd, photos_db_path), tempdir.name, *options]
        )
        assert result.exit_code == 0
        assert (
            f"exported: 0, updated: 0, skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7-1}, updated EXIF data: 0"
            in result.output
        )

        # change the template and run again
        options.extend(["--keyword-template", "FOO"])

        # run update and all photos should be updated
        result = runner.invoke(
            export, [os.path.join(cwd, photos_db_path), tempdir.name, *options]
        )
        assert result.exit_code == 0
        assert (
            f"exported: 0, updated: {PHOTOS_NOT_IN_TRASH_LEN_15_7-1}, skipped: 0, updated EXIF data: {PHOTOS_NOT_IN_TRASH_LEN_15_7-1}"
            in result.output
        )


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_EXPORT" not in os.environ,
    reason="Skip if not running on author's personal library.",
)
def test_export_live_edited():
    """test export of edited live image #576"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, LOCAL_PHOTOSDB),
                ".",
                "-V",
                "--uuid",
                UUID_LIVE_EDITED,
                "--download-missing",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_LIVE_EDITED)


def test_export_update_child_folder():
    """test export then update into a child folder of previous export"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0

        os.mkdir("foo")

        # update into foo
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), "foo", "--update"], input="N\n"
        )
        assert result.exit_code != 0
        assert "WARNING: found other export database files" in result.output


def test_export_update_parent_folder():
    """test export then update into a parent folder of previous export"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        os.mkdir("foo")
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), "foo", "-V"])
        assert result.exit_code == 0

        # update into "."
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update"], input="N\n"
        )
        assert result.exit_code != 0
        assert "WARNING: found other export database files" in result.output


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_update_exiftool():
    """test export then update with exiftool"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)

        # update with exiftool
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update", "--exiftool"]
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: 0, updated: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, skipped: 0, updated EXIF data: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, missing: 3, error: 1"
            in result.output
        )

        # update with exiftool again, should be no changes
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update", "--exiftool"]
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: 0, updated: 0, skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, updated EXIF data: 0, missing: 3, error: 0"
            in result.output
        )


def test_export_update_hardlink():
    """test export with hardlink then update"""

    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with isolated_filesystem_here():
        # basic export
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--export-as-hardlink"],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)

        # update, should replace the hardlink files with new copies
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update"]
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: 0, updated: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, skipped: 0, updated EXIF data: 0, missing: 3, error: 0"
            in result.output
        )
        assert not os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_update_hardlink_exiftool():
    """test export with hardlink then update with exiftool"""

    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with isolated_filesystem_here():
        # basic export
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--export-as-hardlink"],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)

        # update, should replace the hardlink files with new copies
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update", "--exiftool"]
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: 0, updated: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, skipped: 0, updated EXIF data: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, missing: 3, error: 1"
            in result.output
        )
        assert not os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)


def test_export_update_edits():
    """test export then update after removing and editing files"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--export-by-date"]
        )
        assert result.exit_code == 0

        # change a couple of destination photos
        os.unlink(CLI_EXPORT_BY_DATE[1])
        shutil.copyfile(CLI_EXPORT_BY_DATE[0], CLI_EXPORT_BY_DATE[1])
        os.unlink(CLI_EXPORT_BY_DATE[0])

        # update
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update", "--export-by-date"],
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: 1, updated: 1, skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7-2}, updated EXIF data: 0, missing: 3, error: 0"
            in result.output
        )


@pytest.mark.usefixtures("set_tz_pacific")
def test_export_update_only_new():
    """test --update --only-new"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--to-date",
                "2020-12-20T18:33:41.766684-08:00",
            ],
        )
        assert result.exit_code == 0

        # --update with --only-new --dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--dry-run",
                "--update",
                "--only-new",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 7" in result.output

        # --update with --only-new
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V", "--update", "--only-new"],
        )
        assert result.exit_code == 0
        assert "exported: 7" in result.output

        # --update with --only-new, should export nothing
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V", "--update", "--only-new"],
        )
        assert result.exit_code == 0
        assert "exported: 0" in result.output


def test_export_update_no_db():
    """test export then update after db has been deleted"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert os.path.isfile(OSXPHOTOS_EXPORT_DB)
        os.unlink(OSXPHOTOS_EXPORT_DB)

        # update, will re-export all files with different names
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update"]
        )
        assert result.exit_code == 0

        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, updated: 0"
            in result.output
        )
        assert os.path.isfile(OSXPHOTOS_EXPORT_DB)


def test_export_then_hardlink():
    """test export then hardlink"""

    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with isolated_filesystem_here():
        # basic export
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)
        assert not os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)

        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--export-as-hardlink",
                "--overwrite",
            ],
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, missing: 3, error: 0"
            in result.output
        )
        assert os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)


def test_export_dry_run():
    """test export with --dry-run flag"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--dry-run"]
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, missing: 3, error: 0"
            in result.output
        )
        for filepath in CLI_EXPORT_FILENAMES_DRY_RUN:
            assert re.search(r"Exported.*" + f"{re.escape(filepath)}", result.output)
            assert not os.path.isfile(normalize_fs_path(filepath))


def test_export_dry_run_alt_copy():
    """test export with --dry-run flag and --alt-copy"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--alt-copy", "--dry-run"],
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}, missing: 3, error: 0"
            in result.output
        )
        for filepath in CLI_EXPORT_FILENAMES_DRY_RUN:
            assert re.search(r"Exported.*" + f"{re.escape(filepath)}", result.output)
            assert not os.path.isfile(normalize_fs_path(filepath))


def test_export_update_edits_dry_run():
    """test export then update after removing and editing files with dry-run flag"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--export-by-date"]
        )
        assert result.exit_code == 0

        # change a couple of destination photos
        os.unlink(CLI_EXPORT_BY_DATE[1])
        shutil.copyfile(CLI_EXPORT_BY_DATE[0], CLI_EXPORT_BY_DATE[1])
        os.unlink(CLI_EXPORT_BY_DATE[0])

        # update dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "--update",
                "--export-by-date",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert (
            f"Processed: {PHOTOS_NOT_IN_TRASH_LEN_15_7} photos, exported: 1, updated: 1, skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7-2}, updated EXIF data: 0, missing: 3, error: 0"
            in result.output
        )

        # make sure file didn't really get copied
        assert not os.path.isfile(CLI_EXPORT_BY_DATE[0])


def test_export_directory_template_1_dry_run():
    """test export using directory template with dry-run flag"""

    setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--directory",
                "{created.year}/{created.month}",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert (
            f"exported: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}"
            in result.output
        )
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES1:
            assert re.search(r"Exported.*" + f"{filepath}", result.output)
            assert not os.path.isfile(os.path.join(workdir, filepath))


@pytest.mark.usefixtures("set_tz_pacific")
def test_export_touch_files():
    """test export with --touch-files"""

    setup_touch_tests()

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_TOUCH),
                ".",
                "-V",
                "--touch-file",
                "--export-by-date",
            ],
        )
        assert result.exit_code == 0

        assert (
            f"exported: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}"
            in result.output
        )

        # on macOS there are two files that have the correct date and these don't get touched
        # on other platforms, all files get touched
        touched_files = (
            PHOTOS_NOT_IN_TRASH_LEN_15_7 + PHOTOS_EDITED_15_7 - 2
            if is_macos
            else PHOTOS_NOT_IN_TRASH_LEN_15_7 + PHOTOS_EDITED_15_7
        )

        assert f"touched date: {touched_files}" in result.output

        for fname, mtime in zip(CLI_EXPORT_BY_DATE, CLI_EXPORT_BY_DATE_TOUCH_TIMES):
            st = os.stat(fname)
            assert int(st.st_mtime) == int(mtime)


@pytest.mark.usefixtures("set_tz_pacific")
def test_export_touch_files_update():
    """test complex export scenario with --update and --touch-files"""

    setup_touch_tests()

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export with dry-run
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_TOUCH), ".", "--export-by-date", "--dry-run"],
        )
        assert result.exit_code == 0

        assert (
            f"exported: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}"
            in result.output
        )

        assert not pathlib.Path(CLI_EXPORT_BY_DATE[0]).is_file()

        # without dry-run
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_TOUCH), ".", "--export-by-date"]
        )
        assert result.exit_code == 0

        assert (
            f"exported: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}"
            in result.output
        )

        assert pathlib.Path(CLI_EXPORT_BY_DATE[0]).is_file()

        # --update
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_TOUCH), ".", "--export-by-date", "--update"],
        )
        assert result.exit_code == 0

        assert (
            f"skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}"
            in result.output
        )

        # --update --touch-file --dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_TOUCH),
                ".",
                "--export-by-date",
                "--update",
                "--touch-file",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert (
            f"skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}"
            in result.output
        )

        # on macOS there are two files that have the correct date and these don't get touched
        # on other platforms, all files get touched
        touched_files = (
            PHOTOS_NOT_IN_TRASH_LEN_15_7 + PHOTOS_EDITED_15_7 - 2
            if is_macos
            else PHOTOS_NOT_IN_TRASH_LEN_15_7 + PHOTOS_EDITED_15_7
        )

        assert f"touched date: {touched_files}" in result.output

        for fname, mtime in zip(
            CLI_EXPORT_BY_DATE_NEED_TOUCH, CLI_EXPORT_BY_DATE_NEED_TOUCH_TIMES
        ):
            st = os.stat(fname)
            assert int(st.st_mtime) != int(mtime)

        # --update --touch-file
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_TOUCH),
                ".",
                "--export-by-date",
                "--update",
                "--touch-file",
            ],
        )
        assert result.exit_code == 0
        assert (
            f"skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}"
            in result.output
        )
        assert f"touched date: {touched_files}" in result.output

        for fname, mtime in zip(
            CLI_EXPORT_BY_DATE_NEED_TOUCH, CLI_EXPORT_BY_DATE_NEED_TOUCH_TIMES
        ):
            st = os.stat(fname)
            assert int(st.st_mtime) == int(mtime)

        # touch one file and run update again
        ts = time.time()
        os.utime(CLI_EXPORT_BY_DATE_NEED_TOUCH[1], (ts, ts))

        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_TOUCH),
                ".",
                "--export-by-date",
                "--update",
                "--touch-file",
            ],
        )
        assert result.exit_code == 0
        assert (
            f"updated: 1, skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7-1}"
            in result.output
        )
        assert "touched date: 1" in result.output

        for fname, mtime in zip(CLI_EXPORT_BY_DATE, CLI_EXPORT_BY_DATE_TOUCH_TIMES):
            st = os.stat(fname)
            assert int(st.st_mtime) == int(mtime)

        # run update without --touch-file
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_TOUCH), ".", "--export-by-date", "--update"],
        )
        assert result.exit_code == 0

        assert (
            f"skipped: {PHOTOS_NOT_IN_TRASH_LEN_15_7+PHOTOS_EDITED_15_7}"
            in result.output
        )


@pytest.mark.usefixtures("set_tz_pacific")
@pytest.mark.skip("TODO: This fails on some machines but not all")
# @pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_touch_files_exiftool_update():
    """test complex export scenario with --update, --exiftool, and --touch-files"""

    setup_touch_tests()

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # basic export with dry-run
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_TOUCH), ".", "--export-by-date", "--dry-run"],
        )
        assert result.exit_code == 0

        assert "exported: 18" in result.output

        assert not pathlib.Path(CLI_EXPORT_BY_DATE[0]).is_file()

        # without dry-run
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_TOUCH), ".", "--export-by-date"]
        )
        assert result.exit_code == 0

        assert "exported: 18" in result.output

        assert pathlib.Path(CLI_EXPORT_BY_DATE[0]).is_file()

        # --update
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_TOUCH), ".", "--export-by-date", "--update"],
        )
        assert result.exit_code == 0

        assert "skipped: 19" in result.output

        # --update --exiftool --dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_TOUCH),
                ".",
                "--export-by-date",
                "--update",
                "--exiftool",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

        assert "updated: 18" in result.output
        assert "updated EXIF data: 18" in result.output

        # --update --exiftool
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_TOUCH),
                ".",
                "--export-by-date",
                "--update",
                "--exiftool",
            ],
        )
        assert result.exit_code == 0
        assert "updated: 18" in result.output
        assert "updated EXIF data: 18" in result.output

        # --update --touch-file --exiftool --dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_TOUCH),
                ".",
                "--export-by-date",
                "--update",
                "--exiftool",
                "--touch-file",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "skipped: 19" in result.output
        assert "touched date: 18" in result.output

        # --update --touch-file --exiftool
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_TOUCH),
                ".",
                "--export-by-date",
                "--update",
                "--exiftool",
                "--touch-file",
            ],
        )
        assert result.exit_code == 0
        assert "skipped: 19" in result.output
        assert "touched date: 18" in result.output

        for fname, mtime in zip(CLI_EXPORT_BY_DATE, CLI_EXPORT_BY_DATE_TOUCH_TIMES):
            st = os.stat(fname)
            assert int(st.st_mtime) == int(mtime)

        # touch one file and run update again
        ts = time.time()
        os.utime(CLI_EXPORT_BY_DATE[0], (ts, ts))

        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_TOUCH),
                ".",
                "--export-by-date",
                "--update",
                "--exiftool",
                "--touch-file",
            ],
        )
        assert result.exit_code == 0
        assert "updated: 1" in result.output
        assert "skipped: 17" in result.output
        assert "updated EXIF data: 1" in result.output
        assert "touched date: 1" in result.output

        for fname, mtime in zip(CLI_EXPORT_BY_DATE, CLI_EXPORT_BY_DATE_TOUCH_TIMES):
            st = os.stat(fname)
            assert int(st.st_mtime) == int(mtime)

        # run --update --exiftool --touch-file again
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_TOUCH),
                ".",
                "--export-by-date",
                "--update",
                "--exiftool",
                "--touch-file",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 0" in result.output
        assert "skipped: 19" in result.output

        # run update without --touch-file
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_TOUCH),
                ".",
                "--export-by-date",
                "--exiftool",
                "--update",
            ],
        )
        assert result.exit_code == 0

        assert "exported: 0" in result.output
        assert "skipped: 19" in result.output


def test_export_ignore_signature():
    """test export with --ignore-signature"""

    runner = CliRunner()
    cwd = os.getcwd()

    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # first, export some files
        result = runner.invoke(export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V"])
        assert result.exit_code == 0

        # modify a couple of files
        for filename in CLI_EXPORT_IGNORE_SIGNATURE_FILENAMES:
            modify_file(f"./{filename}")

        # export with --update and --ignore-signature
        # which should ignore the two modified files
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--update",
                "--ignore-signature",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 0, updated: 0" in result.output

        # export with --update and not --ignore-signature
        # which should updated the two modified files
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V", "--update"]
        )
        assert result.exit_code == 0
        assert "updated: 2" in result.output

        # run --update again, should be 0 files exported
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V", "--update"]
        )
        assert result.exit_code == 0
        assert "exported: 0, updated: 0" in result.output


def test_export_ignore_signature_sidecar():
    """test export with --ignore-signature and --sidecar"""
    """
    Test the following use cases: 
    If the metadata (in Photos) that went into the sidecar did not change, the sidecar will not be updated
    If the metadata (in Photos) that went into the sidecar did change, a new sidecar is written but a new image file is not
    If a sidecar does not exist for the photo, a sidecar will be written whether or not the photo file was written
    """

    runner = CliRunner()
    cwd = os.getcwd()

    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # first, export some files
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V", "--sidecar", "XMP"]
        )
        assert result.exit_code == 0

        # export with --update and --ignore-signature
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--update",
                "--sidecar",
                "XMP",
                "--ignore-signature",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 0, updated: 0" in result.output
        assert "Writing XMP sidecar" not in result.output

        # modify a couple of files
        for filename in CLI_EXPORT_IGNORE_SIGNATURE_FILENAMES:
            modify_file(f"./{filename}")

        # export with --update and --ignore-signature
        # which should ignore the two modified files
        # sidecar files should not be re-written
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--update",
                "--sidecar",
                "XMP",
                "--ignore-signature",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 0" in result.output
        assert "Writing XMP sidecar" not in result.output

        # change the sidecar data in export DB
        # should result in a new sidecar being exported but not the image itself
        exportdb = osxphotos.export_db.ExportDB("./.osxphotos_export.db", ".")
        for filename in CLI_EXPORT_IGNORE_SIGNATURE_FILENAMES:
            record = exportdb.get_file_record(filename)
            sidecar_record = exportdb.create_or_get_file_record(
                f"{filename}.xmp", record.uuid
            )
            sidecar_record.dest_sig = (0, 1, 2)
            sidecar_record.digest = "FOO"

        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--update",
                "--ignore-signature",
                "--sidecar",
                "XMP",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 0, updated: 0" in result.output
        assert result.output.count("Writing XMP sidecar") == len(
            CLI_EXPORT_IGNORE_SIGNATURE_FILENAMES
        )

        # run --update again, should be 0 files exported
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--update",
                "--ignore-signature",
                "--sidecar",
                "XMP",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 0, updated: 0" in result.output
        assert "Writing XMP sidecar" not in result.output

        # remove XMP files and run again to verify the files get written
        for filename in CLI_EXPORT_IGNORE_SIGNATURE_FILENAMES:
            os.unlink(f"./{filename}.xmp")

        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--update",
                "--ignore-signature",
                "--sidecar",
                "XMP",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 0, updated: 0" in result.output
        assert result.output.count("Writing XMP sidecar") == len(
            CLI_EXPORT_IGNORE_SIGNATURE_FILENAMES
        )


def test_labels():
    """Test osxphotos labels"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        labels, ["--db", os.path.join(cwd, PHOTOS_DB_15_7), "--json"]
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert json_got == LABELS_JSON


def test_keywords():
    """Test osxphotos keywords"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        keywords, ["--db", os.path.join(cwd, PHOTOS_DB_15_7), "--json"]
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert json_got == KEYWORDS_JSON


def test_albums_json():
    """Test osxphotos albums json output"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        albums, ["--db", os.path.join(cwd, PHOTOS_DB_15_7), "--json"]
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert json_got == ALBUMS_JSON


def test_persons():
    """Test osxphotos persons"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        persons, ["--db", os.path.join(cwd, PHOTOS_DB_15_7), "--json"]
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert json_got == PERSONS_JSON


def test_export_report():
    """test export with --report option"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # test report creation
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                UUID_REPORT[0]["uuid"],
                "--report",
                "report.csv",
            ],
        )
        assert result.exit_code == 0
        assert "Wrote export report" in result.output
        assert os.path.exists("report.csv")
        with open("report.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert sorted(filenames) == sorted(UUID_REPORT[0]["filenames"])

        # test report gets overwritten
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                UUID_REPORT[1]["uuid"],
                "--report",
                "report.csv",
            ],
        )
        assert result.exit_code == 0
        with open("report.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert sorted(filenames) == sorted(UUID_REPORT[1]["filenames"])

        # test report with --append
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                UUID_REPORT[0]["uuid"],
                "--report",
                "report.csv",
                "--overwrite",
                "--append",
            ],
        )
        assert result.exit_code == 0
        with open("report.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert sorted(filenames) == sorted(
            UUID_REPORT[0]["filenames"] + UUID_REPORT[1]["filenames"]
        )


def test_export_report_json():
    """test export with --report option for JSON report"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # test report creation
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                UUID_REPORT[0]["uuid"],
                "--report",
                "report.json",
            ],
        )
        assert result.exit_code == 0
        assert "Wrote export report" in result.output
        assert os.path.exists("report.json")
        with open("report.json", "r") as f:
            rows = json.load(f)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert sorted(filenames) == sorted(UUID_REPORT[0]["filenames"])

        # test report gets overwritten
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                UUID_REPORT[1]["uuid"],
                "--report",
                "report.json",
            ],
        )
        assert result.exit_code == 0
        with open("report.json", "r") as f:
            rows = json.load(f)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert sorted(filenames) == sorted(UUID_REPORT[1]["filenames"])

        # test report with --append
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                UUID_REPORT[0]["uuid"],
                "--report",
                "report.json",
                "--overwrite",
                "--append",
            ],
        )
        assert result.exit_code == 0
        with open("report.json", "r") as f:
            rows = json.load(f)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert sorted(filenames) == sorted(
            UUID_REPORT[0]["filenames"] + UUID_REPORT[1]["filenames"]
        )


@pytest.mark.parametrize("report_file", ["report.db", "report.sqlite"])
def test_export_report_sqlite(report_file):
    """test export with --report option with sqlite report"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # test report creation
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                UUID_REPORT[0]["uuid"],
                "--report",
                report_file,
            ],
        )
        assert result.exit_code == 0
        assert "Wrote export report" in result.output
        assert os.path.exists(report_file)
        conn = sqlite3.connect(report_file)
        c = conn.cursor()
        c.execute("SELECT filename FROM report")
        filenames = [str(pathlib.Path(row[0]).name) for row in c.fetchall()]
        assert sorted(filenames) == sorted(UUID_REPORT[0]["filenames"])

        # test report gets overwritten
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                UUID_REPORT[1]["uuid"],
                "--report",
                report_file,
            ],
        )
        assert result.exit_code == 0
        conn = sqlite3.connect(report_file)
        c = conn.cursor()
        c.execute("SELECT filename FROM report")
        filenames = [str(pathlib.Path(row[0]).name) for row in c.fetchall()]
        assert sorted(filenames) == sorted(UUID_REPORT[1]["filenames"])

        # test report with --append
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                UUID_REPORT[0]["uuid"],
                "--report",
                report_file,
                "--overwrite",
                "--append",
            ],
        )
        assert result.exit_code == 0
        conn = sqlite3.connect(report_file)
        c = conn.cursor()
        c.execute("SELECT filename FROM report")
        filenames = [str(pathlib.Path(row[0]).name) for row in c.fetchall()]
        assert sorted(filenames) == sorted(
            UUID_REPORT[0]["filenames"] + UUID_REPORT[1]["filenames"]
        )


def test_export_report_template():
    """test export with --report option with a template for report name"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--report",
                "report_{osxphotos_version}.csv",
            ],
        )
        assert result.exit_code == 0
        assert "Wrote export report" in result.output
        assert os.path.exists(f"report_{__version__}.csv")


def test_export_report_not_a_file():
    """test export with --report option and bad report value"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--report", "."]
        )
        assert result.exit_code != 0
        assert "is a directory, must be file name" in result.output


def test_export_as_hardlink_download_missing():
    """test export with incompatible export options"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with isolated_filesystem_here():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--download-missing",
                "--export-as-hardlink",
                ".",
            ],
        )
        assert result.exit_code != 0
        assert "Incompatible export options" in result.output


def test_export_missing_not_download_missing():
    """test export with incompatible export options"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--missing",
                "--dry-run",
                ".",
            ],
        )
        assert result.exit_code != 0
        assert "Incompatible export options" in result.output


def test_export_not_missing():
    """test export with --not-missing"""
    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--not-missing", "--dry-run"],
        )
        assert result.exit_code == 0
        assert f"Exporting {PHOTOS_NOT_MISSING_15_7} photos" in result.output


def test_export_cleanup():
    """test export with --cleanup flag"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0

        # create 2 files and a directory
        with open("delete_me.txt", "w") as fd:
            fd.write("delete me!")
        os.mkdir("./foo")
        with open("foo/delete_me_too.txt", "w") as fd:
            fd.write("delete me too!")

        assert pathlib.Path("./delete_me.txt").is_file()
        # run cleanup with dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--update",
                "--cleanup",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Deleted: 2 files, 0 directories" in result.output
        assert pathlib.Path("./delete_me.txt").is_file()
        assert pathlib.Path("./foo/delete_me_too.txt").is_file()

        # run cleanup without dry-run
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--update", "--cleanup"],
        )
        assert "Deleted: 2 files, 1 directory" in result.output
        assert not pathlib.Path("./delete_me.txt").is_file()
        assert not pathlib.Path("./foo/delete_me_too.txt").is_file()


def test_export_cleanup_report():
    """test export with --cleanup flag with --report in the export dir (#739)"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0

        tmpdir = os.getcwd()

        # run cleanup without dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--update",
                "--cleanup",
                "--report",
                f"{tmpdir}/report.db",
            ],
        )
        assert "Deleted: 0 files, 0 directories" in result.output
        assert pathlib.Path("./report.db").is_file()


def test_export_cleanup_empty_album():
    """test export with --cleanup flag with an empty album (#481)"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0

        # run cleanup with dry-run
        with tempfile.TemporaryDirectory() as tempdir:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, CLI_PHOTOS_DB),
                    tempdir,
                    "-V",
                    "--uuid",
                    UUID_LOCATION,
                ],
            )

            # run cleanup with an empty folder
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, CLI_PHOTOS_DB),
                    tempdir,
                    "-V",
                    "--update",
                    "--cleanup",
                    "--album",
                    "EmptyAlbum",
                ],
            )
            assert "Did not find any photos to export" in result.output
            assert "Deleted: 1 file" in result.output


def test_export_cleanup_accented_album_name():
    """test export with --cleanup flag and photos in album with accented unicode characters (#561, #618)"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with tempfile.TemporaryDirectory() as tempdir:
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                tempdir,
                "-V",
                "--update",
                "--cleanup",
                "--directory",
                "{folder_album}",
            ],
        )
        assert "Deleted: 0 files, 0 directories" in result.output

        # do it again
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                tempdir,
                "-V",
                "--update",
                "--cleanup",
                "--directory",
                "{folder_album}",
                "--update",
            ],
        )
        assert "exported: 0, updated: 0" in result.output
        assert "Deleted: 0 files, 0 directories" in result.output


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_cleanup_exiftool_accented_album_name_same_filenames():
    """test export with --cleanup flag and photos in album with accented unicode characters (#561, #618)"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with tempfile.TemporaryDirectory() as report_dir:
        # keep report file out of of expor dir for --cleanup
        report_file = os.path.join(report_dir, "test.csv")
        with tempfile.TemporaryDirectory() as tempdir:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, CLI_PHOTOS_DB),
                    tempdir,
                    "-V",
                    "--cleanup",
                    "--directory",
                    "{album[/,.|:,.]}",
                    "--exiftool",
                    "--exiftool-merge-keywords",
                    "--exiftool-merge-persons",
                    "--keyword-template",
                    "{keyword}",
                    "--report",
                    report_file,
                    "--skip-original-if-edited",
                    "--update",
                    "--touch-file",
                    "--not-hidden",
                ],
            )
            assert "Deleted: 0 files, 0 directories" in result.output

            # do it again
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, CLI_PHOTOS_DB),
                    tempdir,
                    "-V",
                    "--cleanup",
                    "--directory",
                    "{album[/,.|:,.]}",
                    "--exiftool",
                    "--exiftool-merge-keywords",
                    "--exiftool-merge-persons",
                    "--keyword-template",
                    "{keyword}",
                    "--report",
                    report_file,
                    "--skip-original-if-edited",
                    "--update",
                    "--touch-file",
                    "--not-hidden",
                ],
            )
            assert "exported: 0, updated: 0" in result.output
            assert "updated EXIF data: 0" in result.output
            assert "Deleted: 0 files, 0 directories" in result.output


def test_export_cleanup_keep():
    """test export with --cleanup --keep options"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        tmpdir = os.getcwd()
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0

        # create file and a directory that should be deleted
        os.mkdir("./empty_dir")
        os.mkdir("./delete_me_dir")
        with open("./delete_me.txt", "w") as fd:
            fd.write("delete me!")
        with open("./delete_me_dir/delete_me.txt", "w") as fd:
            fd.write("delete me!")

        # create files and directories that should be kept
        os.mkdir("./keep_me")
        os.mkdir("./keep_me/keep_me_2")
        with open("./keep_me.txt", "w") as fd:
            fd.write("keep me!")
        with open("./report.db", "w") as fd:
            fd.write("keep me!")
        with open("./keep_me/keep_me.txt", "w") as fd:
            fd.write("keep me")

        # run cleanup with dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--update",
                "--cleanup",
                "--keep",
                f"{tmpdir}/keep_me",
                "--keep",
                f"{tmpdir}/keep_me.txt",
                "--keep",
                f"{tmpdir}/*.db",
                "--dry-run",
            ],
        )
        assert "Deleted: 2 files, 1 directory" in result.output
        assert pathlib.Path("./delete_me.txt").is_file()
        assert pathlib.Path("./delete_me_dir/delete_me.txt").is_file()
        assert pathlib.Path("./empty_dir").is_dir()

        # run cleanup without dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--update",
                "--cleanup",
                "--keep",
                f"{tmpdir}/keep_me",
                "--keep",
                f"{tmpdir}/keep_me.txt",
                "--keep",
                f"{tmpdir}/*.db",
            ],
        )
        assert "Deleted: 2 files, 2 directories" in result.output
        assert not pathlib.Path("./delete_me.txt").is_file()
        assert not pathlib.Path("./delete_me_dir/delete_me_too.txt").is_file()
        assert not pathlib.Path("./empty_dir").is_dir()
        assert pathlib.Path("./keep_me.txt").is_file()
        assert pathlib.Path("./keep_me").is_dir()
        assert pathlib.Path("./keep_me/keep_me.txt").is_file()
        assert pathlib.Path("./keep_me/keep_me_2").is_dir()
        assert pathlib.Path("./report.db").is_file()


def test_export_cleanup_keep_leading_slash():
    """test export with --cleanup --keep options when pattern has leading slash"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        tmpdir = os.getcwd()
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0

        # create file and a directory that should be deleted
        os.mkdir("./empty_dir")
        os.mkdir("./delete_me_dir")
        with open("./delete_me.txt", "w") as fd:
            fd.write("delete me!")
        with open("./delete_me_dir/delete_me.txt", "w") as fd:
            fd.write("delete me!")

        # create files and directories that should be kept
        os.mkdir("./keep_me")
        os.mkdir("./keep_me/keep_me_2")
        with open("./keep_me.txt", "w") as fd:
            fd.write("keep me!")
        with open("./report.db", "w") as fd:
            fd.write("keep me!")
        with open("./keep_me/keep_me.txt", "w") as fd:
            fd.write("keep me")

        # run cleanup with dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--update",
                "--cleanup",
                "--keep",
                f"/keep_me/",
                "--keep",
                f"/keep_me.txt",
                "--keep",
                f"/*.db",
                "--dry-run",
            ],
        )
        assert "Deleted: 2 files, 1 directory" in result.output
        assert pathlib.Path("./delete_me.txt").is_file()
        assert pathlib.Path("./delete_me_dir/delete_me.txt").is_file()
        assert pathlib.Path("./empty_dir").is_dir()

        # run cleanup without dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--update",
                "--cleanup",
                "--keep",
                f"/keep_me/",
                "--keep",
                f"/keep_me.txt",
                "--keep",
                f"/*.db",
            ],
        )
        assert "Deleted: 2 files, 2 directories" in result.output
        assert not pathlib.Path("./delete_me.txt").is_file()
        assert not pathlib.Path("./delete_me_dir/delete_me_too.txt").is_file()
        assert not pathlib.Path("./empty_dir").is_dir()
        assert pathlib.Path("./keep_me.txt").is_file()
        assert pathlib.Path("./keep_me").is_dir()
        assert pathlib.Path("./keep_me/keep_me.txt").is_file()
        assert pathlib.Path("./keep_me/keep_me_2").is_dir()
        assert pathlib.Path("./report.db").is_file()


def test_export_cleanup_keep_relative_path():
    """test export with --cleanup --keep options with relative paths"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0

        # create file and a directory that should be deleted
        os.mkdir("./empty_dir")
        os.mkdir("./delete_me_dir")
        with open("./delete_me.txt", "w") as fd:
            fd.write("delete me!")
        with open("./delete_me_dir/delete_me.txt", "w") as fd:
            fd.write("delete me!")

        # create files and directories that should be kept
        os.mkdir("./keep_me")
        os.mkdir("./keep_me/keep_me_2")
        with open("./keep_me.txt", "w") as fd:
            fd.write("keep me!")
        with open("./report.db", "w") as fd:
            fd.write("keep me!")
        with open("./keep_me/keep_me.txt", "w") as fd:
            fd.write("keep me")

        # for negation rule
        with open("./keep_me/keep_me.db", "w") as fd:
            fd.write("keep me")

        # run cleanup with dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--update",
                "--cleanup",
                "--keep",
                "keep_me/",
                "--keep",
                "keep_me.txt",
                "--keep",
                "*.db",
                "--dry-run",
                "--keep",
                "!keep_me/keep_me.db",
            ],
        )
        assert "Deleted: 3 files, 1 directory" in result.output
        assert pathlib.Path("./delete_me.txt").is_file()
        assert pathlib.Path("./delete_me_dir/delete_me.txt").is_file()
        assert pathlib.Path("./empty_dir").is_dir()

        # run cleanup without dry-run
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--update",
                "--cleanup",
                "--keep",
                "keep_me/",
                "--keep",
                "keep_me.txt",
                "--keep",
                "*.db",
                "--keep",
                "!keep_me/keep_me.db",
            ],
        )
        assert "Deleted: 3 files, 2 directories" in result.output
        assert not pathlib.Path("./delete_me.txt").is_file()
        assert not pathlib.Path("./delete_me_dir/delete_me_too.txt").is_file()
        assert not pathlib.Path("./empty_dir").is_dir()
        assert not pathlib.Path("./keep_me/keep_me.db").is_file()
        assert pathlib.Path("./keep_me.txt").is_file()
        assert pathlib.Path("./keep_me").is_dir()
        assert pathlib.Path("./keep_me/keep_me.txt").is_file()
        assert pathlib.Path("./keep_me/keep_me_2").is_dir()
        assert pathlib.Path("./report.db").is_file()


def test_export_cleanup_exportdb_report():
    """test export with --cleanup flag results show in exportdb --report"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0

        # create 2 files and a directory
        with open("delete_me.txt", "w") as fd:
            fd.write("delete me!")
        os.mkdir("./foo")
        with open("foo/delete_me_too.txt", "w") as fd:
            fd.write("delete me too!")

        assert pathlib.Path("./delete_me.txt").is_file()
        results = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--update", "--cleanup"],
        )
        assert "Deleted: 2 files, 1 directory" in results.output
        assert not pathlib.Path("./delete_me.txt").is_file()
        assert not pathlib.Path("./foo/delete_me_too.txt").is_file()

        results = runner.invoke(
            exportdb,
            [".", "--report", "report.json", "0"],
        )
        assert results.exit_code == 0
        with open("report.json", "r") as fd:
            report = json.load(fd)
        deleted_dirs = [x for x in report if x["cleanup_deleted_directory"]]
        deleted_files = [x for x in report if x["cleanup_deleted_file"]]
        assert len(deleted_dirs) == 1
        assert len(deleted_files) == 2


def test_export_cleanup_osxphotos_keep():
    """test export with --cleanup with a .osxphotos_keep file"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        tmpdir = os.getcwd()
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0

        # create file and a directory that should be deleted
        os.mkdir("./empty_dir")
        os.mkdir("./delete_me_dir")
        with open("./delete_me.txt", "w") as fd:
            fd.write("delete me!")
        with open("./delete_me_dir/delete_me.txt", "w") as fd:
            fd.write("delete me!")

        # create files and directories that should be kept
        os.mkdir("./keep_me")
        os.mkdir("./keep_me/keep_me_2")
        with open("./keep_me.txt", "w") as fd:
            fd.write("keep me!")
        with open("./report.db", "w") as fd:
            fd.write("keep me!")
        with open("./keep_me/keep_me.txt", "w") as fd:
            fd.write("keep me")

        with open(".osxphotos_keep", "w") as fd:
            fd.write("/keep_me/\n")
            fd.write("/keep_me.txt\n")
            fd.write("/*.db\n")

        # run cleanup with dry-run
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, CLI_PHOTOS_DB),
                "-V",
                "--update",
                "--cleanup",
                "--dry-run",
            ],
        )
        assert "Deleted: 2 files, 1 directory" in result.output
        assert pathlib.Path("./delete_me.txt").is_file()
        assert pathlib.Path("./delete_me_dir/delete_me.txt").is_file()
        assert pathlib.Path("./empty_dir").is_dir()

        # run cleanup without dry-run
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, CLI_PHOTOS_DB),
                "-V",
                "--update",
                "--cleanup",
            ],
        )
        assert "Deleted: 2 files, 2 directories" in result.output
        assert not pathlib.Path("./delete_me.txt").is_file()
        assert not pathlib.Path("./delete_me_dir/delete_me_too.txt").is_file()
        assert not pathlib.Path("./empty_dir").is_dir()
        assert pathlib.Path("./keep_me.txt").is_file()
        assert pathlib.Path("./keep_me").is_dir()
        assert pathlib.Path("./keep_me/keep_me.txt").is_file()
        assert pathlib.Path("./keep_me/keep_me_2").is_dir()
        assert pathlib.Path("./report.db").is_file()


def test_export_cleanup_osxphotos_keep_keep():
    """test export with --cleanup with a .osxphotos_keep file and --keep"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        tmpdir = os.getcwd()
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0

        # create file and a directory that should be deleted
        os.mkdir("./empty_dir")
        os.mkdir("./delete_me_dir")
        with open("./delete_me.txt", "w") as fd:
            fd.write("delete me!")
        with open("./delete_me_dir/delete_me.txt", "w") as fd:
            fd.write("delete me!")

        # create files and directories that should be kept
        os.mkdir("./keep_me")
        os.mkdir("./keep_me/keep_me_2")
        with open("./keep_me.txt", "w") as fd:
            fd.write("keep me!")
        with open("./report.db", "w") as fd:
            fd.write("keep me!")
        with open("./keep_me/keep_me.txt", "w") as fd:
            fd.write("keep me")

        with open(".osxphotos_keep", "w") as fd:
            fd.write("/keep_me/\n")
            fd.write("/keep_me.txt\n")

        # run cleanup with dry-run
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, CLI_PHOTOS_DB),
                "-V",
                "--update",
                "--cleanup",
                "--dry-run",
                "--keep",
                "/*.db",
            ],
        )
        assert "Deleted: 2 files, 1 directory" in result.output
        assert pathlib.Path("./delete_me.txt").is_file()
        assert pathlib.Path("./delete_me_dir/delete_me.txt").is_file()
        assert pathlib.Path("./empty_dir").is_dir()

        # run cleanup without dry-run
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, CLI_PHOTOS_DB),
                "-V",
                "--update",
                "--cleanup",
                "--keep",
                "/*.db",
            ],
        )
        assert "Deleted: 2 files, 2 directories" in result.output
        assert not pathlib.Path("./delete_me.txt").is_file()
        assert not pathlib.Path("./delete_me_dir/delete_me_too.txt").is_file()
        assert not pathlib.Path("./empty_dir").is_dir()
        assert pathlib.Path("./keep_me.txt").is_file()
        assert pathlib.Path("./keep_me").is_dir()
        assert pathlib.Path("./keep_me/keep_me.txt").is_file()
        assert pathlib.Path("./keep_me/keep_me_2").is_dir()
        assert pathlib.Path("./report.db").is_file()


def test_save_load_config():
    """test --save-config, --load-config"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # test save config file
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--sidecar",
                "XMP",
                "--touch-file",
                "--update",
                "--save-config",
                "config.toml",
            ],
        )
        assert result.exit_code == 0
        assert "Saving options to config file" in result.output
        files = glob.glob("*")
        assert "config.toml" in files

        # test load config file
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--load-config",
                "config.toml",
            ],
        )
        assert result.exit_code == 0
        assert "Loaded options from file" in result.output
        assert "Skipped up to date XMP sidecar" in result.output

        # test overwrite existing config file
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--sidecar",
                "XMP",
                "--touch-file",
                "--not-live",
                "--update",
                "--save-config",
                "config.toml",
            ],
        )
        assert result.exit_code == 0
        assert "Saving options to config file" in result.output
        files = glob.glob("*")
        assert "config.toml" in files

        # test load config file with incompat command line option
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--load-config",
                "config.toml",
                "--live",
            ],
        )
        assert result.exit_code != 0
        assert "Incompatible export options" in result.output

        # test load config file with command line override
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--load-config",
                "config.toml",
                "--sidecar",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert "Writing JSON sidecar" in result.output
        assert "Writing XMP sidecar" not in result.output


def test_config_only():
    """test --save-config, --config-only"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # test save config file
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--sidecar",
                "XMP",
                "--touch-file",
                "--update",
                "--save-config",
                "config.toml",
                "--config-only",
            ],
        )
        assert result.exit_code == 0
        assert "Saved config file" in result.output
        assert "Processed:" not in result.output
        files = glob.glob("*")
        assert "config.toml" in files


def test_config_command_line_precedence():
    """Test that command line options take precedence over config file"""

    runner = CliRunner()
    cwd = os.getcwd()

    with runner.isolated_filesystem():
        # create a config file
        with open("config.toml", "w") as fd:
            fd.write("[export]\n")
            fd.write(
                "uuid = ["
                + ", ".join(f'"{u}"' for u in UUID_EXPECTED_FROM_FILE)
                + "]\n"
            )

        result = runner.invoke(
            export,
            [
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--load-config",
                "config.toml",
            ],
        )
        assert result.exit_code == 0
        for uuid in UUID_EXPECTED_FROM_FILE:
            assert uuid in result.output

        # now run with a command line option that should override the config file
        result = runner.invoke(
            export,
            [
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--uuid",
                UUID_NOT_FROM_FILE,
                "--load-config",
                "config.toml",
            ],
        )
        assert result.exit_code == 0
        assert UUID_NOT_FROM_FILE in result.output
        for uuid in UUID_EXPECTED_FROM_FILE:
            assert uuid not in result.output


def test_export_exportdb():
    """test --exportdb"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                "--db",
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--exportdb",
                "export.db",
            ],
        )
        assert result.exit_code == 0
        assert re.search(r"Created export database.*export\.db", result.output)
        files = glob.glob("*")
        assert "export.db" in files

        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--exportdb",
                "export.db",
                "--update",
            ],
        )
        assert result.exit_code == 0
        assert re.search(r"Using export database.*export\.db", result.output)

        # export again w/o --exportdb
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        assert re.search(
            r"Created export database.*\.osxphotos_export\.db", result.output
        )
        files = glob.glob(".*")
        assert ".osxphotos_export.db" in files

        # now try again with --exportdb, should generate warning
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--exportdb", "export.db"],
        )
        assert result.exit_code == 0
        assert (
            "Warning: export database is 'export.db' but found '.osxphotos_export.db'"
            in result.output
        )


def test_export_exportdb_ramdb():
    """test --exportdb --ramdb"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--exportdb",
                "export.db",
                "--ramdb",
            ],
        )
        assert result.exit_code == 0
        assert re.search(r"Created export database.*export\.db", result.output)
        files = glob.glob("*")
        assert "export.db" in files

        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--exportdb",
                "export.db",
                "--update",
                "--ramdb",
            ],
        )
        assert result.exit_code == 0
        assert re.search(r"Using export database.*export\.db", result.output)
        assert "exported: 0" in result.output


def test_export_ramdb():
    """test --ramdb"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--ramdb"],
        )
        assert result.exit_code == 0

        # run again, update should update no files if db written back to disk
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--update", "--ramdb"],
        )
        assert result.exit_code == 0
        assert "exported: 0" in result.output

        # run again without --ramdb, update should update no files if db written back to disk
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, CLI_PHOTOS_DB),
                ".",
                "-V",
                "--update",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 0" in result.output


def test_export_finder_tag_keywords_dry_run():
    """test --finder-tag-keywords with --dry-run, #958"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_FINDER_TAGS:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--finder-tag-keywords",
                    "--uuid",
                    f"{uuid}",
                    "--dry-run",
                ],
            )
            assert result.exit_code == 0


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_export_finder_tag_keywords():
    """test --finder-tag-keywords"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_FINDER_TAGS:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--finder-tag-keywords",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0

            md = OSXMetaData(CLI_FINDER_TAGS[uuid]["File:FileName"])
            keywords = CLI_FINDER_TAGS[uuid]["IPTC:Keywords"]
            keywords = [keywords] if type(keywords) != list else keywords
            expected = [Tag(x, 0) for x in keywords]
            assert sorted(md.tags) == sorted(expected)

            # run again with --update, should skip writing extended attributes
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--finder-tag-keywords",
                    "--uuid",
                    f"{uuid}",
                    "--update",
                ],
            )
            assert result.exit_code == 0
            assert "Skipping Finder tags" in result.output

            md = OSXMetaData(CLI_FINDER_TAGS[uuid]["File:FileName"])
            keywords = CLI_FINDER_TAGS[uuid]["IPTC:Keywords"]
            keywords = [keywords] if type(keywords) != list else keywords
            expected = [Tag(x, 0) for x in keywords]
            assert sorted(md.tags) == sorted(expected)

            # clear tags and run again, should update extended attributes
            md.tags = None

            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--finder-tag-keywords",
                    "--uuid",
                    f"{uuid}",
                    "--update",
                ],
            )
            assert result.exit_code == 0
            assert "Writing Finder tags" in result.output

            md = OSXMetaData(CLI_FINDER_TAGS[uuid]["File:FileName"])
            keywords = CLI_FINDER_TAGS[uuid]["IPTC:Keywords"]
            keywords = [keywords] if type(keywords) != list else keywords
            expected = [Tag(x, 0) for x in keywords]
            assert sorted(md.tags) == sorted(expected)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_export_finder_tag_template():
    """test --finder-tag-template"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_FINDER_TAGS:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--finder-tag-template",
                    "{person}",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0

            md = OSXMetaData(CLI_FINDER_TAGS[uuid]["File:FileName"])
            keywords = CLI_FINDER_TAGS[uuid]["XMP:PersonInImage"]
            keywords = [keywords] if type(keywords) != list else keywords
            expected = [Tag(x, 0) for x in keywords]
            assert sorted(md.tags) == sorted(expected)

            # run again with --update, should skip writing extended attributes
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--finder-tag-template",
                    "{person}",
                    "--uuid",
                    f"{uuid}",
                    "--update",
                ],
            )
            assert result.exit_code == 0
            assert "Skipping Finder tags" in result.output

            md = OSXMetaData(CLI_FINDER_TAGS[uuid]["File:FileName"])
            keywords = CLI_FINDER_TAGS[uuid]["XMP:PersonInImage"]
            keywords = [keywords] if type(keywords) != list else keywords
            expected = [Tag(x, 0) for x in keywords]
            assert sorted(md.tags) == sorted(expected)

            # clear tags and run again, should update extended attributes
            md.tags = None

            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--finder-tag-template",
                    "{person}",
                    "--uuid",
                    f"{uuid}",
                    "--update",
                ],
            )
            assert result.exit_code == 0
            assert "Writing Finder tags" in result.output

            md = OSXMetaData(CLI_FINDER_TAGS[uuid]["File:FileName"])
            keywords = CLI_FINDER_TAGS[uuid]["XMP:PersonInImage"]
            keywords = [keywords] if type(keywords) != list else keywords
            expected = [Tag(x, 0) for x in keywords]
            assert sorted(md.tags) == sorted(expected)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_export_finder_tag_template_multiple():
    """test --finder-tag-template used more than once"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_FINDER_TAGS:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--finder-tag-template",
                    "{keyword}",
                    "--finder-tag-template",
                    "{person}",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0

            md = OSXMetaData(CLI_FINDER_TAGS[uuid]["File:FileName"])
            keywords = CLI_FINDER_TAGS[uuid]["IPTC:Keywords"]
            keywords = [keywords] if type(keywords) != list else keywords
            persons = CLI_FINDER_TAGS[uuid]["XMP:PersonInImage"]
            persons = [persons] if type(persons) != list else persons
            expected = [Tag(x, 0) for x in set(keywords + persons)]
            assert sorted(md.tags) == sorted(expected)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_export_finder_tag_template_keywords():
    """test --finder-tag-template with --finder-tag-keywords"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_FINDER_TAGS:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--finder-tag-keywords",
                    "--finder-tag-template",
                    "{person}",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0

            md = OSXMetaData(CLI_FINDER_TAGS[uuid]["File:FileName"])
            keywords = CLI_FINDER_TAGS[uuid]["IPTC:Keywords"]
            keywords = [keywords] if type(keywords) != list else keywords
            persons = CLI_FINDER_TAGS[uuid]["XMP:PersonInImage"]
            persons = [persons] if type(persons) != list else persons
            expected = [Tag(x, 0) for x in set(keywords + persons)]
            assert sorted(md.tags) == sorted(expected)


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_export_finder_tag_template_multi_field():
    """test --finder-tag-template with multiple fields (issue #422)"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_FINDER_TAGS:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--finder-tag-template",
                    "{title};{descr}",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0

            md = OSXMetaData(CLI_FINDER_TAGS[uuid]["File:FileName"])
            title = CLI_FINDER_TAGS[uuid]["XMP:Title"] or ""
            descr = CLI_FINDER_TAGS[uuid]["XMP:Description"] or ""
            expected = [Tag(f"{title};{descr}", 0)]
            assert sorted(md.tags) == sorted(expected)


def test_export_xattr_template_dry_run():
    """test --xattr template with --dry-run, #958"""

    # Note: this test does not actually test that the metadata attributes get correctly
    # written by osxmetadata as osxmetadata doesn't work reliably when run by pytest
    # (but does appear to work correctly in practice)
    # Reference: https://github.com/RhetTbull/osxmetadata/issues/68

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        test_dir = os.getcwd()
        for uuid in CLI_FINDER_TAGS:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--xattr-template",
                    "copyright",
                    "osxphotos 2022",
                    "--xattr-template",
                    "comment",
                    "{title};{descr}",
                    "--uuid",
                    f"{uuid}",
                    "--dry-run",
                ],
            )
            assert result.exit_code == 0
            assert "Writing extended attribute" in result.output


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_export_xattr_template():
    """test --xattr template"""

    # Note: this test does not actually test that the metadata attributes get correctly
    # written by osxmetadata as osxmetadata doesn't work reliably when run by pytest
    # (but does appear to work correctly in practice)
    # Reference: https://github.com/RhetTbull/osxmetadata/issues/68

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        test_dir = os.getcwd()
        for uuid in CLI_FINDER_TAGS:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--xattr-template",
                    "copyright",
                    "osxphotos 2022",
                    "--xattr-template",
                    "comment",
                    "{title};{descr}",
                    "--uuid",
                    f"{uuid}",
                ],
            )
            assert result.exit_code == 0
            assert "Writing extended attribute copyright" in result.output
            assert "Writing extended attribute comment" in result.output

            # run again with --update, should skip writing extended attributes
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--xattr-template",
                    "copyright",
                    "osxphotos 2022",
                    "--xattr-template",
                    "comment",
                    "{title};{descr}",
                    "--uuid",
                    f"{uuid}",
                    "--update",
                ],
            )
            assert result.exit_code == 0

            # clear tags and run again, should update extended attributes
            md = OSXMetaData(
                os.path.join(test_dir, CLI_FINDER_TAGS[uuid]["File:FileName"])
            )
            md.copyright = None
            md.comment = None

            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--xattr-template",
                    "copyright",
                    "osxphotos 2022",
                    "--xattr-template",
                    "comment",
                    "{title}",
                    "--uuid",
                    f"{uuid}",
                    "--update",
                ],
            )
            assert result.exit_code == 0


def test_export_jpeg_ext():
    """test --jpeg-ext"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid, fileinfo in UUID_JPEGS_DICT.items():
            result = runner.invoke(
                export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V", "--uuid", uuid]
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            filename, ext = fileinfo
            assert f"{filename}.{ext}" in files

    for jpeg_ext in ["jpg", "JPG", "jpeg", "JPEG"]:
        with runner.isolated_filesystem():
            for uuid, fileinfo in UUID_JPEGS_DICT.items():
                result = runner.invoke(
                    export,
                    [
                        os.path.join(cwd, PHOTOS_DB_15_7),
                        ".",
                        "-V",
                        "--uuid",
                        uuid,
                        "--jpeg-ext",
                        jpeg_ext,
                    ],
                )
                assert result.exit_code == 0
                files = glob.glob("*")
                filename, ext = fileinfo
                assert f"{filename}.{jpeg_ext}" in files


def test_export_jpeg_ext_not_jpeg():
    """test --jpeg-ext with non-jpeg files"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid, fileinfo in UUID_JPEGS_DICT.items():
            result = runner.invoke(
                export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V", "--uuid", uuid]
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            filename, ext = fileinfo
            assert f"{filename}.{ext}" in files

    for jpeg_ext in ["jpg", "JPG", "jpeg", "JPEG"]:
        with runner.isolated_filesystem():
            for uuid, fileinfo in UUID_JPEGS_DICT_NOT_JPEG.items():
                result = runner.invoke(
                    export,
                    [
                        os.path.join(cwd, PHOTOS_DB_15_7),
                        ".",
                        "-V",
                        "--uuid",
                        uuid,
                        "--jpeg-ext",
                        jpeg_ext,
                    ],
                )
                assert result.exit_code == 0
                files = glob.glob("*")
                filename, ext = fileinfo
                assert f"{filename}.{ext}" in files


def test_export_jpeg_ext_edited_movie():
    """test --jpeg-ext doesn't change extension on edited movie (issue #366)"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid, fileinfo in UUID_MOVIES_NOT_JPEGS_DICT.items():
            result = runner.invoke(
                export, [os.path.join(cwd, PHOTOS_DB_MOVIES), ".", "-V", "--uuid", uuid]
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            files = [f.lower() for f in files]
            filename, ext = fileinfo
            assert f"{filename}_edited.{ext}".lower() in files

    for jpeg_ext in ["jpg", "JPG", "jpeg", "JPEG"]:
        with runner.isolated_filesystem():
            for uuid, fileinfo in UUID_MOVIES_NOT_JPEGS_DICT.items():
                result = runner.invoke(
                    export,
                    [
                        os.path.join(cwd, PHOTOS_DB_MOVIES),
                        ".",
                        "-V",
                        "--uuid",
                        uuid,
                        "--jpeg-ext",
                        jpeg_ext,
                    ],
                )
                assert result.exit_code == 0
                files = glob.glob("*")
                files = [f.lower() for f in files]
                filename, ext = fileinfo
                assert f"{filename}_edited.{jpeg_ext}".lower() not in files
                assert f"{filename}_edited.{ext}".lower() in files


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_CONVERT" not in os.environ,
    reason="Skip if running in Github actions, no GPU.",
)
def test_export_jpeg_ext_convert_to_jpeg():
    """test --jpeg-ext with --convert-to-jpeg"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid, filename in UUID_HEIC.items():
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--uuid",
                    uuid,
                    "--convert-to-jpeg",
                    "--jpeg-ext",
                    "jpg",
                ],
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            assert f"{filename}.jpg" in files


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_CONVERT" not in os.environ,
    reason="Skip if running in Github actions, no GPU.",
)
def test_export_jpeg_ext_convert_to_jpeg_movie():
    """test --jpeg-ext with --convert-to-jpeg and a movie, shouldn't convert or change extensions, #366"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid, fileinfo in UUID_MOVIES_NOT_JPEGS_DICT.items():
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_MOVIES),
                    ".",
                    "-V",
                    "--uuid",
                    uuid,
                    "--convert-to-jpeg",
                    "--jpeg-ext",
                    "jpg",
                ],
            )
            assert result.exit_code == 0
            files = glob.glob("*")
            files = [f.lower() for f in files]
            filename, ext = fileinfo
            assert f"{filename}.jpg".lower() not in files
            assert f"{filename}.{ext}".lower() in files
            assert f"{filename}_edited.{ext}".lower() in files


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_EXPORT_V2" not in os.environ,
    reason="Skip if not running on author's personal library.",
)
def test_export_burst_folder_album(local_photosdb):
    """test non-selected burst photos are exported with the album their key photo is in, issue #401"""

    runner = CliRunner()
    cwd = os.getcwd()
    photos = local_photosdb.query(
        osxphotos.QueryOptions(description=["osxphotos:test_export_burst_folder_album"])
    )
    for photo in photos:
        with runner.isolated_filesystem():
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, LOCAL_PHOTOSDB),
                    ".",
                    "-V",
                    "--directory",
                    "{folder_album}",
                    "--uuid",
                    photo.uuid,
                    "--download-missing",
                    "--use-photokit",
                ],
            )
            assert result.exit_code == 0
            files = [str(p) for p in pathlib.Path(".").glob("**/*.JPG")]
            expected = []
            for p in [photo, *photo.burst_photos]:
                paths, _ = p.render_template("{folder_album}/{photo.original_filename}")
                expected.extend(paths)
            assert sorted(files) == sorted(expected)


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_EXPORT_V2" not in os.environ,
    reason="Skip if not running on author's personal library.",
)
def test_export_burst_uuid(local_photosdb: osxphotos.PhotosDB):
    """test non-selected burst photos are exported when image is specified by --uuid, #640"""

    runner = CliRunner()
    cwd = os.getcwd()
    photos = local_photosdb.query(
        osxphotos.QueryOptions(description=["osxphotos:test_export_burst_uuid"])
    )
    for photo in photos:
        with runner.isolated_filesystem():
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, LOCAL_PHOTOSDB),
                    ".",
                    "-V",
                    "--uuid",
                    photo.uuid,
                ],
            )
            assert result.exit_code == 0
            expected = len(photo.burst_photos) + 1
            assert f"exported: {expected}" in result.output

            # export again with --skip-bursts
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, LOCAL_PHOTOSDB),
                    ".",
                    "-V",
                    "--uuid",
                    photo.uuid,
                    "--skip-bursts",
                ],
            )
            assert result.exit_code == 0
            assert f"exported: 1" in result.output


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_EXPORT" not in os.environ,
    reason="Skip if not running on author's personal library.",
)
def test_export_download_missing_file_exists():
    """test --download-missing with file exists and --update, issue #456"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager

    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, LOCAL_PHOTOSDB),
                ".",
                "-V",
                "--uuid",
                UUID_DOWNLOAD_MISSING,
                "--download-missing",
                "--use-photos-export",
            ],
        )
        assert result.exit_code == 0

        # export again with --update
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, LOCAL_PHOTOSDB),
                ".",
                "-V",
                "--uuid",
                UUID_DOWNLOAD_MISSING,
                "--download-missing",
                "--use-photos-export",
                "--update",
            ],
        )
        assert result.exit_code == 0
        assert "skipped: 1" in result.output


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_EXPORT" not in os.environ,
    reason="Skip if not running on author's personal library.",
)
def test_export_download_missing_preview():
    """test --download-missing --preview, #564"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager

    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, LOCAL_PHOTOSDB),
                ".",
                "-V",
                "--uuid",
                UUID_DOWNLOAD_MISSING,
                "--download-missing",
                "--use-photos-export",
                "--use-photokit",
                "--preview",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 2" in result.output


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_EXPORT" not in os.environ,
    reason="Skip if not running on author's personal library.",
)
def test_export_download_missing_preview_applescript():
    """test --download-missing --preview and applescript download, #564"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager

    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, LOCAL_PHOTOSDB),
                ".",
                "-V",
                "--uuid",
                UUID_DOWNLOAD_MISSING,
                "--download-missing",
                "--use-photos-export",
                "--preview",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 2" in result.output


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_EXPORT" not in os.environ,
    reason="Skip if not running on author's personal library.",
)
def test_export_skip_live_photokit():
    """test that --skip-live works with --use-photokit (issue #537)"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    for uuid in UUID_SKIP_LIVE_PHOTOKIT:
        with runner.isolated_filesystem():
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, LOCAL_PHOTOSDB),
                    ".",
                    "-V",
                    "--uuid",
                    uuid,
                    "--use-photos-export",
                    "--use-photokit",
                    "--skip-live",
                    "--skip-original-if-edited",
                    "--convert-to-jpeg",
                ],
            )
            assert result.exit_code == 0
            files = [str(p) for p in pathlib.Path(".").glob("IMG*")]
            assert sorted(files) == sorted(UUID_SKIP_LIVE_PHOTOKIT[uuid])


def test_query_name():
    """test query --name"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--name", "DSC03584"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 1
    assert json_got[0]["original_filename"] == "DSC03584.dng"


def test_query_name_unicode():
    """test query --name with a unicode name"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--name", "Frítest"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 4
    assert normalize_unicode(json_got[0]["original_filename"]).startswith(
        normalize_unicode("Frítest.jpg")
    )


def test_query_name_i():
    """test query --name -i"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--name",
            "dsc03584",
            "-i",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 1
    assert json_got[0]["original_filename"] == "DSC03584.dng"


def test_query_name_original_filename():
    """test query --name only searches original filename on Photos 5+"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--name", "AA"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 4


def test_query_name_original_filename_i():
    """test query --name only searches original filename on Photos 5+ with -i"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--name", "aa", "-i"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 4


def test_export_name():
    """test export --name"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_7), ".", "-V", "--name", "DSC03584"]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == 1


def test_query_eval():
    """test export --query-eval"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--query-eval",
                "'DSC03584' in photo.original_filename",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == 1


def test_bad_query_eval():
    """test export --query-eval with bad input"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--query-eval",
                "'DSC03584' in photo.originalfilename",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid query-eval CRITERIA" in result.output


def test_query_min_size_1():
    """test query --min-size"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--min-size", "10MB"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 4


def test_query_min_size_2():
    """test query --min-size"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--min-size",
            "10_000_000",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 4


def test_query_max_size_1():
    """test query --max-size"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--max-size", "500 kB"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 3


def test_query_max_size_2():
    """test query --max-size"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--max-size", "500_000"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 3


def test_query_min_max_size():
    """test query --max-size with --min-size"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--min-size",
            "48MB",
            "--max-size",
            "49MB",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 1


def test_query_min_size_error():
    """test query --max-size with invalid size"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--min-size", "500 foo"],
    )
    assert result.exit_code != 0


def test_query_regex_1():
    """test query --regex against title"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--regex",
            "I found",
            "{title}",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 1


def test_query_regex_2():
    """test query --regex with no match"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--regex",
            "{title}",
            "i Found",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 0


def test_query_regex_3():
    """test query --regex with --ignore-case"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--regex",
            "i Found",
            "{title}",
            "--ignore-case",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 1


def test_query_regex_4():
    """test query --regex against album"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--regex",
            "^Test",
            "{album}",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 2


def test_query_regex_multiple():
    """test query multiple --regex values (#525)"""

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--regex",
            "I found",
            "{title}",
            "--regex",
            "carry",
            "{title}",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)

    assert len(json_got) == 2


def test_query_function():
    """test query --query-function"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        with open("query1.py", "w") as f:
            f.writelines(
                [
                    "def query(photos):\n",
                    "    return [p for p in photos if 'DSC03584' in p.original_filename]",
                ]
            )
        tmpdir = os.getcwd()
        result = runner.invoke(
            query,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--query-function",
                f"{tmpdir}/query1.py::query",
                "--json",
            ],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)
        assert len(json_got) == 1
        assert json_got[0]["original_filename"] == "DSC03584.dng"


def test_query_added_after():
    """test query --added-after"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    results = runner.invoke(
        query,
        [
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--json",
            "--added-after",
            "2022-02-03",
        ],
    )
    assert results.exit_code == 0
    json_got = json.loads(results.output)
    assert len(json_got) == 4


def test_query_added_before():
    """test query --added-before"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    results = runner.invoke(
        query,
        [
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--json",
            "--added-before",
            "2019-07-28",
        ],
    )
    assert results.exit_code == 0
    json_got = json.loads(results.output)
    assert len(json_got) == 7


def test_query_added_in_last():
    """test query --added-in-last"""

    # Note: ideally, I'd test this with freezegun to verify the time deltas worked but
    # freezegun causes osxphotos tests to crash so we just test that the --added-in-last runs without error

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    results = runner.invoke(
        query,
        [
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--json",
            "--added-in-last",
            "10 years",
        ],
    )
    assert results.exit_code == 0


def test_query_count():
    """Test query --count"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    results = runner.invoke(
        query,
        [
            "--library",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--added-before",
            "2019-07-28",
            "--count",
        ],
    )
    assert results.exit_code == 0
    assert results.output.strip() == "7"


def test_query_count_0():
    """Test query --count with zero results"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    results = runner.invoke(
        query,
        [
            "--library",
            os.path.join(cwd, PHOTOS_DB_15_7),
            "--added-before",
            "1900-01-01",
            "--count",
        ],
    )
    assert results.exit_code == 0
    assert results.output.strip() == "0"


def test_export_export_dir_template():
    """Test {export_dir} template"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        isolated_cwd = os.getcwd()
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--sidecar=json",
                f"--uuid={CLI_UUID_DICT_15_7['template']}",
                "-V",
                "--keyword-template",
                "{person}",
                "--description-template",
                "{export_dir}",
            ],
        )
        assert result.exit_code == 0
        assert os.path.isfile(CLI_TEMPLATE_SIDECAR_FILENAME)
        with open(CLI_TEMPLATE_SIDECAR_FILENAME, "r") as jsonfile:
            exifdata = json.load(jsonfile)
        assert exifdata[0]["XMP:Description"] == isolated_cwd


def test_export_filepath_template():
    """Test {filepath} template"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        isolated_cwd = os.getcwd()
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--sidecar=json",
                f"--uuid={CLI_UUID_DICT_15_7['template']}",
                "-V",
                "--keyword-template",
                "{person}",
                "--description-template",
                "{filepath}",
            ],
        )
        assert result.exit_code == 0
        assert os.path.isfile(CLI_TEMPLATE_SIDECAR_FILENAME)
        with open(CLI_TEMPLATE_SIDECAR_FILENAME, "r") as jsonfile:
            exifdata = json.load(jsonfile)
        assert exifdata[0]["XMP:Description"] == os.path.join(
            isolated_cwd, CLI_TEMPLATE_FILENAME
        )


def test_export_post_command():
    """Test --post-command"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--post-command",
                "exported",
                "echo {filepath.name|shell_quote} >> {export_dir}/exported.txt",
                "--name",
                "Park",
                "--skip-original-if-edited",
            ],
        )
        assert result.exit_code == 0
        with open("exported.txt") as f:
            lines = [line.strip() for line in f]
        assert lines[0] == "St James Park_edited.jpeg"

        # run again with --update to test skipped
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--post-command",
                "skipped",
                "echo {filepath.name|shell_quote} >> {export_dir}/skipped.txt",
                "--name",
                "Park",
                "--skip-original-if-edited",
                "--update",
            ],
        )
        assert result.exit_code == 0
        with open("skipped.txt") as f:
            lines = [line.strip() for line in f]
        assert lines[0] == "St James Park_edited.jpeg"


def test_export_post_command_bad_command():
    """Test --post-command with bad command"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--post-command",
                "exported",
                "false",
                "--name",
                "Park",
                "--skip-original-if-edited",
            ],
        )
        assert result.exit_code != 0


def test_export_post_command_bad_command_continue():
    """Test --post-command with bad command with --post-command-error=continue"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--post-command",
                "exported",
                "false",
                "--post-command-error",
                "continue",
                "--name",
                "wedding",
            ],
        )
        assert result.exit_code == 0
        assert result.output.count("Error running command") == 2


def test_export_post_command_bad_command_break():
    """Test --post-command with bad command with --post-command-error=break"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--post-command",
                "exported",
                "false",
                "--post-command-error",
                "break",
                "--name",
                "wedding",
            ],
        )
        assert result.exit_code == 0
        assert result.output.count("Error running command") == 1


def test_export_post_command_bad_option_1():
    """Test --post-command with bad options"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--post-command",
                "export",  # should be "exported"
                "foobar {filepath.name|shell_quote} >> {export_dir}/exported.txt",
                "--name",
                "Park",
                "--skip-original-if-edited",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output


def test_export_post_command_bad_option_2():
    """Test --post-command with bad options"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--post-command",
                "exported",
                # error in template for command (missing closing curly brace)
                "foobar {filepath.name|shell_quote >> {export_dir}/exported.txt",
                "--name",
                "Park",
                "--skip-original-if-edited",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output


def test_export_post_function():
    """Test --post-function"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        with open("foo1.py", "w") as f:
            f.writelines(
                ["def foo(photo, results, verbose):\n", "    verbose('FOO BAR')\n"]
            )

        tempdir = os.getcwd()
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--post-function",
                f"{tempdir}/foo1.py::foo",
                "--name",
                "Park",
                "--skip-original-if-edited",
                "-V",
            ],
        )
        assert result.exit_code == 0
        assert "FOO BAR" in result.output


def test_export_post_function_exception():
    """Test --post-function that generates an exception"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        with open("bar1.py", "w") as f:
            f.writelines(
                [
                    "def bar(photo, results, verbose):\n",
                    "    raise ValueError('Argh!')\n",
                ]
            )

        tempdir = os.getcwd()
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--post-function",
                f"{tempdir}/bar1.py::bar",
                "--name",
                "Park",
                "--skip-original-if-edited",
                "-V",
            ],
        )
        assert result.exit_code != 0
        assert "Error running post-function" in result.output


def test_export_post_function_bad_value():
    """Test --post-function option validation"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        with open("foo2.py", "w") as f:
            f.writelines(
                [
                    "def foo(photo, results, verbose):\n",
                    "    raise ValueError('Argh!')\n",
                ]
            )

        tempdir = os.getcwd()
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--post-function",
                f"{tempdir}/foo2.py::bar",
                "--name",
                "Park",
                "--skip-original-if-edited",
                "-V",
            ],
        )
        assert result.exit_code != 0
        assert "Could not load function" in result.output


def test_export_post_function_results():
    """Test --post-function with returned ExportResults, uses the post_function in examples/post_function.py"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        tempdir = os.getcwd()
        result = runner.invoke(
            cli_main,
            [
                "export",
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--name",
                "wedding",
                "-V",
                "--post-function",
                f"{cwd}/examples/post_function.py::post_function",
            ],
        )
        assert result.exit_code == 0
        assert "Writing new file" in result.output
        export_files = glob.glob(os.path.join(f"{tempdir}", "*"))
        assert os.path.join(tempdir, "wedding.jpg.new") in export_files

        # run again with --update and --cleanup
        result = runner.invoke(
            cli_main,
            [
                "export",
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--name",
                "wedding",
                "-V",
                "--post-function",
                f"{cwd}/examples/post_function.py::post_function",
                "--update",
                "--cleanup",
            ],
        )
        assert result.exit_code == 0
        assert "Skipping file" in result.output
        assert "Deleted: 0 files" in result.output
        export_files = glob.glob(os.path.join(f"{tempdir}", "*"))
        assert os.path.join(tempdir, "wedding.jpg.new") in export_files


def test_export_directory_template_function():
    """Test --directory with template function"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        with open("foo3.py", "w") as f:
            f.writelines(["def foo(photo, **kwargs):\n", "    return 'foo/bar'"])

        tempdir = os.getcwd()
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "-V",
                "--uuid",
                CLI_EXPORT_UUID,
                "--directory",
                "{function:" + f"{tempdir}" + "/foo3.py::foo}",
            ],
        )
        assert result.exit_code == 0
        assert pathlib.Path(f"foo/bar/{CLI_EXPORT_UUID_FILENAME}").is_file()


def test_export_query_function():
    """Test --query-function"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        with open("query2.py", "w") as f:
            f.writelines(
                [
                    "def query(photos):\n",
                    "    return [p for p in photos if p.title and 'Tulips' in p.title]\n",
                ]
            )

        tempdir = os.getcwd()
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--query-function",
                f"{tempdir}/query2.py::query",
                "-V",
                "--skip-edited",
            ],
        )
        assert result.exit_code == 0
        assert "exported: 1" in result.output


def test_export_album_seq():
    """Test {album_seq} template"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in UUID_DICT_FOLDER_ALBUM_SEQ:
            result = runner.invoke(
                cli_main,
                [
                    "export",
                    "--db",
                    os.path.join(cwd, PHOTOS_DB_15_7),
                    ".",
                    "-V",
                    "--album",
                    UUID_DICT_FOLDER_ALBUM_SEQ[uuid]["album"],
                    "--directory",
                    UUID_DICT_FOLDER_ALBUM_SEQ[uuid]["directory"],
                    "--filename",
                    UUID_DICT_FOLDER_ALBUM_SEQ[uuid]["filename"],
                    "--uuid",
                    uuid,
                ],
            )
        assert result.exit_code == 0
        files = glob.glob(f"{UUID_DICT_FOLDER_ALBUM_SEQ[uuid]['album']}/*")
        assert (
            f"{UUID_DICT_FOLDER_ALBUM_SEQ[uuid]['album']}/{UUID_DICT_FOLDER_ALBUM_SEQ[uuid]['result']}"
            in files
        )


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_description_template():
    """Test for issue #506"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--sidecar=json",
                f"--uuid={UUID_EMPTY_TITLE}",
                "-V",
                "--description-template",
                DESCRIPTION_TEMPLATE_EMPTY_TITLE,
                "--exiftool",
            ],
        )
        assert result.exit_code == 0
        exif = ExifTool(FILENAME_EMPTY_TITLE).asdict()
        assert exif["EXIF:ImageDescription"] == DESCRIPTION_VALUE_EMPTY_TITLE


def test_export_description_template_conditional():
    """Test for issue #506"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli_main,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                ".",
                "--sidecar=json",
                f"--uuid={UUID_EMPTY_TITLE}",
                "-V",
                "--description-template",
                DESCRIPTION_TEMPLATE_TITLE_CONDITIONAL,
                "--sidecar",
                "JSON",
            ],
        )
        assert result.exit_code == 0
        with open(f"{FILENAME_EMPTY_TITLE}.json", "r") as fp:
            json_got = json.load(fp)[0]
            assert (
                json_got["EXIF:ImageDescription"] == DESCRIPTION_VALUE_TITLE_CONDITIONAL
            )


def test_export_min_size_1():
    """test export --min-size"""

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [".", "--db", os.path.join(cwd, PHOTOS_DB_15_7), "--min-size", "10MB"],
        )
        assert result.exit_code == 0
        assert "Exporting 4 photos" in result.output


def test_export_validate_template_1():
    """ "Test CLI validation of template arguments"""

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--filename",
                "{original_names}",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output


def test_export_validate_template_2():
    """ "Test CLI validation of template arguments"""

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--filename",
                "{original_name",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid value" in result.output


def test_theme_list():
    """Test theme --list command"""

    runner = CliRunner()
    temp_file = tempfile.TemporaryFile()
    with runner.isolated_filesystem():
        result = runner.invoke(cli_main, ["theme", "--list"])
        assert result.exit_code == 0
        assert "Dark" in result.output


def test_export_added_after():
    """test export --added-after"""

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--added-after",
                "2022-02-03",
            ],
        )
        assert result.exit_code == 0
        assert "Exporting 4 photos" in result.output


def test_export_added_before():
    """test export --added-before"""

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--added-before",
                "2019-07-28",
            ],
        )
        assert result.exit_code == 0
        assert "Exporting 7 photos" in result.output


def test_export_added_in_last():
    """test export --added-in-last"""

    # can't use freezegun as it causes osxphotos tests to crash so
    # just run export with --added-in-last and verify no errors

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--added-in-last",
                "10 years",
            ],
        )
        assert result.exit_code == 0
        assert "Exporting" in result.output


def test_export_limit():
    """test export --limit"""

    # Use --added-before so test doesn't break if photos added in the future

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--update",
                "--limit",
                "20",
                "--added-before",
                "2022-05-07",
            ],
        )
        assert result.exit_code == 0
        assert "limit: 20/20 exported" in result.output

        result = runner.invoke(
            export,
            [
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--update",
                "--limit",
                "20",
                "--added-before",
                "2022-05-07",
            ],
        )
        assert result.exit_code == 0
        assert "limit: 5/20 exported" in result.output

        result = runner.invoke(
            export,
            [
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--update",
                "--limit",
                "20",
                "--added-before",
                "2022-05-07",
            ],
        )
        assert result.exit_code == 0
        assert "limit: 0/20 exported" in result.output


def test_export_no_keyword():
    """test export --no-keyword"""

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--no-keyword",
                "--added-before",
                "2022-05-05",
            ],
        )
        assert result.exit_code == 0
        assert "Exporting 11" in result.output


def test_export_print():
    """test export --print"""

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--print",
                "uuid: {uuid}",
                "--uuid",
                UUID_FAVORITE,
            ],
        )
        assert result.exit_code == 0
        assert f"uuid: {UUID_FAVORITE}" in result.output


def test_query_print_quiet():
    """test query --print"""

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--print",
                "uuid: {uuid}",
                "--uuid",
                UUID_FAVORITE,
                "--quiet",
            ],
        )
        assert result.exit_code == 0
        assert result.output.strip() == f"uuid: {UUID_FAVORITE}"


def test_query_field():
    """test query --field"""

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--field",
                "uuid",
                "{uuid}",
                "--field",
                "name",
                "{photo.original_filename}",
                "--uuid",
                UUID_FAVORITE,
            ],
        )
        assert result.exit_code == 0
        assert result.output.strip() == f"uuid,name\n{UUID_FAVORITE},{FILE_FAVORITE}"


def test_query_field_json():
    """test query --field --json"""

    runner = CliRunner()
    cwd = os.getcwd()
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_7),
                "--field",
                "uuid",
                "{uuid}",
                "--field",
                "name",
                "{photo.original_filename}",
                "--uuid",
                UUID_FAVORITE,
                "--json",
            ],
        )
        assert result.exit_code == 0
        json_results = json.loads(result.output)
        assert json_results[0]["uuid"] == UUID_FAVORITE
        assert json_results[0]["name"] == FILE_FAVORITE
