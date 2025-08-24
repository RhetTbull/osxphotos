"""Test osxphotos with bad or missing Photos database, #1805, #1893"""

import os
import pathlib
import shutil

from osxphotos import PhotosDB

PHOTOS_DB = "tests/Test-13.0.0.photoslibrary/"
CWD = os.getcwd()


def copy_photos_library(dest: pathlib.Path) -> pathlib.Path:
    """Make a copy of the Photos library for testing"""
    return pathlib.Path(shutil.copytree(os.path.join(CWD, PHOTOS_DB), dest))


def test_missing_photos_db(tmp_path: pathlib.Path):
    """Test missing photos.db file"""
    test_library = copy_photos_library(tmp_path / "Test.photoslibrary")
    (test_library / "database" / "photos.db").unlink()
    photosdb = PhotosDB(test_library)
    assert photosdb is not None


def test_bad_photos_db(tmp_path: pathlib.Path):
    """Test malformed photos.db file"""
    test_library = copy_photos_library(tmp_path / "Test.photoslibrary")
    (test_library / "database" / "photos.db").unlink()
    (test_library / "database" / "photos.db").touch()
    photosdb = PhotosDB(test_library)
    assert photosdb is not None
