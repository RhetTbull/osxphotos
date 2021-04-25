import os
import pytest

from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.utils import _get_os_version

OS_VERSION = _get_os_version()
SKIP_TEST = "OSXPHOTOS_TEST_EXPORT" not in os.environ or OS_VERSION[1] != "15"
PHOTOS_DB = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")
pytestmark = pytest.mark.skipif(
    SKIP_TEST, reason="These tests only run against system photos library"
)

UUID_DICT = {
    "has_adjustments": "2B2D5434-6D31-49E2-BF47-B973D34A317B",
    "no_adjustments": "A8D646C3-89A9-4D74-8001-4EB46BA55B94",
    "live": "BFF29EBD-22DF-4FCF-9817-317E7104EA50",
}

UUID_BURSTS = {
    "9F90DC00-AAAF-4A05-9A65-61FEEE0D67F2": {
        "selected": False,
        "filename": "IMG_9812.JPG",
        "burst_albums": ["TestBurst"],
        "albums": ["TestBurst"]
    },
    "A385FA13-DF8E-482F-A8C5-970EDDF54C2F": {
        "selected": False,
        "filename": "IMG_9813.JPG",
        "burst_albums": ["TestBurst"],
        "albums": []
    },
    "38F8F30C-FF6D-49DA-8092-18497F1D6628": {
        "selected": True,
        "filename": "IMG_9814.JPG",
        "burst_albums": ["TestBurst", "TestBurst2"],
        "albums": ["TestBurst2"]
    },
    "E3863443-9EA8-417F-A90B-8F7086623DAD": {
        "selected": False,
        "filename": "IMG_9815.JPG",
        "burst_albums": ["TestBurst"],
        "albums": []
    },
        "964F457D-5FFC-47B9-BEAD-56B0A83FEF63": {
        "selected": True,
        "filename": "IMG_9816.JPG",
        "burst_albums": ["TestBurst"],
        "albums": []
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
    expected_dest = expected_dest.parent / f"{expected_dest.stem}.jpeg"
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

    import osxphotos

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


def test_burst_albums(photosdb):
    """Test burst_selected, burst_albums"""

    for uuid in UUID_BURSTS:
        photo = photosdb.get_photo(uuid)
        assert photo.burst
        assert photo.burst_selected == UUID_BURSTS[uuid]["selected"]
        assert sorted(photo.albums) == sorted(UUID_BURSTS[uuid]["albums"])
        assert sorted(photo.burst_albums) == sorted(UUID_BURSTS[uuid]["burst_albums"])
