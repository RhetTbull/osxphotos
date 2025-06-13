"""Test macOS 16.0.0 Photos library"""

import collections
import datetime
import json
import os
import os.path
import pathlib
import sqlite3
import tempfile
import time
from collections import Counter, namedtuple

import pytest

import osxphotos
from osxphotos import PhotosDB
from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.adjustmentsinfo import AdjustmentsInfo
from osxphotos.exifwriter import ExifWriter
from osxphotos.platform import get_macos_version, is_macos

PHOTOS_DB = "./tests/Test-16.0.0-beta.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-16.0.0-beta.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-16.0.0-beta.photoslibrary"

TEST_JSON = pathlib.Path(__file__).parent / "test-16.0.0-beta.json"


@pytest.fixture(scope="session")
def photosdb():
    """Return a PhotosDB object for use by tests."""
    return PhotosDB(dbfile=PHOTOS_DB)


@pytest.fixture(scope="session")
def expected_photoinfo():
    """Load expected PhotoInfo JSON data."""
    with open(TEST_JSON, "r") as f:
        return json.load(f)


def _normalize_paths(obj):
    tests_root = str(TEST_JSON.parent)
    if isinstance(obj, dict):
        return {k: _normalize_paths(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_paths(v) for v in obj]
    if isinstance(obj, str) and tests_root in obj:
        new = obj.replace(tests_root, "")
        return new.lstrip(os.sep)
    return obj


def test_photoinfo_json(photosdb, expected_photoinfo):
    """Test that PhotoInfo.json(shallow=False) matches expected JSON data."""
    expected_map = {item["uuid"]: item for item in expected_photoinfo}
    for uuid, expected in expected_map.items():
        photo = photosdb.photos(uuid=[uuid])[0]
        actual = json.loads(photo.json(shallow=False))
        assert _normalize_paths(actual) == _normalize_paths(expected)
