"""Test fingerprint() function in fingerprint.py"""

import pytest

from osxphotos import PhotosDB
from osxphotos.platform import is_macos

if not is_macos:
    pytest.skip("skipping fingerprint tests, macOS only", allow_module_level=True)

from osxphotos.fingerprint import fingerprint

LIBRARY_PATH = "tests/Test-13.0.0.photoslibrary"
UUID = "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4"


def test_fingerprint():
    """Test that fingerprint() returns the same as Photos fingerprint"""
    photos = PhotosDB(LIBRARY_PATH).photos(uuid=[UUID])
    photo = photos[0]
    assert photo.fingerprint == fingerprint(photo.path)
