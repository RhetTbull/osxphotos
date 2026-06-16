"""Test macOS 27.0 (Tahoe developer beta) Photos library"""

import datetime
import json
import pathlib

import pytest

from osxphotos import PhotosDB

PHOTOS_DB = "./tests/Test-27.0_DevBeta.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-27.0_DevBeta.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-27.0_DevBeta.photoslibrary"

TEST_JSON = pathlib.Path(__file__).parent / "test-Test-27.0_DevBeta.json"

LIBRARY_NAME = "Test-27.0_DevBeta.photoslibrary"


@pytest.fixture(scope="session")
def photosdb():
    """Return a PhotosDB object for use by tests."""
    return PhotosDB(dbfile=PHOTOS_DB)


@pytest.fixture(scope="session")
def expected_photoinfo():
    """Load expected PhotoInfo JSON data."""
    with open(TEST_JSON, "r") as f:
        return json.load(f)


def _normalize_for_comparison(obj):
    if isinstance(obj, dict):
        return {k: _normalize_for_comparison(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_for_comparison(v) for v in obj]
    if isinstance(obj, str):
        # Normalize paths
        if LIBRARY_NAME in obj:
            # Extract just the relative path from the library name onwards
            parts = obj.split(LIBRARY_NAME)
            if len(parts) >= 2:
                return LIBRARY_NAME + parts[1]
        # Normalize ISO 8601 date strings to datetime objects
        if (
            obj
            and (obj.count("-") >= 2 or "T" in obj)
            and ("T" in obj or obj.count(":") >= 2)
        ):
            try:
                return datetime.datetime.fromisoformat(obj.replace("Z", "+00:00"))
            except ValueError:
                pass
    return obj


def test_photosdb_loads(photosdb):
    """Test that the macOS 27.0 library loads and reports the expected version."""
    assert photosdb.photos_version == 12
    assert len(photosdb.photos(movies=True)) == 13


def test_photoinfo_json(photosdb, expected_photoinfo):
    """Test that PhotoInfo.json(shallow=False) matches expected JSON data."""
    expected_map = {item["uuid"]: item for item in expected_photoinfo}
    for uuid, expected in expected_map.items():
        photo = photosdb.photos(uuid=[uuid])[0]
        actual = json.loads(photo.json(shallow=False))
        assert _normalize_for_comparison(actual) == _normalize_for_comparison(expected)
