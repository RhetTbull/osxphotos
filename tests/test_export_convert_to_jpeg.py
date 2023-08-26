import os

import pytest

from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.exportoptions import ExportOptions
from osxphotos.photoexporter import PhotoExporter

skip_test = "OSXPHOTOS_TEST_CONVERT" not in os.environ
pytestmark = pytest.mark.skipif(
    skip_test, reason="Skip if running on GitHub actions, no GPU."
)

PHOTOS_DB = "tests/Test-10.15.6.photoslibrary"

UUID_DICT = {
    "raw": "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068",
    "heic": "7783E8E6-9CAC-40F3-BE22-81FB7051C266",
}

NAMES_DICT = {"raw": "DSC03584.jpeg", "heic": "IMG_3092.jpeg"}

UUID_LIVE_HEIC = "8EC216A2-0032-4934-BD3F-04C6259B3304"
NAMES_LIVE_HEIC = ["IMG_3259.jpeg", "IMG_3259.mov"]


@pytest.fixture(scope="module")
def photosdb():
    import osxphotos

    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_export_convert_raw_to_jpeg(photosdb):
    # test export with convert_to_jpeg
    import pathlib
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["raw"]])

    export_options = ExportOptions(convert_to_jpeg=True)
    results = PhotoExporter(photos[0]).export(dest, options=export_options)
    got_dest = pathlib.Path(results.exported[0])

    assert got_dest.is_file()
    assert got_dest.suffix == ".jpeg"
    assert got_dest.name == NAMES_DICT["raw"]


def test_export_convert_heic_to_jpeg(photosdb):
    # test export with convert_to_jpeg
    import pathlib
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["heic"]])

    export_options = ExportOptions(convert_to_jpeg=True)
    results = PhotoExporter(photos[0]).export(dest, options=export_options)
    got_dest = pathlib.Path(results.exported[0])

    assert got_dest.is_file()
    assert got_dest.suffix == ".jpeg"
    assert got_dest.name == NAMES_DICT["heic"]


@pytest.mark.skipif(
    "OSXPHOTOS_TEST_EXPORT" not in os.environ,
    reason="Skip if not running against author's personal library",
)
def test_export_convert_live_heic_to_jpeg():
    # test export with convert_to_jpeg with live heic (issue #235)
    # don't have a live HEIC in one of the test libraries so use one from
    # my personal library
    import os
    import pathlib
    import tempfile

    import osxphotos

    photosdb = osxphotos.PhotosDB()
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photo = photosdb.get_photo(UUID_LIVE_HEIC)

    export_options = ExportOptions(convert_to_jpeg=True, live_photo=True)
    results = PhotoExporter(photo).export(dest, options=export_options)

    for name in NAMES_LIVE_HEIC:
        assert f"{tempdir.name}/{name}" in results.exported

    for file_ in results.exported:
        dest = pathlib.Path(file_)
        assert dest.is_file()
