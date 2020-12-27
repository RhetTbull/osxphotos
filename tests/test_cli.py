r""" Test the command line interface (CLI) """

import os

import pytest
from click.testing import CliRunner

import osxphotos
from osxphotos.exiftool import get_exiftool_path

CLI_PHOTOS_DB = "tests/Test-10.15.1.photoslibrary"
LIVE_PHOTOS_DB = "tests/Test-Cloud-10.15.1.photoslibrary"
RAW_PHOTOS_DB = "tests/Test-RAW-10.15.1.photoslibrary"
COMMENTS_PHOTOS_DB = "tests/Test-Cloud-10.15.6.photoslibrary"
PLACES_PHOTOS_DB = "tests/Test-Places-Catalina-10_15_1.photoslibrary"
PLACES_PHOTOS_DB_13 = "tests/Test-Places-High-Sierra-10.13.6.photoslibrary"
PHOTOS_DB_15_4 = "tests/Test-10.15.4.photoslibrary"
PHOTOS_DB_15_5 = "tests/Test-10.15.5.photoslibrary"
PHOTOS_DB_15_6 = "tests/Test-10.15.6.photoslibrary"
PHOTOS_DB_15_7 = "tests/Test-10.15.7.photoslibrary"
PHOTOS_DB_TOUCH = PHOTOS_DB_15_6
PHOTOS_DB_14_6 = "tests/Test-10.14.6.photoslibrary"

UUID_FILE = "tests/uuid_from_file.txt"

CLI_OUTPUT_NO_SUBCOMMAND = [
    "Options:",
    "--db <Photos database path>  Specify Photos database path. Path to Photos",
    "library/database can be specified using either",
    "--db or directly as PHOTOS_LIBRARY positional",
    "argument.",
    "--json                       Print output in JSON format.",
    "-v, --version                Show the version and exit.",
    "-h, --help                   Show this message and exit.",
    "Commands:",
    "  albums    Print out albums found in the Photos library.",
    "  dump      Print list of all photos & associated info from the Photos",
    "  export    Export photos from the Photos database.",
    "  help      Print help; for help on commands: help <command>.",
    "  info      Print out descriptive info of the Photos library database.",
    "  keywords  Print out keywords found in the Photos library.",
    "  labels    Print out image classification labels found in the Photos",
    "  list      Print list of Photos libraries found on the system.",
    "  persons   Print out persons (faces) found in the Photos library.",
    "  places    Print out places found in the Photos library.",
    "  query     Query the Photos database using 1 or more search options; if",
]

CLI_OUTPUT_QUERY_UUID = '[{"uuid": "D79B8D77-BFFC-460B-9312-034F2877D35B", "filename": "D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg", "original_filename": "Pumkins2.jpg", "date": "2018-09-28T16:07:07-04:00", "description": "Girl holding pumpkin", "title": "I found one!", "keywords": ["Kids"], "albums": ["Pumpkin Farm", "Test Album", "Multi Keyword"], "persons": ["Katie"], "path": "/tests/Test-10.15.1.photoslibrary/originals/D/D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg", "ismissing": false, "hasadjustments": false, "external_edit": false, "favorite": false, "hidden": false, "latitude": null, "longitude": null, "path_edited": null, "shared": false, "isphoto": true, "ismovie": false, "uti": "public.jpeg", "burst": false, "live_photo": false, "path_live_photo": null, "iscloudasset": false, "incloud": null}]'

CLI_EXPORT_FILENAMES = [
    "Pumkins1.jpg",
    "Pumkins2.jpg",
    "Pumpkins3.jpg",
    "St James Park.jpg",
    "St James Park_edited.jpeg",
    "Tulips.jpg",
    "wedding.jpg",
    "wedding_edited.jpeg",
]

CLI_EXPORT_IGNORE_SIGNATURE_FILENAMES = ["Tulips.jpg", "wedding.jpg"]

CLI_EXPORT_FILENAMES_ALBUM = ["Pumkins1.jpg", "Pumkins2.jpg", "Pumpkins3.jpg"]

CLI_EXPORT_FILENAMES_ALBUM_UNICODE = ["IMG_4547.jpg"]

CLI_EXPORT_FILENAMES_DELETED_TWIN = ["wedding.jpg", "wedding_edited.jpeg"]

CLI_EXPORT_EDITED_SUFFIX = "_bearbeiten"
CLI_EXPORT_EDITED_SUFFIX_TEMPLATE = "{edited?_edited,}"
CLI_EXPORT_ORIGINAL_SUFFIX = "_original"
CLI_EXPORT_ORIGINAL_SUFFIX_TEMPLATE = "{edited?_original,}"

CLI_EXPORT_FILENAMES_EDITED_SUFFIX = [
    "Pumkins1.jpg",
    "Pumkins2.jpg",
    "Pumpkins3.jpg",
    "St James Park.jpg",
    "St James Park_bearbeiten.jpeg",
    "Tulips.jpg",
    "wedding.jpg",
    "wedding_bearbeiten.jpeg",
]

CLI_EXPORT_FILENAMES_EDITED_SUFFIX_TEMPLATE = [
    "Pumkins1.jpg",
    "Pumkins2.jpg",
    "Pumpkins3.jpg",
    "St James Park.jpg",
    "St James Park_edited.jpeg",
    "Tulips.jpg",
    "wedding.jpg",
    "wedding_edited.jpeg",
]

CLI_EXPORT_FILENAMES_ORIGINAL_SUFFIX = [
    "Pumkins1_original.jpg",
    "Pumkins2_original.jpg",
    "Pumpkins3_original.jpg",
    "St James Park_original.jpg",
    "St James Park_edited.jpeg",
    "Tulips_original.jpg",
    "wedding_original.jpg",
    "wedding_edited.jpeg",
]

CLI_EXPORT_FILENAMES_ORIGINAL_SUFFIX_TEMPLATE = [
    "Pumkins1.jpg",
    "Pumkins2.jpg",
    "Pumpkins3.jpg",
    "St James Park_original.jpg",
    "St James Park_edited.jpeg",
    "Tulips.jpg",
    "wedding_original.jpg",
    "wedding_edited.jpeg",
]

