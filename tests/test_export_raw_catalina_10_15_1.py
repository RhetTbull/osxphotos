import pytest

from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.utils import dd_to_dms_str

PHOTOS_DB = "./tests/Test-RAW-10.15.1.photoslibrary/database/photos.db"

UUID_DICT = {"has_adjustments": "441DFE2A-A69B-4C79-A69B-3F51D1B9B29C"}
FILENAME_DICT = {
    "original": "IMG_0476_2.CR2",
    "original_edited": "IMG_0476_2_edited.jpeg",
    "current": "441DFE2A-A69B-4C79-A69B-3F51D1B9B29C.cr2",
    "current_edited": "441DFE2A-A69B-4C79-A69B-3F51D1B9B29C_edited.jpeg",
}


def test_export_1():
    # test basic export
    # get an unedited image and export it using default filename
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    filename = photos[0].original_filename
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)
    assert pathlib.Path(got_dest).name == FILENAME_DICT["original"]


def test_export_2():
    # test basic export
    # get an unedited image and export it using original filename
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    filename = photos[0].original_filename
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)
    assert pathlib.Path(got_dest).name == FILENAME_DICT["original"]


def test_export_edited_name():
    # export edited file with name provided
    import os
    import os.path
    import pathlib
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename, edited=True)[0]
    assert got_dest == expected_dest
    assert pathlib.Path(got_dest).name == filename


def test_export_edited_default():
    # export edited file with default name
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    got_dest = photos[0].export(dest, edited=True)[0]
    assert pathlib.Path(got_dest).name == FILENAME_DICT["original_edited"]


def test_export_edited_wrong_suffix():
    # export edited file with name provided but wrong suffix
    # should produce a warning via logging.warning
    import os
    import os.path
    import pathlib
    import sys
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.cr2"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename, edited=True)[0]
    # assert "Invalid destination suffix" in caplog.text
    assert got_dest == expected_dest
    assert pathlib.Path(got_dest).name == filename
