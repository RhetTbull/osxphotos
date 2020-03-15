import os
import pytest

from osxphotos._constants import _UNKNOWN_PERSON

skip_test = False if "OSXPHOTOS_TEST_EXPORT" in os.environ else True
pytestmark = pytest.mark.skipif(
    skip_test, reason="These tests only run against system photos library"
)

PHOTOS_DB = "/Users/rhet/Pictures/Photos Library.photoslibrary"

UUID_DICT = {
    "has_adjustments": "A8111956-E900-4DEC-9191-A04A87C07BC5",
    "no_adjustments": "EA7BB55F-92F1-4818-94E3-E8DEDC6B2E31",
    "live": "9032C168-9319-40C0-8210-5ADC42F4C603",
}


@pytest.fixture(scope="module")
def photosdb():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    return photosdb


def test_export_default_name(photosdb):
    # test basic export
    # get an unedited image and export it using default filename
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, use_photos_export=True)[0]

    assert got_dest == expected_dest
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

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    suffix = pathlib.Path(photos[0].path_edited).suffix
    filename = f"{pathlib.Path(photos[0].filename).stem}_edited{suffix}"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, use_photos_export=True, edited=True)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(expected_dest)


def test_export_edited_exiftool(photosdb):
    # test export edited file
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos
    import osxphotos.exiftool

    import logging

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