CLI_EXPORT_FILENAMES_CURRENT = [
    "1EB2B765-0765-43BA-A90C-0D0580E6172C.jpeg",
    "3DD2C897-F19E-4CA6-8C22-B027D5A71907.jpeg",
    "4D521201-92AC-43E5-8F7C-59BC41C37A96.cr2",
    "4D521201-92AC-43E5-8F7C-59BC41C37A96.jpeg",
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4.jpeg",
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91.cr2",
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91.jpeg",
    "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068.dng",
    "D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg",
    "DC99FBDD-7A52-4100-A5BB-344131646C30.jpeg",
    "DC99FBDD-7A52-4100-A5BB-344131646C30_edited.jpeg",
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51.jpeg",
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51_edited.jpeg",
    "F12384F6-CD17-4151-ACBA-AE0E3688539E.jpeg",
]

CLI_EXPORT_FILENAMES_CONVERT_TO_JPEG = [
    "DSC03584.jpeg",
    "IMG_1693.jpeg",
    "IMG_1994.JPG",
    "IMG_1994.cr2",
    "IMG_1997.JPG",
    "IMG_1997.cr2",
    "IMG_3092.jpeg",
    "IMG_3092_edited.jpeg",
    "IMG_4547.jpg",
    "Pumkins1.jpg",
    "Pumkins2.jpg",
    "Pumpkins3.jpg",
    "St James Park.jpg",
    "St James Park_edited.jpeg",
    "Tulips.jpg",
    "Tulips_edited.jpeg",
    "wedding.jpg",
    "wedding_edited.jpeg",
]

CLI_EXPORT_FILENAMES_CONVERT_TO_JPEG_SKIP_RAW = [
    "DSC03584.jpeg",
    "IMG_1693.jpeg",
    "IMG_1994.JPG",
    "IMG_1997.JPG",
    "IMG_3092.jpeg",
    "IMG_3092_edited.jpeg",
    "IMG_4547.jpg",
    "Pumkins1.jpg",
    "Pumkins2.jpg",
    "Pumpkins3.jpg",
    "St James Park.jpg",
    "St James Park_edited.jpeg",
    "Tulips.jpg",
    "Tulips_edited.jpeg",
    "wedding.jpg",
    "wedding_edited.jpeg",
]

CLI_EXPORT_CONVERT_TO_JPEG_LARGE_FILE = "DSC03584.jpeg"

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES1 = [
    "2019/April/wedding.jpg",
    "2019/July/Tulips.jpg",
    "2018/October/St James Park.jpg",
    "2018/September/Pumpkins3.jpg",
    "2018/September/Pumkins2.jpg",
    "2018/September/Pumkins1.jpg",
]

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_LOCALE = [
    "2019/September/IMG_9975.JPEG",
    "2020/Februar/IMG_1064.JPEG",
    "2016/März/IMG_3984.JPEG",
]

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_ALBUM1 = [
    "Multi Keyword/wedding.jpg",
    "_/Tulips.jpg",
    "_/St James Park.jpg",
    "Pumpkin Farm/Pumpkins3.jpg",
    "Pumpkin Farm/Pumkins2.jpg",
    "Pumpkin Farm/Pumkins1.jpg",
    "Test Album/Pumkins1.jpg",
]

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES_ALBUM2 = [
    "Multi Keyword/wedding.jpg",
    "NOALBUM/Tulips.jpg",
    "NOALBUM/St James Park.jpg",
    "Pumpkin Farm/Pumpkins3.jpg",
    "Pumpkin Farm/Pumkins2.jpg",
    "Pumpkin Farm/Pumkins1.jpg",
    "Test Album/Pumkins1.jpg",
]

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES2 = [
    "St James's Park, Great Britain, Westminster, England, United Kingdom/St James Park.jpg",
    "_/Pumpkins3.jpg",
    "_/Pumkins2.jpg",
    "_/Pumkins1.jpg",
    "_/Tulips.jpg",
    "_/wedding.jpg",
]

CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES3 = [
    "2019/{foo}/wedding.jpg",
    "2019/{foo}/Tulips.jpg",
    "2018/{foo}/St James Park.jpg",
    "2018/{foo}/Pumpkins3.jpg",
    "2018/{foo}/Pumkins2.jpg",
    "2018/{foo}/Pumkins1.jpg",
]


CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES1 = [
    "2019-wedding.jpg",
    "2019-wedding_edited.jpeg",
    "2019-Tulips.jpg",
    "2018-St James Park.jpg",
    "2018-St James Park_edited.jpeg",
    "2018-Pumpkins3.jpg",
    "2018-Pumkins2.jpg",
    "2018-Pumkins1.jpg",
]

CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES2 = [
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

CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES_PATHSEP = [
    "2018-10 - Sponsion, Museum, Frühstück, Römermuseum/IMG_4547.jpg",
    "Folder1/SubFolder2/AlbumInFolder/IMG_4547.jpg",
    "2019-10:11 Paris Clermont/IMG_4547.jpg",
]


CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES_KEYWORD_PATHSEP = [
    "foo:bar/foo:bar_IMG_3092.heic"
]

CLI_EXPORTED_FILENAME_TEMPLATE_LONG_DESCRIPTION = [
    "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. "
    "Aenean commodo ligula eget dolor. Aenean massa. "
    "Cum sociis natoque penatibus et magnis dis parturient montes, "
    "nascetur ridiculus mus. Donec quam felis, ultricies nec, "
    "pellentesque eu, pretium q.tif"
]

CLI_EXPORT_UUID = "D79B8D77-BFFC-460B-9312-034F2877D35B"
CLI_EXPORT_UUID_STATUE = "3DD2C897-F19E-4CA6-8C22-B027D5A71907"
CLI_EXPORT_UUID_KEYWORD_PATHSEP = "7783E8E6-9CAC-40F3-BE22-81FB7051C266"
CLI_EXPORT_UUID_LONG_DESCRIPTION = "8846E3E6-8AC8-4857-8448-E3D025784410"

CLI_EXPORT_UUID_FILENAME = "Pumkins2.jpg"

CLI_EXPORT_BY_DATE_TOUCH_UUID = [
    "1EB2B765-0765-43BA-A90C-0D0580E6172C",  # Pumpkins3.jpg
    "F12384F6-CD17-4151-ACBA-AE0E3688539E",  # Pumkins1.jpg
]
CLI_EXPORT_BY_DATE_TOUCH_TIMES = [1538165373, 1538163349]
CLI_EXPORT_BY_DATE_NEED_TOUCH = [
    "2018/09/28/Pumkins2.jpg",
    "2018/10/13/St James Park.jpg",
]
CLI_EXPORT_BY_DATE_NEED_TOUCH_UUID = [
    "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "DC99FBDD-7A52-4100-A5BB-344131646C30",
]
CLI_EXPORT_BY_DATE_NEED_TOUCH_TIMES = [1538165227, 1539436692]
CLI_EXPORT_BY_DATE = ["2018/09/28/Pumpkins3.jpg", "2018/09/28/Pumkins1.jpg"]

CLI_EXPORT_SIDECAR_FILENAMES = ["Pumkins2.jpg", "Pumkins2.jpg.json", "Pumkins2.jpg.xmp"]

CLI_EXPORT_LIVE = [
    "51F2BEF7-431A-4D31-8AC1-3284A57826AE.jpeg",
    "51F2BEF7-431A-4D31-8AC1-3284A57826AE.mov",
]

CLI_EXPORT_LIVE_ORIGINAL = ["IMG_0728.JPG", "IMG_0728.mov"]

CLI_EXPORT_RAW = ["441DFE2A-A69B-4C79-A69B-3F51D1B9B29C.cr2"]
CLI_EXPORT_RAW_ORIGINAL = ["IMG_0476_2.CR2"]
CLI_EXPORT_RAW_EDITED = [
    "441DFE2A-A69B-4C79-A69B-3F51D1B9B29C.cr2",
    "441DFE2A-A69B-4C79-A69B-3F51D1B9B29C_edited.jpeg",
]
CLI_EXPORT_RAW_EDITED_ORIGINAL = ["IMG_0476_2.CR2", "IMG_0476_2_edited.jpeg"]

CLI_UUID_DICT_15_5 = {
    "intrash": "71E3E212-00EB-430D-8A63-5E294B268554",
    "template": "F12384F6-CD17-4151-ACBA-AE0E3688539E",
}

CLI_TEMPLATE_SIDECAR_FILENAME = "Pumkins1.jpg.json"

CLI_UUID_DICT_14_6 = {"intrash": "3tljdX43R8+k6peNHVrJNQ"}

PHOTOS_NOT_IN_TRASH_LEN_14_6 = 12
PHOTOS_IN_TRASH_LEN_14_6 = 1
PHOTOS_MISSING_14_6 = 1

PHOTOS_NOT_IN_TRASH_LEN_15_5 = 13
PHOTOS_IN_TRASH_LEN_15_5 = 2
PHOTOS_MISSING_15_5 = 2

PHOTOS_NOT_IN_TRASH_LEN_15_6 = 14
PHOTOS_IN_TRASH_LEN_15_6 = 2
PHOTOS_MISSING_15_6 = 1

CLI_PLACES_JSON = """{"places": {"_UNKNOWN_": 1, "Maui, Wailea, Hawai'i, United States": 1, "Washington, District of Columbia, United States": 1}}"""

CLI_EXIFTOOL = {
    "D79B8D77-BFFC-460B-9312-034F2877D35B": {
        "File:FileName": "Pumkins2.jpg",
        "IPTC:Keywords": "Kids",
        "XMP:TagsList": "Kids",
        "XMP:Title": "I found one!",
        "EXIF:ImageDescription": "Girl holding pumpkin",
        "XMP:Description": "Girl holding pumpkin",
        "XMP:PersonInImage": "Katie",
        "XMP:Subject": "Kids",
        "EXIF:GPSLatitudeRef": "N",
        "EXIF:GPSLongitudeRef": "W",
        "EXIF:GPSLatitude": 41.256566,
        "EXIF:GPSLongitude": 95.940257,
    }
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
        "XMP:TagsList": "wedding",
        "IPTC:Keywords": "wedding",
        "XMP:PersonInImage": "Maria",
        "XMP:Subject": "wedding",
        "EXIF:DateTimeOriginal": "2019:04:15 14:40:24",
        "EXIF:CreateDate": "2019:04:15 14:40:24",
        "EXIF:OffsetTimeOriginal": "-04:00",
        "IPTC:DigitalCreationDate": "2019:04:15",
        "IPTC:DateCreated": "2019:04:15",
        "EXIF:ModifyDate": "2019:04:15 14:40:24",
    }
}

CLI_EXIFTOOL_ERROR = ["E2078879-A29C-4D6F-BACB-E3BBE6C3EB91"]

CLI_EXIFTOOL_DUPLICATE_KEYWORDS = {
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": "wedding.jpg"
}

LABELS_JSON = {
    "labels": {
        "Plant": 7,
        "Outdoor": 4,
        "Sky": 3,
        "Tree": 2,
        "Art": 2,
        "Foliage": 2,
        "People": 2,
        "Agriculture": 2,
        "Farm": 2,
        "Food": 2,
        "Vegetable": 2,
        "Pumpkin": 2,
        "Waterways": 1,
        "River": 1,
        "Cloudy": 1,
        "Land": 1,
        "Water Body": 1,
        "Water": 1,
        "Statue": 1,
        "Window": 1,
        "Decorative Plant": 1,
        "Blue Sky": 1,
        "Palm Tree": 1,
        "Flower": 1,
        "Flower Arrangement": 1,
        "Bouquet": 1,
        "Vase": 1,
        "Container": 1,
        "Camera": 1,
        "Child": 1,
        "Clothing": 1,
        "Jeans": 1,
        "Straw Hay": 1,
    }
}

KEYWORDS_JSON = {
    "keywords": {
        "Kids": 4,
        "wedding": 3,
        "London 2018": 1,
        "St. James's Park": 1,
        "England": 1,
        "United Kingdom": 1,
        "UK": 1,
        "London": 1,
        "flowers": 1,
    }
}

