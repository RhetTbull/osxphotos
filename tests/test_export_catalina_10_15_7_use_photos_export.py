import os

import pytest

from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.platform import get_macos_version, is_macos

OS_VERSION = get_macos_version() if is_macos else (None, None, None)
SKIP_TEST = "OSXPHOTOS_TEST_EXPORT" not in os.environ or OS_VERSION[1] != "15"
PHOTOS_DB = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")
pytestmark = pytest.mark.skipif(
    SKIP_TEST, reason="These tests only run against system photos library"
)

UUID_DICT = {
    "has_adjustments": "C925CFDC-FF2B-4E71-AC9D-C669B6453A8B",  # IMG_1929.JPG
    "no_adjustments": "16A6AF6B-D8FC-4256-AE33-889733E3EEAB",  # IMG_9847.JPG
    "live": "8EC216A2-0032-4934-BD3F-04C6259B3304",  # IMG_3259.HEIC
}

UUID_BURSTS = {
    "9A5B4CE6-6A9F-4917-95D4-1C98D14FCE4F": {
        "selected": False,
        "filename": "IMG_9812.JPG",
        "burst_albums": ["TestBurst", "osxphotos"],
        "albums": ["TestBurst", "osxphotos"],
    },
    "89E235DD-B9AC-4E8D-BDA2-986981CA7582": {
        "selected": False,
        "filename": "IMG_9813.JPG",
        "burst_albums": ["TestBurst", "osxphotos"],
        "albums": [],
    },
    "75154738-83AA-4DCD-A913-632D5D1C0FEE": {
        "selected": True,
        "filename": "IMG_9814.JPG",
        "burst_albums": ["TestBurst", "TestBurst2", "osxphotos"],
        "albums": ["TestBurst2"],
    },
    "4A836160-51B2-4E32-907D-ECDDB2CEC657": {
        "selected": False,
        "filename": "IMG_9815.JPG",
        "burst_albums": ["TestBurst", "osxphotos"],
        "albums": [],
    },
    "F5E6BD24-B493-44E9-BDA2-7AD9D2CC8C9D": {
        "selected": True,
        "filename": "IMG_9816.JPG",
        "burst_albums": ["TestBurst", "osxphotos"],
        "albums": [],
    },
}


@pytest.fixture(scope="module")
def photosdb():
    import osxphotos

    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_export_default_name(photosdb):
    # test basic export
    # get an unedited image and export it using default filename
    import os
    import pathlib
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    filename = photos[0].original_filename
    expected_dest = pathlib.Path(dest) / filename
    got_dest = photos[0].export(dest, use_photos_export=True)[0]

    assert got_dest == str(expected_dest)
    assert os.path.isfile(got_dest)


def test_export_supplied_name(photosdb):
    # test export with user provided filename
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpeg"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename, use_photos_export=True)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_edited(photosdb):
    # test export edited file
    import os
    import os.path
    import pathlib
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    suffix = pathlib.Path(photos[0].path_edited).suffix
    filename = f"{pathlib.Path(photos[0].original_filename).stem}_edited{suffix}"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, use_photos_export=True, edited=True)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(expected_dest)


def test_export_edited_exiftool(photosdb):
    # test export edited file
    import logging
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos
    import osxphotos.exiftool

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    got_dest = photos[0].export(
        dest, use_photos_export=True, edited=True, exiftool=True
    )
    logging.warning(got_dest)
    got_dest = got_dest[0]

    assert os.path.isfile(got_dest)
    exif = osxphotos.exiftool.ExifTool(got_dest)
    assert exif.data["IPTC:Keywords"] == "osxphotos"


def test_export_edited_supplied_name(photosdb):
    # test export with user provided filename
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpeg"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename, use_photos_export=True, edited=True)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_edited_no_edit(photosdb):
    # test export edited file if not actually edited
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, use_photos_export=True, edited=True)
    assert e.type == ValueError


def test_burst_albums(photosdb):
    """Test burst_selected, burst_albums"""

    for uuid in UUID_BURSTS:
        photo = photosdb.get_photo(uuid)
        assert photo.burst
        assert photo.burst_selected == UUID_BURSTS[uuid]["selected"]
        assert sorted(photo.albums) == sorted(UUID_BURSTS[uuid]["albums"])
        assert sorted(photo.burst_albums) == sorted(UUID_BURSTS[uuid]["burst_albums"])
