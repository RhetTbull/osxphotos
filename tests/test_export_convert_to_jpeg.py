import os
import pytest

from osxphotos._constants import _UNKNOWN_PERSON

skip_test = "OSXPHOTOS_TEST_CONVERT" not in os.environ
pytestmark = pytest.mark.skipif(
    skip_test, reason="Skip if running on GitHub actions, no GPU."
)

PHOTOS_DB = "tests/Test-10.15.6.photoslibrary"

UUID_DICT = {
    "raw": "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068",
    "heic": "7783E8E6-9CAC-40F3-BE22-81FB7051C266",
}

NAMES_DICT = {
    "raw": "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068.jpeg",
    "heic": "7783E8E6-9CAC-40F3-BE22-81FB7051C266.jpeg",
}


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

    results = photos[0].export2(dest, convert_to_jpeg=True)
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

    results = photos[0].export2(dest, convert_to_jpeg=True)
    got_dest = pathlib.Path(results.exported[0])

    assert got_dest.is_file()
    assert got_dest.suffix == ".jpeg"
    assert got_dest.name == NAMES_DICT["heic"]