ALBUMS_JSON = {
    "albums": {
        "Raw": 4,
        "Pumpkin Farm": 3,
        "Test Album": 2,
        "AlbumInFolder": 2,
        "I have a deleted twin": 1,
        "2018-10 - Sponsion, Museum, Frühstück, Römermuseum": 1,
        "2019-10/11 Paris Clermont": 1,
        "EmptyAlbum": 0,
    },
    "shared albums": {},
}

ALBUMS_STR = """albums:
  Raw: 4
  Pumpkin Farm: 3
  Test Album: 2
  AlbumInFolder: 2
  I have a deleted twin: 1
  2018-10 - Sponsion, Museum, Frühstück, Römermuseum: 1
  EmptyAlbum: 0
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


def modify_file(filename):
    """ appends data to a file to modify it """
    with open(filename, "ab") as fd:
        fd.write(b"foo")


@pytest.fixture(autouse=True)
def reset_globals():
    """ reset globals in __main__ that tests may have changed """
    yield
    osxphotos.__main__.VERBOSE = False


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
    import os
    import time

    import osxphotos

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
    """ perform setup needed for --touch-file tests """
    import os
    import time
    import logging
    import osxphotos

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
    import osxphotos
    from osxphotos.__main__ import cli

    runner = CliRunner()
    result = runner.invoke(cli, [])
    output = result.output

    assert result.exit_code == 0
    for line in CLI_OUTPUT_NO_SUBCOMMAND:
        assert line.strip() in output


def test_osxphotos_help_1():
    # test help command no topic
    import osxphotos
    from osxphotos.__main__ import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["help"])
    output = result.output
    assert result.exit_code == 0
    for line in CLI_OUTPUT_NO_SUBCOMMAND:
        assert line.strip() in output


def test_osxphotos_help_2():
    # test help command valid topic
    import osxphotos
    from osxphotos.__main__ import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["help", "persons"])
    assert result.exit_code == 0
    assert "Print out persons (faces) found in the Photos library." in result.output


def test_osxphotos_help_3():
    # test help command invalid topic
    import osxphotos
    from osxphotos.__main__ import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["help", "foo"])
    assert result.exit_code == 0
    assert "Invalid command: foo" in result.output


def test_query_uuid():
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

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
    """ Test query with --uuid-from-file """
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
            "--uuid-from-file",
            UUID_FILE,
        ],
    )
    assert result.exit_code == 0

    # build list of uuids we got from the output JSON
    json_got = json.loads(result.output)
    uuid_got = [photo["uuid"] for photo in json_got]
    assert sorted(UUID_EXPECTED_FROM_FILE) == sorted(uuid_got)


def test_query_has_comment():
    """ Test query with --has-comment """
    import json
    import os
    import os.path
    from osxphotos.__main__ import query

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
    """ Test query with --no-comment """
    import json
    import os
    import os.path
    from osxphotos.__main__ import query

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
    """ Test query with --has-likes"""
    import json
    import os
    import os.path
    from osxphotos.__main__ import query

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
    """ Test query with --no-likes"""
    import json
    import os
    import os.path
    from osxphotos.__main__ import query

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


def test_export():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V"])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES)


def test_export_uuid_from_file():
    """ Test export with --uuid-from-file """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_5),
                ".",
                "-V",
                "--uuid-from-file",
                os.path.join(cwd, UUID_FILE),
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_UUID_FROM_FILE_FILENAMES)


def test_export_as_hardlink():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
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
    import os
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
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
    import os
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
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
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_4), ".", "--current-name", "-V"]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_CURRENT)


def test_export_skip_edited():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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


def test_export_skip_original_if_edited():
    """ test export with --skip-original-if-edited """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_15_6), ".", "--skip-original-if-edited", "-V"],
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
    import glob
    import os
    import os.path
    from osxphotos.__main__ import export
    from osxphotos.exiftool import ExifTool

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_6),
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
def test_export_exiftool_ignore_date_modified():
    import glob
    import os
    import os.path
    from osxphotos.__main__ import export
    from osxphotos.exiftool import ExifTool

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        for uuid in CLI_EXIFTOOL_IGNORE_DATE_MODIFIED:
            result = runner.invoke(
                export,
                [
                    os.path.join(cwd, PHOTOS_DB_15_6),
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
    """ test --exiftol correctly writes QuickTime tags """
    import glob
    import os
    import os.path
    from osxphotos.__main__ import export
    from osxphotos.exiftool import ExifTool

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
    """ ensure duplicate keywords are removed """
    import glob
    import os
    import os.path
    from osxphotos.__main__ import export
    from osxphotos.exiftool import ExifTool

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
    """" test --exiftool catching error """
    import glob
    import os
    import os.path
    from osxphotos.__main__ import export
    from osxphotos.exiftool import ExifTool

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
    """ test --exiftool-option """
    import glob
    import os
    import os.path
    from osxphotos.__main__ import export
    from osxphotos.exiftool import ExifTool

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


def test_export_edited_suffix():
    """ test export with --edited-suffix """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    """ test export with --edited-suffix template """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    """ test export with --original-suffix """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    """ test export with --original-suffix template """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    """ test --convert-to-jpeg """
    import glob
    import os
    import os.path
    import pathlib
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_6), ".", "-V", "--convert-to-jpeg"]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_CONVERT_TO_JPEG)
        large_file = pathlib.Path(CLI_EXPORT_CONVERT_TO_JPEG_LARGE_FILE)
        assert large_file.stat().st_size > 10000000


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_CONVERT" not in os.environ,
    reason="Skip if running in Github actions, no GPU.",
)
def test_export_convert_to_jpeg_quality():
    """ test --convert-to-jpeg --jpeg-quality """
    import glob
    import os
    import os.path
    import pathlib
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_6),
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
    """ test --convert-to-jpeg """
    import glob
    import os
    import os.path
    import pathlib
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_6),
                ".",
                "-V",
                "--convert-to-jpeg",
                "--skip-raw",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_CONVERT_TO_JPEG_SKIP_RAW)


def test_query_date_1():
    """ Test --from-date and --to-date """
    import json
    import osxphotos
    import os
    import os.path
    import time
    from osxphotos.__main__ import query

    os.environ["TZ"] = "US/Pacific"
    time.tzset()

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
    assert len(json_got) == 4


