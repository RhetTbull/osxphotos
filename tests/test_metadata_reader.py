"""Test metadata_reader.py functions."""

from __future__ import annotations

import datetime
import pathlib

import pytest

from osxphotos.exiftool import get_exiftool_path
from osxphotos.metadata_reader import (
    SidecarFileType,
    get_sidecar_filetype,
    get_sidecar_for_file,
    metadata_from_exiftool,
    metadata_from_sidecar,
)

TEST_IMAGES_DIR = "tests/test-images"
TEST_IMAGE_1 = "tests/test-images/IMG_4179.jpeg"
TEST_IMAGE_1_XMP = "tests/test-images/IMG_4179.jpeg.xmp"
TEST_IMAGE_1_JSON_EXIFTOOL = "tests/test-images/IMG_4179.jpeg.exiftool.json"
TEST_IMAGE_1_JSON_OSXPHOTOS_EXIFTOOL = "tests/test-images/IMG_4179.jpeg.json"
TEST_IMAGE_1_JSON_OSXPHOTOS_JSON = "tests/test-images/IMG_4179.jpeg.json_osxphotos.json"
TEST_IMAGE_NO_SIDECAR = "tests/test-images/IMG_9975.jpeg"
TEST_SIDECAR_GOOGLE = "tests/test-images/IMG_4547.jpg.google_json.json"

# this test image has person info
TEST_IMAGE_2 = "tests/test-images/Pumkins1.jpg"
TEST_IMAGE_2_JSON = "tests/test-images/Pumkins1.jpg.json"

# list of lists of [image, sidecar, extra files]
# for testing get_sidecar_for_file
SIDECARS = [
    ["IMG_1234.jpeg", "IMG_1234.jpeg.xmp", []],
    ["IMG_1234.jpeg", "IMG_1234.xmp", []],
    ["IMG_1234.jpeg", "IMG_1234.json", ["IMG_1234.xmp"]],
    ["IMG_1234.jpeg", "IMG_1234.jpeg.json", []],
    ["IMG_1234-edited.jpeg", "IMG_1234.json", []],
    ["IMG_1234-edited.jpeg", "IMG_1234.jpeg.json", []],
    ["IMG_1234-edited.jpeg", "IMG_1234-edited.jpeg.json", ["IMG_1234.jpeg.json"]],
    ["IMG_1234(1).jpeg", "IMG_1234.jpeg(1).json", []],
    ["IMG_1234(1).jpeg", "IMG_1234(1).jpeg.json", []],
    ["IMG_1234(1).jpeg", "IMG_1234(1).json", []],
]

SIDECAR_TYPES = {
    TEST_IMAGE_1_XMP: SidecarFileType.XMP,
    TEST_IMAGE_1_JSON_EXIFTOOL: SidecarFileType.exiftool,
    TEST_IMAGE_1_JSON_OSXPHOTOS_EXIFTOOL: SidecarFileType.exiftool,
    TEST_IMAGE_1_JSON_OSXPHOTOS_JSON: SidecarFileType.osxphotos,
    TEST_SIDECAR_GOOGLE: SidecarFileType.GoogleTakeout,
    TEST_IMAGE_1: SidecarFileType.Unknown,
}

# determine if exiftool installed so exiftool tests can be skipped
try:
    exiftool_path = get_exiftool_path()
except FileNotFoundError:
    exiftool_path = None


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
@pytest.mark.usefixtures("set_tz_pacific")
def test_metadata_from_exiftool():
    """Test metadata_from_exiftool"""
    metadata = metadata_from_exiftool(TEST_IMAGE_1, None)
    assert metadata.title == "Waves crashing on rocks"
    assert metadata.description == "Used for testing osxphotos"
    assert metadata.keywords == ["osxphotos", "Sümmer"]
    assert metadata.location == (
        pytest.approx(33.7150638888889),
        pytest.approx(-118.319672222222),
    )
    assert not metadata.favorite
    assert metadata.date == datetime.datetime(2021, 4, 8, 16, 4, 55)
    assert metadata.timezone == datetime.timezone(
        datetime.timedelta(days=-1, seconds=61200)
    )
    assert metadata.tz_offset_sec == -25200.0


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
def test_metadata_from_exiftool_person_info():
    """Test metadata_from_exiftool with person info"""
    metadata = metadata_from_exiftool(TEST_IMAGE_2, None)
    assert sorted(metadata.persons) == ["Katie", "Suzy"]


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
@pytest.mark.usefixtures("set_tz_pacific")
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
    assert not metadata.favorite
    assert metadata.date == datetime.datetime(2021, 4, 8, 16, 4, 55)
    assert metadata.timezone == datetime.timezone(
        datetime.timedelta(days=-1, seconds=61200)
    )
    assert metadata.tz_offset_sec == -25200.0


def test_metadata_from_sidecar_persons():
    """Test metadata_from_sidecar with persons info"""
    metadata = metadata_from_sidecar(TEST_IMAGE_2_JSON, None)
    assert sorted(metadata.persons) == ["Katie", "Suzy"]


@pytest.mark.parametrize("filename,sidecar,extra_files", SIDECARS)
def test_get_sidecar_for_file(tmp_path, filename, sidecar, extra_files):
    """Test get_sidecar_for_file"""
    img = tmp_path / filename
    sidecar = tmp_path / sidecar
    img.touch()
    sidecar.touch()
    for extra in extra_files:
        (tmp_path / extra).touch()
    assert get_sidecar_for_file(img) == sidecar


def test_get_sidecar_for_file_none():
    """Test get_sidecar_for_file when there is no sidecar"""
    assert get_sidecar_for_file(TEST_IMAGE_NO_SIDECAR) is None


@pytest.mark.parametrize("data", SIDECAR_TYPES.items())
def test_get_sidecar_filetype(data):
    """Test get_sidecar_filetype()"""
    filename, sidecar_type = data
    assert get_sidecar_filetype(filename) == sidecar_type
