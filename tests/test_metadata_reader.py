"""Test metadata_reader.py functions."""

from __future__ import annotations

import pathlib

import pytest

from osxphotos.exiftool import get_exiftool_path
from osxphotos.metadata_reader import (
    get_sidecar_for_file,
    metadata_from_file,
    metadata_from_sidecar,
)

TEST_IMAGES_DIR = "tests/test-images"
TEST_IMAGE_1 = "tests/test-images/IMG_4179.jpeg"
TEST_IMAGE_1_XMP = "tests/test-images/IMG_4179.jpeg.xmp"
TEST_IMAGE_1_JSON_EXIFTOOL = "tests/test-images/IMG_4179.jpeg.exiftool.json"
TEST_IMAGE_1_JSON_OSXPHOTOS_EXIFTOOL = "tests/test-images/IMG_4179.jpeg.json"
TEST_IMAGE_1_JSON_OSXPHOTOS_JSON = "tests/test-images/IMG_4179.jpeg.json_osxphotos.json"
TEST_IMAGE_NO_SIDECAR = "tests/test-images/IMG_9975.jpeg"

# determine if exiftool installed so exiftool tests can be skipped
try:
    exiftool_path = get_exiftool_path()
except FileNotFoundError:
    exiftool_path = None


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
def test_metadata_from_file():
    """Test metadata_from_file"""
    metadata = metadata_from_file(TEST_IMAGE_1, None)
    assert metadata.title == "Waves crashing on rocks"
    assert metadata.description == "Used for testing osxphotos"
    assert metadata.keywords == ["osxphotos", "Sümmer"]
    assert metadata.location == (
        pytest.approx(33.7150638888889),
        pytest.approx(-118.319672222222),
    )


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
@pytest.mark.parametrize(
    "filename",
    [
        TEST_IMAGE_1_XMP,
        TEST_IMAGE_1_JSON_EXIFTOOL,
        TEST_IMAGE_1_JSON_OSXPHOTOS_EXIFTOOL,
        TEST_IMAGE_1_JSON_OSXPHOTOS_JSON,
    ],
)
def test_metadata_from_sidecar(filename):
    """Test metadata_from_sidecar"""
    metadata = metadata_from_sidecar(filename, None)
    assert metadata.title == "Image Title"
    assert metadata.description == "Image Description"
    assert metadata.keywords == ["nature"]
    assert metadata.location == (
        pytest.approx(33.71506),
        pytest.approx(-118.31967),
    )


def test_get_sidecar_for_file():
    """Test get_sidecar_for_file"""
    assert get_sidecar_for_file(TEST_IMAGE_1) == pathlib.Path(
        TEST_IMAGE_1_JSON_OSXPHOTOS_EXIFTOOL
    )


def test_get_sidecar_for_file_none():
    """Test get_sidecar_for_file when there is no sidecar"""
    assert get_sidecar_for_file(TEST_IMAGE_NO_SIDECAR) is None