def test_query_date_2():
    """ Test --from-date and --to-date """
    import json
    import osxphotos
    import os
    import os.path
    import time
    from osxphotos.__main__ import query

    os.environ["TZ"] = "Asia/Jerusalem"
    time.tzset()

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


def test_query_date_timezone():
    """ Test --from-date, --to-date with ISO 8601 timezone """
    import json
    import osxphotos
    import os
    import os.path
    import time
    from osxphotos.__main__ import query

    os.environ["TZ"] = "US/Pacific"
    time.tzset()

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


def test_query_keyword_1():
    """Test query --keyword """
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_5), "--keyword", "Kids"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 4


def test_query_keyword_2():
    """Test query --keyword with lower case keyword"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_5), "--keyword", "kids"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 0


def test_query_keyword_3():
    """Test query --keyword with lower case keyword and --ignore-case"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
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
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
            "--keyword",
            "Kids",
            "--keyword",
            "wedding",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 6


def test_query_person_1():
    """Test query --person"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_5), "--person", "Katie"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 3


def test_query_person_2():
    """Test query --person with lower case person"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_5), "--person", "katie"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 0


def test_query_person_3():
    """Test query --person with lower case person and --ignore-case"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
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
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
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
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
            "--album",
            "Pumpkin Farm",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 3


def test_query_album_2():
    """Test query --album with lower case album"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
            "--album",
            "pumpkin farm",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 0


def test_query_album_3():
    """Test query --album with lower case album and --ignore-case"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
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
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
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
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_5), "--label", "Statue"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 1


def test_query_label_2():
    """Test query --label with lower case label """
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_5), "--label", "statue"],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 0


def test_query_label_3():
    """Test query --label with lower case label and --ignore-case"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
            "--label",
            "statue",
            "--ignore-case",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 1


def test_query_label_4():
    """Test query with more than one --label"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
            "--label",
            "Statue",
            "--label",
            "Plant",
        ],
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == 8


def test_query_deleted_deleted_only():
    """Test query with --deleted and --deleted-only"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query,
        [
            "--json",
            "--db",
            os.path.join(cwd, PHOTOS_DB_15_5),
            "--deleted",
            "--deleted-only",
        ],
    )
    assert "Incompatible query options" in result.output


def test_query_deleted_1():
    """Test query with --deleted"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_5), "--deleted"]
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == PHOTOS_NOT_IN_TRASH_LEN_15_5 + PHOTOS_IN_TRASH_LEN_15_5


def test_query_deleted_2():
    """Test query with --deleted"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_6), "--deleted"]
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == PHOTOS_NOT_IN_TRASH_LEN_15_6 + PHOTOS_IN_TRASH_LEN_15_6


def test_query_deleted_3():
    """Test query with --deleted-only"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_5), "--deleted-only"]
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == PHOTOS_IN_TRASH_LEN_15_5
    assert json_got[0]["intrash"]


def test_query_deleted_4():
    """Test query with --deleted-only"""
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        query, ["--json", "--db", os.path.join(cwd, PHOTOS_DB_15_6), "--deleted-only"]
    )
    assert result.exit_code == 0
    json_got = json.loads(result.output)
    assert len(json_got) == PHOTOS_IN_TRASH_LEN_15_6
    assert json_got[0]["intrash"]


def test_export_sidecar():
    import glob
    import os
    import os.path
    import osxphotos

    from osxphotos.__main__ import cli

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
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


def test_export_sidecar_templates():
    import json
    import os
    import os.path
    import osxphotos

    from osxphotos.__main__ import cli

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "export",
                "--db",
                os.path.join(cwd, PHOTOS_DB_15_5),
                ".",
                "--sidecar=json",
                f"--uuid={CLI_UUID_DICT_15_5['template']}",
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
        assert (
            exifdata[0]["XMP:Description"]
            == "Girls with pumpkins Katie, Suzy Kids Pumpkin Farm, Test Album"
        )
        assert (
            exifdata[0]["EXIF:ImageDescription"]
            == "Girls with pumpkins Katie, Suzy Kids Pumpkin Farm, Test Album"
        )


def test_export_sidecar_update():
    """ test sidecar don't update if not changed and do update if changed """
    import datetime
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.fileutil import FileUtil

    from osxphotos.__main__ import cli

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
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
        assert "Writing exiftool JSON sidecar" in result.output

        # delete a sidecar file and run update
        fileutil = FileUtil()
        fileutil.unlink(CLI_EXPORT_SIDECAR_FILENAMES[1])

        result = runner.invoke(
            cli,
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
        assert "Writing exiftool JSON sidecar" in result.output

        # run update again, no sidecar files should update
        result = runner.invoke(
            cli,
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
        assert "Skipped up to date exiftool JSON sidecar" in result.output

        # touch a file and export again
        ts = datetime.datetime.now().timestamp() + 1000
        fileutil.utime(CLI_EXPORT_SIDECAR_FILENAMES[2], (ts, ts))

        result = runner.invoke(
            cli,
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
        assert "Skipped up to date exiftool JSON sidecar" in result.output

        # run update again, no sidecar files should update
        result = runner.invoke(
            cli,
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
        assert "Skipped up to date exiftool JSON sidecar" in result.output

        # run update again with updated metadata, forcing update
        result = runner.invoke(
            cli,
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
        assert "Writing exiftool JSON sidecar" in result.output


def test_export_live():
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
#     import glob
#     import os
#     import os.path
#     import osxphotos
#     from osxphotos.__main__ import export

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
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(export, [os.path.join(cwd, RAW_PHOTOS_DB), ".", "-V"])
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_RAW_EDITED_ORIGINAL)


def test_export_directory_template_1():
    # test export using directory template
    import glob
    import locale
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    locale.setlocale(locale.LC_ALL, "en_US")

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
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
        assert result.exit_code == 2
        assert "Error: Invalid template" in result.output


def test_export_directory_template_album_1():
    # test export using directory template with multiple albums
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    import os
    import glob
    import locale
    import os.path

    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        # set locale environment
        os.environ["LANG"] = "de_DE.UTF-8"
        os.environ["LC_COLLATE"] = "de_DE.UTF-8"
        os.environ["LC_CTYPE"] = "de_DE.UTF-8"
        os.environ["LC_MESSAGES"] = "de_DE.UTF-8"
        os.environ["LC_MONETARY"] = "de_DE.UTF-8"
        os.environ["LC_NUMERIC"] = "de_DE.UTF-8"
        os.environ["LC_TIME"] = "de_DE.UTF-8"
        locale.setlocale(locale.LC_ALL, "")
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
    """ export photos using filename template """
    import glob
    import locale
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    locale.setlocale(locale.LC_ALL, "en_US")

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
        workdir = os.getcwd()
        files = glob.glob("*.*")
        assert sorted(files) == sorted(CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES1)


def test_export_filename_template_2():
    """ export photos using filename template with folder_album and path_sep """
    import glob
    import locale
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    locale.setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_5),
                ".",
                "-V",
                "--filename",
                "{folder_album,None}-{original_name}",
            ],
        )
        assert result.exit_code == 0
        files = glob.glob("*.*")
        assert sorted(files) == sorted(CLI_EXPORTED_FILENAME_TEMPLATE_FILENAMES2)


def test_export_filename_template_pathsep_in_name_1():
    """ export photos using filename template with folder_album and "/" in album name """
    import locale
    import os
    import os.path
    import pathlib
    from osxphotos.__main__ import export

    locale.setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_6),
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
    """ export photos using filename template with keyword and "/" in keyword """
    import locale
    import os
    import os.path
    import pathlib
    from osxphotos.__main__ import export

    locale.setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_6),
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
    """ export photos using filename template with description that exceeds max length """
    import locale
    import os
    import os.path
    import pathlib
    import osxphotos
    from osxphotos.__main__ import export

    locale.setlocale(locale.LC_ALL, "en_US")

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_6),
                ".",
                "-V",
                "--filename",
                "{descr}",
                "--uuid",
                CLI_EXPORT_UUID_LONG_DESCRIPTION,
            ],
        )
        assert result.exit_code == 0
        for fname in CLI_EXPORTED_FILENAME_TEMPLATE_LONG_DESCRIPTION:
            assert pathlib.Path(fname).is_file()


