"""Test photosdb_utils """

import pathlib

import pytest

from osxphotos.photosdb.photosdb_utils import (
    get_db_path_for_library,
    get_photos_library_version,
)

LIBRARIES = {
    2: pathlib.Path("tests/Test-10.12.6.photoslibrary"),
    3: pathlib.Path("tests/Test-10.13.6.photoslibrary"),
    4: pathlib.Path("tests/Test-10.14.6.photoslibrary"),
    5: pathlib.Path("tests/Test-10.15.7.photoslibrary"),
    6: pathlib.Path("tests/Test-10.16.0.photoslibrary"),
    7: pathlib.Path("tests/Test-12.0.1.photoslibrary"),
    8: pathlib.Path("tests/Test-13.0.0.photoslibrary"),
}


@pytest.mark.parametrize("version,library_path", list(LIBRARIES.items()))
def test_get_photos_library_version_library_path(version, library_path):
    """Test get_photos_library_version with library path"""
    photos_version = get_photos_library_version(library_path)
    assert photos_version == version


@pytest.mark.parametrize("version,library_path", list(LIBRARIES.items()))
def test_get_photos_library_version_db_path(version, library_path):
    """Test get_photos_library_version with database path"""
    photos_version = get_photos_library_version(library_path / "database" / "photos.db")
    assert photos_version == version


@pytest.mark.parametrize("library_path", list(LIBRARIES.values()))
def test_get_db_path_for_library(library_path):
    """Test get_db_path_for_library"""
    db_path = get_db_path_for_library(library_path)
    assert db_path.is_file()