def test_export_filename_template_3():
    """ test --filename with invalid template """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
        assert result.exit_code == 2
        assert "Error: Invalid template" in result.output


def test_export_album():
    """Test export of an album """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, PHOTOS_DB_15_5), ".", "--album", "Pumpkin Farm", "-V"],
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert sorted(files) == sorted(CLI_EXPORT_FILENAMES_ALBUM)


def test_export_album_unicode_name():
    """Test export of an album with non-English characters in name """
    import glob
    import os
    import os.path
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_6),
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
    """Test export of an album where album of same name has been deleted """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                os.path.join(cwd, PHOTOS_DB_15_5),
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
    """Test export with --deleted """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        skip = ["--skip-edited", "--skip-bursts", "--skip-live", "--skip-raw"]
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_5), ".", "--deleted", *skip]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert (
            len(files)
            == PHOTOS_NOT_IN_TRASH_LEN_15_5
            + PHOTOS_IN_TRASH_LEN_15_5
            - PHOTOS_MISSING_15_5
        )


def test_export_deleted_2():
    """Test export with --deleted """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    """Test export does not find intrash files without --deleted flag """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        skip = ["--skip-edited", "--skip-bursts", "--skip-live", "--skip-raw"]
        result = runner.invoke(export, [os.path.join(cwd, PHOTOS_DB_15_5), ".", *skip])
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == PHOTOS_NOT_IN_TRASH_LEN_15_5 - PHOTOS_MISSING_15_5


def test_export_not_deleted_2():
    """Test export does not find intrash files without --deleted flag """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
    """Test export with --deleted-only """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        skip = ["--skip-edited", "--skip-bursts", "--skip-live", "--skip-raw"]
        result = runner.invoke(
            export, [os.path.join(cwd, PHOTOS_DB_15_5), ".", "--deleted-only", *skip]
        )
        assert result.exit_code == 0
        files = glob.glob("*")
        assert len(files) == PHOTOS_IN_TRASH_LEN_15_5


def test_export_deleted_only_2():
    """Test export with --deleted-only """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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


def test_places():
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import places

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(places, [os.path.join(cwd, PLACES_PHOTOS_DB), "--json"])
        assert result.exit_code == 0
        json_got = json.loads(result.output)
        assert json_got == json.loads(CLI_PLACES_JSON)


def test_place_13():
    # test --place on 10.13
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [os.path.join(cwd, PLACES_PHOTOS_DB_13), "--json", "--place", "Adelaide"],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "2L6X2hv3ROWRSCU3WRRAGQ"


def test_no_place_13():
    # test --no-place on 10.13
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query, [os.path.join(cwd, PLACES_PHOTOS_DB_13), "--json", "--no-place"]
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "pERZk5T1Sb+XcKDFRCsGpA"


def test_place_15_1():
    # test --place on 10.15
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [os.path.join(cwd, PLACES_PHOTOS_DB), "--json", "--place", "Washington"],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "128FB4C6-0B16-4E7D-9108-FB2E90DA1546"


def test_place_15_2():
    # test --place on 10.15
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [os.path.join(cwd, PLACES_PHOTOS_DB), "--json", "--place", "United States"],
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 2  # single element
        uuid = [json_got[x]["uuid"] for x in (0, 1)]
        assert "128FB4C6-0B16-4E7D-9108-FB2E90DA1546" in uuid
        assert "FF7AFE2C-49B0-4C9B-B0D7-7E1F8B8F2F0C" in uuid


def test_no_place_15():
    # test --no-place on 10.15
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query, [os.path.join(cwd, PLACES_PHOTOS_DB), "--json", "--no-place"]
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "A9B73E13-A6F2-4915-8D67-7213B39BAE9F"


def test_no_folder_1_15():
    # test --folder on 10.15
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query, [os.path.join(cwd, PHOTOS_DB_15_4), "--json", "--folder", "Folder1"]
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)

        assert len(json_got) == 2  # single element
        for item in json_got:
            assert item["uuid"] in [
                "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
                "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
            ]
            assert item["albums"] == ["AlbumInFolder"]


def test_no_folder_2_15():
    # test --folder with --uuid on 10.15
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query,
            [
                os.path.join(cwd, PHOTOS_DB_15_4),
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
            assert item["albums"] == ["AlbumInFolder"]


def test_no_folder_1_14():
    # test --folder on 10.14
    import json
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import query

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            query, [os.path.join(cwd, PHOTOS_DB_14_6), "--json", "--folder", "Folder1"]
        )
        assert result.exit_code == 0
        json_got = json.loads(result.output)
        assert len(json_got) == 1  # single element
        assert json_got[0]["uuid"] == "15uNd7%8RguTEgNPKHfTWw"


def test_export_sidecar_keyword_template():
    import json
    import glob
    import os
    import os.path
    import osxphotos

    from osxphotos.__main__ import cli

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
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
            [{"EXIF:ImageDescription": "Girl holding pumpkin", 
            "XMP:Description": "Girl holding pumpkin", 
            "XMP:Title": "I found one!", 
            "XMP:TagsList": ["Kids", "Multi Keyword", "Pumpkin Farm", "Test Album"], 
            "IPTC:Keywords": ["Kids", "Multi Keyword", "Pumpkin Farm", "Test Album"], 
            "XMP:PersonInImage": ["Katie"], 
            "XMP:Subject": ["Kids", "Multi Keyword", "Pumpkin Farm", "Test Album"], 
            "EXIF:DateTimeOriginal": "2018:09:28 16:07:07", 
            "EXIF:CreateDate": "2018:09:28 16:07:07", 
            "EXIF:OffsetTimeOriginal": "-04:00", 
            "IPTC:DateCreated": "2018:09:28",
            "IPTC:TimeCreated": "16:07:07-04:00",
            "EXIF:ModifyDate": "2018:09:28 16:07:07"}]
            """
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
    """ test export then update """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export, OSXPHOTOS_EXPORT_DB

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
            "Processed: 7 photos, exported: 0, updated: 0, skipped: 8, updated EXIF data: 0, missing: 1, error: 0"
            in result.output
        )


def test_export_update_child_folder():
    """ test export then update into a child folder of previous export """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export, OSXPHOTOS_EXPORT_DB

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
    """ test export then update into a parent folder of previous export """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export, OSXPHOTOS_EXPORT_DB

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
    """ test export then update with exiftool """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export

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
            "Processed: 7 photos, exported: 0, updated: 8, skipped: 0, updated EXIF data: 8, missing: 1, error: 0"
            in result.output
        )

        # update with exiftool again, should be no changes
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update", "--exiftool"]
        )
        assert result.exit_code == 0
        assert (
            "Processed: 7 photos, exported: 0, updated: 0, skipped: 8, updated EXIF data: 0, missing: 1, error: 0"
            in result.output
        )


def test_export_update_hardlink():
    """ test export with hardlink then update """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export

    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
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
            "Processed: 7 photos, exported: 0, updated: 8, skipped: 0, updated EXIF data: 0, missing: 1, error: 0"
            in result.output
        )
        assert not os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)


@pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_update_hardlink_exiftool():
    """ test export with hardlink then update with exiftool """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export

    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
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
            "Processed: 7 photos, exported: 0, updated: 8, skipped: 0, updated EXIF data: 8, missing: 1, error: 0"
            in result.output
        )
        assert not os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)


def test_export_update_edits():
    """ test export then update after removing and editing files """
    import glob
    import os
    import os.path
    import shutil

    import osxphotos
    from osxphotos.__main__ import export

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
            "Processed: 7 photos, exported: 1, updated: 1, skipped: 6, updated EXIF data: 0, missing: 1, error: 0"
            in result.output
        )


def test_export_update_no_db():
    """ test export then update after db has been deleted """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export, OSXPHOTOS_EXPORT_DB

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

        # update
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "--update"]
        )
        assert result.exit_code == 0

        # unedited files will be skipped because their signatures will compare but
        # edited files will be re-exported because there won't be an edited signature
        # in the database
        assert (
            "Processed: 7 photos, exported: 0, updated: 2, skipped: 6, updated EXIF data: 0, missing: 1, error: 0"
            in result.output
        )
        assert os.path.isfile(OSXPHOTOS_EXPORT_DB)


def test_export_then_hardlink():
    """ test export then hardlink """
    import glob
    import os
    import os.path

    import osxphotos
    from osxphotos.__main__ import export

    photosdb = osxphotos.PhotosDB(dbfile=CLI_PHOTOS_DB)
    photo = photosdb.photos(uuid=[CLI_EXPORT_UUID])[0]

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
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
        assert "Processed: 7 photos, exported: 8, missing: 1, error: 0" in result.output
        assert os.path.samefile(CLI_EXPORT_UUID_FILENAME, photo.path)


def test_export_dry_run():
    """ test export with dry-run flag """
    import os
    import os.path
    import re
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Processed: 7 photos, exported: 8, missing: 1, error: 0" in result.output
        for filepath in CLI_EXPORT_FILENAMES:
            assert re.search(r"Exported.*" + f"{filepath}", result.output)
            assert not os.path.isfile(filepath)


def test_export_update_edits_dry_run():
    """ test export then update after removing and editing files with dry-run flag """
    import glob
    import os
    import os.path
    import shutil

    import osxphotos
    from osxphotos.__main__ import export

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
            "Processed: 7 photos, exported: 1, updated: 1, skipped: 6, updated EXIF data: 0, missing: 1, error: 0"
            in result.output
        )

        # make sure file didn't really get copied
        assert not os.path.isfile(CLI_EXPORT_BY_DATE[0])


def test_export_directory_template_1_dry_run():
    """ test export using directory template with dry-run flag """
    import locale
    import os
    import os.path
    import re
    import osxphotos
    from osxphotos.__main__ import export

    locale.setlocale(locale.LC_ALL, "en_US")

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
        assert "exported: 8" in result.output
        workdir = os.getcwd()
        for filepath in CLI_EXPORTED_DIRECTORY_TEMPLATE_FILENAMES1:
            assert re.search(r"Exported.*" + f"{filepath}", result.output)
            assert not os.path.isfile(os.path.join(workdir, filepath))


def test_export_touch_files():
    """ test export with --touch-files """
    import os
    import time

    import osxphotos
    from osxphotos.__main__ import export

    os.environ["TZ"] = "US/Pacific"
    time.tzset()

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

        assert "exported: 18" in result.output
        assert "touched date: 16" in result.output

        for fname, mtime in zip(CLI_EXPORT_BY_DATE, CLI_EXPORT_BY_DATE_TOUCH_TIMES):
            st = os.stat(fname)
            assert int(st.st_mtime) == int(mtime)


def test_export_touch_files_update():
    """ test complex export scenario with --update and --touch-files """
    import os
    import pathlib
    import time

    import osxphotos
    from osxphotos.__main__ import export

    os.environ["TZ"] = "US/Pacific"
    time.tzset()

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

        assert "skipped: 18" in result.output

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
        assert "skipped: 18" in result.output
        assert "touched date: 16" in result.output

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
        assert "skipped: 18" in result.output
        assert "touched date: 16" in result.output

        for fname, mtime in zip(
            CLI_EXPORT_BY_DATE_NEED_TOUCH, CLI_EXPORT_BY_DATE_NEED_TOUCH_TIMES
        ):
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
                "--touch-file",
            ],
        )
        assert result.exit_code == 0
        assert "updated: 1, skipped: 17" in result.output
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

        assert "skipped: 18" in result.output


@pytest.mark.skip("TODO: This fails on some machines but not all")
# @pytest.mark.skipif(exiftool is None, reason="exiftool not installed")
def test_export_touch_files_exiftool_update():
    """ test complex export scenario with --update, --exiftool, and --touch-files """
    import os
    import pathlib
    import time

    import osxphotos
    from osxphotos.__main__ import export

    os.environ["TZ"] = "US/Pacific"
    time.tzset()

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

        assert "skipped: 18" in result.output

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
        assert "skipped: 18" in result.output
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
        assert "skipped: 18" in result.output
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
        assert "skipped: 18" in result.output

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
        assert "skipped: 18" in result.output


def test_export_ignore_signature():
    """ test export with --ignore-signature """
    import os
    from osxphotos.__main__ import export

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
    """ test export with --ignore-signature and --sidecar """
    """
    Test the following use cases: 
    If the metadata (in Photos) that went into the sidecar did not change, the sidecar will not be updated
    If the metadata (in Photos) that went into the sidecar did change, a new sidecar is written but a new image file is not
    If a sidecar does not exist for the photo, a sidecar will be written whether or not the photo file was written
    """

    import osxphotos
    import os

    from osxphotos.__main__ import export

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
        exportdb = osxphotos.export_db.ExportDB("./.osxphotos_export.db")
        for filename in CLI_EXPORT_IGNORE_SIGNATURE_FILENAMES:
            exportdb.set_sidecar_for_file(f"{filename}.xmp", "FOO", (0, 1, 2))

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
    """Test osxphotos labels """
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import labels

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        labels, ["--db", os.path.join(cwd, PHOTOS_DB_15_5), "--json"]
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert json_got == LABELS_JSON


def test_keywords():
    """Test osxphotos keywords """
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import keywords

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        keywords, ["--db", os.path.join(cwd, PHOTOS_DB_15_5), "--json"]
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert json_got == KEYWORDS_JSON


# TODO: this fails with result.exit_code == 1 but I think this has to
# do with how pytest is invoking the command
# def test_albums_str():
#     """Test osxphotos albums string output """
#     import json
#     import osxphotos
#     import os
#     import os.path
#     from osxphotos.__main__ import albums

#     runner = CliRunner()
#     cwd = os.getcwd()
#     result = runner.invoke(albums, ["--db", os.path.join(cwd, PHOTOS_DB_15_6), ])
#     assert result.exit_code == 0

#     assert result.output == ALBUMS_STR


def test_albums_json():
    """Test osxphotos albums json output """
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import albums

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        albums, ["--db", os.path.join(cwd, PHOTOS_DB_15_6), "--json"]
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert json_got == ALBUMS_JSON


def test_persons():
    """Test osxphotos persons """
    import json
    import osxphotos
    import os
    import os.path
    from osxphotos.__main__ import persons

    runner = CliRunner()
    cwd = os.getcwd()
    result = runner.invoke(
        persons, ["--db", os.path.join(cwd, PHOTOS_DB_15_5), "--json"]
    )
    assert result.exit_code == 0

    json_got = json.loads(result.output)
    assert json_got == PERSONS_JSON


def test_export_report():
    """ test export with --report option """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--report", "report.csv"],
        )
        assert result.exit_code == 0
        assert "Writing export report" in result.output
        assert os.path.exists("report.csv")


def test_export_report_not_a_file():
    """ test export with --report option and bad report value """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--report", "."]
        )
        assert result.exit_code != 0
        assert "Aborted!" in result.output


def test_export_as_hardlink_download_missing():
    """ test export with incompatible export options """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
                "--download-missing",
                "--export-as-hardlink",
                ".",
            ],
        )
        assert result.exit_code != 0
        assert "Aborted!" in result.output


def test_export_missing():
    """ test export with --missing """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
                "--missing",
                "--download-missing",
                ".",
            ],
        )
        assert result.exit_code == 0
        assert "Exporting 2 photos" in result.output


def test_export_missing_not_download_missing():
    """ test export with incompatible export options """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export, [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--missing", "."]
        )
        assert result.exit_code != 0
        assert "Aborted!" in result.output


def test_export_cleanup():
    """ test export with --cleanup flag """
    import pathlib
    from osxphotos.__main__ import export

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


def test_save_load_config():
    """ test --save-config, --load-config """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export

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
        assert "Saving options to file" in result.output
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
        assert "Saving options to file" in result.output
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
        assert "Writing exiftool JSON sidecar" in result.output
        assert "Writing XMP sidecar" not in result.output


def test_export_exportdb():
    """ test --exportdb """
    import glob
    import os
    import os.path
    import osxphotos
    from osxphotos.__main__ import export
    import re

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--exportdb", "export.db"],
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

        # specify a path for exportdb, should generate error
        result = runner.invoke(
            export,
            [os.path.join(cwd, CLI_PHOTOS_DB), ".", "-V", "--exportdb", "./export.db"],
        )
        assert result.exit_code != 0
        assert (
            "Error: --exportdb must be specified as filename not path" in result.output
        )

