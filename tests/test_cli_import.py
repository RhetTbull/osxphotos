""" Tests which require user interaction to run for osxphotos import command; run with pytest --test-import """

import csv
import datetime
import json
import os
import os.path
import pathlib
import re
import shutil
import sqlite3
import time
import unicodedata
from tempfile import TemporaryDirectory
from typing import Dict

import pytest
from click.testing import CliRunner
from pytest import MonkeyPatch, approx

from osxphotos import PhotosDB, QueryOptions
from osxphotos._constants import UUID_PATTERN
from osxphotos.datetime_utils import datetime_remove_tz
from osxphotos.exiftool import get_exiftool_path
from osxphotos.platform import is_macos
from tests.conftest import get_os_version

if is_macos:
    from photoscript import Photo

    from osxphotos.cli.import_cli import import_main
else:
    pytest.skip(allow_module_level=True)

TERMINAL_WIDTH = 250

TEST_IMAGES_DIR = "tests/test-images"
TEST_IMAGE_1 = "tests/test-images/IMG_4179.jpeg"
TEST_IMAGE_2 = "tests/test-images/faceinfo/exif1.jpg"
TEST_IMAGE_NO_EXIF = "tests/test-images/IMG_NO_EXIF.jpeg"
TEST_VIDEO_1 = "tests/test-images/Jellyfish.mov"
TEST_VIDEO_2 = "tests/test-images/IMG_0670B_NOGPS.MOV"

TEST_DATA = {
    TEST_IMAGE_1: {
        "title": "Waves crashing on rocks",
        "description": "Used for testing osxphotos",
        "keywords": ["osxphotos", "Sümmer"],
        "lat": 33.7150638888889,
        "lon": -118.319672222222,
        "check_templates": [
            "exiftool title: Waves crashing on rocks",
            "exiftool description: Used for testing osxphotos",
            "exiftool keywords: ['osxphotos', 'Sümmer']",
            "exiftool location: (33.7150638888889, -118.319672222222)",
            "title: {exiftool:XMP:Title}: Waves crashing on rocks",
            "description: {exiftool:IPTC:Caption-Abstract}: Used for testing osxphotos",
            "keyword: {exiftool:IPTC:Keywords}: ['osxphotos', 'Sümmer']",
            "album: {filepath.parent}: test-images",
        ],
        "sidecar": {
            "title": "Image Title",
            "description": "Image Description",
            "keywords": ["nature"],
            "lat": 33.71506,
            "lon": -118.31967,
        },
    },
    TEST_VIDEO_1: {
        "title": "Jellyfish",
        "description": "Jellyfish Video",
        # "keywords": ["Travel"], # exiftool doesn't seem to support the binary QuickTime:Keywords
        "keywords": [],
        "lat": 34.0533,
        "lon": -118.2423,
    },
    TEST_VIDEO_2: {
        "title": "",
        "description": "",
        "lat": None,
        "lon": None,
    },
    TEST_IMAGE_2: {
        "albums": ["faceinfo"],
    },
}

PARSE_DATE_DEFAULT_DATE = datetime.datetime(1999, 1, 2, 3, 4, 5)
PARSE_DATE_TEST_DATA = [
    ["img_1234_2020_11_22_12_34_56.jpg", datetime.datetime(2020, 11, 22, 12, 34, 56)],
    ["img_1234_20211122.jpg", datetime.datetime(2021, 11, 22, 3, 4, 5)],
    ["19991231_20221122.jpg", datetime.datetime(2022, 11, 22, 3, 4, 5)],
    [
        "img-123456.jpg",
        datetime.datetime(1999, 1, 2, 12, 34, 56),
    ],  # matches only the time
    ["test_parse_date.jpg", PARSE_DATE_DEFAULT_DATE],
]


# set timezone to avoid issues with comparing dates
@pytest.fixture(scope="module", autouse=True)
def set_timezone():
    """Set timezone to US/Pacific for all tests"""
    old_tz = os.environ.get("TZ")
    os.environ["TZ"] = "US/Pacific"
    time.tzset()
    yield
    if old_tz:
        os.environ["TZ"] = old_tz
    else:
        del os.environ["TZ"]
    time.tzset()


# determine if exiftool installed so exiftool tests can be skipped
try:
    exiftool_path = get_exiftool_path()
except FileNotFoundError:
    exiftool_path = None


def prompt(message):
    """Helper function for tests that require user input"""
    message = f"\n{message}\nPlease answer y/n: "
    answer = input(message)
    return answer.lower() == "y"


def say(msg: str) -> None:
    """Say message with text to speech"""
    os.system(f"say {msg}")


def parse_import_output(output: str) -> Dict[str, str]:
    """Parse output of osxphotos import command and return dict of {image name: uuid} for imported photos"""
    # look for lines that look like this:
    # Imported IMG_4179.jpeg with UUID A62792F0-4524-4529-9931-56E52C95E873

    results = {}
    for line in output.split("\n"):
        pattern = re.compile(r"Imported ([\w\.]+)\s.*UUID\s(" + UUID_PATTERN + r")")
        if match := re.match(pattern, line):
            file = match[1]
            uuid = match[2]
            results[file] = uuid
    return results


########## Interactive tests run first ##########


@pytest.mark.test_import
def test_import():
    """Test basic import"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        ["--verbose", test_image_1],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1


@pytest.mark.test_import
def test_import_dry_run():
    """Test import with --dry-run"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--dry-run",
            "--album",
            "Foo",
            "--keyword",
            "Foo",
            "--title",
            "Foo",
            "--description",
            "Foo",
            "--location",
            "0.0",
            "0.0",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0
    assert "imported 1" in result.output


@pytest.mark.test_import
def test_import_dup_check():
    """Test basic import with --dup-check"""
    say("Please click Import when prompted by Photos to import duplicate photo.")

    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()

    # import first to ensure photo is in library
    result = runner.invoke(
        import_main,
        ["--verbose", test_image_1],
        terminal_width=TERMINAL_WIDTH,
    )

    # now import again with --dup-check
    result = runner.invoke(
        import_main,
        ["--verbose", "--dup-check", test_image_1],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1


@pytest.mark.test_import
def test_import_skip_dups():
    """Test basic import with --skip_dups"""

    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    # import first to ensure photo is in library
    result = runner.invoke(
        import_main,
        ["--verbose", test_image_1],
        terminal_width=TERMINAL_WIDTH,
    )

    # now import again with --skip-dups
    result = runner.invoke(
        import_main,
        ["--verbose", "--skip-dups", test_image_1],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0
    assert "Skipping duplicate" in result.output
    assert "1 skipped" in result.output


@pytest.mark.test_import
def test_import_skip_dups_dup_albums():
    """Test basic import with --skip_dups and --dup-albums"""

    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    # import first to ensure photo is in library
    result = runner.invoke(
        import_main,
        ["--verbose", test_image_1],
        terminal_width=TERMINAL_WIDTH,
    )

    # now import again with --skip-dups
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--skip-dups",
            test_image_1,
            "--album",
            "Test Album",
            "--dup-albums",
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0
    assert "Skipping duplicate" in result.output
    image_name = pathlib.Path(test_image_1).name
    assert f"Adding photo {image_name} to album Test Album" in result.output


@pytest.mark.test_import
def test_import_album():
    """Test basic import to an album"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        ["--verbose", "--album", "My New Album", test_image_1],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    albums = photo_1.albums
    assert len(albums) == 1
    assert albums[0].title == "My New Album"


@pytest.mark.test_import
def test_import_album_2():
    """Test basic import to an album with a "/" in it"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        ["--verbose", "--album", "Folder/My New Album", test_image_1],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    albums = photo_1.albums
    assert len(albums) == 1
    assert albums[0].title == "Folder/My New Album"
    assert albums[0].path_str() == "Folder/My New Album"


@pytest.mark.test_import
def test_import_album_split_folder():
    """Test basic import to an album with a "/" in it and --split-folder"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--album",
            "Folder/My New Album",
            "--split-folder",
            "/",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    albums = photo_1.albums
    assert len(albums) == 1
    assert albums[0].title == "My New Album"
    assert albums[0].path_str() == "Folder/My New Album"


@pytest.mark.test_import
def test_import_album_relative_to():
    """Test import with --relative-to"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--album",
            "{filepath.parent}",
            "--split-folder",
            "/",
            "--relative-to",
            cwd,
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    albums = photo_1.albums
    assert len(albums) == 1
    assert albums[0].title == "test-images"
    assert albums[0].path_str() == "tests/test-images"


@pytest.mark.test_import
def test_import_clear_metadata():
    """Test import with --clear-metadata"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert not photo_1.title
    assert not photo_1.description
    assert not photo_1.keywords


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
@pytest.mark.test_import
def test_import_exiftool():
    """Test import file with --exiftool"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            "--exiftool",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert photo_1.title == TEST_DATA[TEST_IMAGE_1]["title"]
    assert photo_1.description == TEST_DATA[TEST_IMAGE_1]["description"]
    assert photo_1.keywords == TEST_DATA[TEST_IMAGE_1]["keywords"]
    lat, lon = photo_1.location
    assert lat == approx(TEST_DATA[TEST_IMAGE_1]["lat"])
    assert lon == approx(TEST_DATA[TEST_IMAGE_1]["lon"])


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
@pytest.mark.test_import
def test_import_exiftool_video():
    """Test import video file with --exiftool"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_VIDEO_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            "--exiftool",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert photo_1.title == TEST_DATA[TEST_VIDEO_1]["title"]
    assert photo_1.description == TEST_DATA[TEST_VIDEO_1]["description"]
    assert photo_1.keywords == TEST_DATA[TEST_VIDEO_1]["keywords"]
    lat, lon = photo_1.location
    assert lat == approx(TEST_DATA[TEST_VIDEO_1]["lat"])
    assert lon == approx(TEST_DATA[TEST_VIDEO_1]["lon"])


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
@pytest.mark.test_import
def test_import_exiftool_video_no_metadata():
    """Test import video file with --exiftool that has no metadata"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_VIDEO_2)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            "--exiftool",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert photo_1.title == ""
    assert photo_1.description == ""
    assert photo_1.keywords == []
    lat, lon = photo_1.location
    assert lat is None
    assert lon is None


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
@pytest.mark.test_import
def test_import_title():
    """Test import with --title"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            "--title",
            "{exiftool:XMP:Title|upper}",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert photo_1.title == TEST_DATA[TEST_IMAGE_1]["title"].upper()


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
@pytest.mark.test_import
def test_import_description():
    """Test import with --description"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            "--description",
            "{exiftool:XMP:Description|upper}",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert photo_1.description == TEST_DATA[TEST_IMAGE_1]["description"].upper()


@pytest.mark.test_import
def test_import_keyword():
    """Test import with --keyword"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--keyword",
            "Bar",
            "--keyword",
            "Foo",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert sorted(photo_1.keywords) == ["Bar", "Foo"]


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
@pytest.mark.test_import
def test_import_keyword_merge():
    """Test import with --keyword and --merge-keywords"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            "--exiftool",
            "--keyword",
            "Bar",
            "--keyword",
            "Foo",
            "--merge-keywords",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert sorted(photo_1.keywords) == sorted(
        list(set(["Bar", "Foo"] + TEST_DATA[TEST_IMAGE_1]["keywords"]))
    )


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
@pytest.mark.test_import
def test_import_keyword_merge_unicode():
    """Test import with --keyword and --merge-keywords with unicode keywords (#1085)"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            "--exiftool",
            "--keyword",
            "Bar",
            "--keyword",
            "Foo",
            "--keyword",
            unicodedata.normalize("NFD", "Sümmer"),
            "--keyword",
            unicodedata.normalize("NFC", "Sümmer"),
            "--merge-keywords",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert sorted(photo_1.keywords) == sorted(
        list(set(["Bar", "Foo"] + TEST_DATA[TEST_IMAGE_1]["keywords"]))
    )


@pytest.mark.test_import
def test_import_location():
    """Test import file with --location"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            "--location",
            "-45.0",
            "-45.0",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    lat, lon = photo_1.location
    assert lat == approx(-45.0)
    assert lon == approx(-45.0)


@pytest.mark.test_import
def test_import_sidecar():
    """Test import file with --sidecar"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            "--sidecar",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0
    assert "Setting metadata and location from sidecar" in result.output
    assert "Set date" in result.output

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert photo_1.title == TEST_DATA[TEST_IMAGE_1]["sidecar"]["title"]
    assert photo_1.description == TEST_DATA[TEST_IMAGE_1]["sidecar"]["description"]
    assert photo_1.keywords == TEST_DATA[TEST_IMAGE_1]["sidecar"]["keywords"]
    lat, lon = photo_1.location
    assert lat == approx(TEST_DATA[TEST_IMAGE_1]["sidecar"]["lat"])
    assert lon == approx(TEST_DATA[TEST_IMAGE_1]["sidecar"]["lon"])


@pytest.mark.test_import
def test_import_sidecar_ignore_date():
    """Test import file with --sidecar --sidecar-ignore-date"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            "--sidecar",
            "--sidecar-ignore-date",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0
    assert "Setting metadata and location from sidecar" in result.output
    assert "Set date" not in result.output


@pytest.mark.test_import
@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
def test_import_sidecar_template():
    """Test import file with --sidecar-template"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--clear-metadata",
            "--sidecar-template",
            "{filepath}.xmp",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0
    assert "Setting metadata and location from sidecar" in result.output

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert photo_1.title == TEST_DATA[TEST_IMAGE_1]["sidecar"]["title"]
    assert photo_1.description == TEST_DATA[TEST_IMAGE_1]["sidecar"]["description"]
    assert photo_1.keywords == TEST_DATA[TEST_IMAGE_1]["sidecar"]["keywords"]
    lat, lon = photo_1.location
    assert lat == approx(TEST_DATA[TEST_IMAGE_1]["sidecar"]["lat"])
    assert lon == approx(TEST_DATA[TEST_IMAGE_1]["sidecar"]["lon"])


@pytest.mark.test_import
def test_import_glob():
    """Test import with --glob"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        ["--verbose", f"{cwd}/{TEST_IMAGES_DIR}/", "--walk", "--glob", "Pumpk*.jpg"],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0
    assert "imported 2 files" in result.output


@pytest.mark.test_import
def test_import_glob_walk():
    """Test import with --walk --glob"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            f"{cwd}/{TEST_IMAGES_DIR}/",
            "--walk",
            "--glob",
            "exif*.jpg",
            "--album",
            "{filepath.parent.name}",
            "--relative-to",
            f"{cwd}/{TEST_IMAGES_DIR}",
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    assert "imported 4 files" in result.output

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(TEST_IMAGE_2).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1
    assert [a.title for a in photo_1.albums] == TEST_DATA[TEST_IMAGE_2]["albums"]


@pytest.mark.skipif(exiftool_path is None, reason="exiftool not installed")
@pytest.mark.test_import
def test_import_check_templates():
    """Test import file with --check-templates"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--exiftool",
            "--title",
            "{exiftool:XMP:Title}",
            "--description",
            "{exiftool:IPTC:Caption-Abstract}",
            "--keyword",
            "{exiftool:IPTC:Keywords}",
            "--album",
            "{filepath.parent}",
            "--relative-to",
            f"{cwd}/tests",
            "--check-templates",
            test_image_1,
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    # assert result.output == "foo"
    assert result.exit_code == 0
    output = result.output.splitlines()
    output.pop(0)

    for idx, line in enumerate(output):
        assert line == TEST_DATA[TEST_IMAGE_1]["check_templates"][idx]


@pytest.mark.test_import
def test_import_function_template():
    """Test import with a function template"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    function = os.path.join(cwd, "examples/template_function_import.py")
    with TemporaryDirectory() as tempdir:
        test_image = shutil.copy(
            test_image_1, os.path.join(tempdir, "MyAlbum_IMG_0001.jpg")
        )
        runner = CliRunner()
        result = runner.invoke(
            import_main,
            [
                "--verbose",
                "--album",
                "{function:" + function + "::example}",
                test_image,
            ],
            terminal_width=TERMINAL_WIDTH,
        )

        assert result.exit_code == 0

        import_data = parse_import_output(result.output)
        file_1 = pathlib.Path(test_image).name
        uuid_1 = import_data[file_1]
        photo_1 = Photo(uuid_1)

        assert photo_1.filename == file_1
        albums = [a.title for a in photo_1.albums]
        assert albums == ["MyAlbum"]


@pytest.mark.test_import
def test_import_report():
    """test import with --report option"""

    runner = CliRunner()
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)

    with runner.isolated_filesystem():
        result = runner.invoke(
            import_main,
            [
                test_image_1,
                "--report",
                "report.csv",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Wrote import report" in result.output
        assert os.path.exists("report.csv")
        with open("report.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert filenames == [pathlib.Path(TEST_IMAGE_1).name]

        # test report gets overwritten
        result = runner.invoke(
            import_main,
            [
                test_image_1,
                "--report",
                "report.csv",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        with open("report.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert filenames == [pathlib.Path(TEST_IMAGE_1).name]

        # test report with --append
        result = runner.invoke(
            import_main,
            [
                test_image_1,
                "--report",
                "report.csv",
                "--append",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        with open("report.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert filenames == [
            pathlib.Path(TEST_IMAGE_1).name,
            pathlib.Path(TEST_IMAGE_1).name,
        ]


@pytest.mark.test_import
def test_import_report_json():
    """test import with --report option with json output"""

    runner = CliRunner()
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)

    with runner.isolated_filesystem():
        result = runner.invoke(
            import_main,
            [
                test_image_1,
                "--report",
                "report.json",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Wrote import report" in result.output
        assert os.path.exists("report.json")
        with open("report.json", "r") as f:
            rows = json.load(f)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert filenames == [pathlib.Path(TEST_IMAGE_1).name]

        # test report gets overwritten
        result = runner.invoke(
            import_main,
            [
                test_image_1,
                "--report",
                "report.json",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Wrote import report" in result.output
        assert os.path.exists("report.json")
        with open("report.json", "r") as f:
            rows = json.load(f)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert filenames == [pathlib.Path(TEST_IMAGE_1).name]

        # test report with --append
        result = runner.invoke(
            import_main,
            [
                test_image_1,
                "--report",
                "report.json",
                "--append",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Wrote import report" in result.output
        assert os.path.exists("report.json")
        with open("report.json", "r") as f:
            rows = json.load(f)
        filenames = [str(pathlib.Path(row["filename"]).name) for row in rows]
        assert filenames == [
            pathlib.Path(TEST_IMAGE_1).name,
            pathlib.Path(TEST_IMAGE_1).name,
        ]


@pytest.mark.test_import
@pytest.mark.parametrize("report_file", ["report.db", "report.sqlite"])
def test_import_report_sqlite(report_file):
    """test import with --report option with sqlite output"""

    runner = CliRunner()
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)

    with runner.isolated_filesystem():
        result = runner.invoke(
            import_main,
            [
                test_image_1,
                "--report",
                report_file,
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Wrote import report" in result.output
        assert os.path.exists(report_file)
        conn = sqlite3.connect(report_file)
        c = conn.cursor()
        c.execute("SELECT filename FROM report")
        filenames = [str(pathlib.Path(row[0]).name) for row in c.fetchall()]
        assert filenames == [pathlib.Path(TEST_IMAGE_1).name]

        # test report gets overwritten
        result = runner.invoke(
            import_main,
            [
                test_image_1,
                "--report",
                report_file,
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Wrote import report" in result.output
        assert os.path.exists(report_file)
        conn = sqlite3.connect(report_file)
        c = conn.cursor()
        c.execute("SELECT filename FROM report")
        filenames = [str(pathlib.Path(row[0]).name) for row in c.fetchall()]
        assert filenames == [pathlib.Path(TEST_IMAGE_1).name]

        # test report with --append
        result = runner.invoke(
            import_main,
            [
                test_image_1,
                "--report",
                report_file,
                "--append",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Wrote import report" in result.output
        assert os.path.exists(report_file)
        conn = sqlite3.connect(report_file)
        c = conn.cursor()
        c.execute("SELECT filename FROM report")
        filenames = [str(pathlib.Path(row[0]).name) for row in c.fetchall()]
        assert filenames == [
            pathlib.Path(TEST_IMAGE_1).name,
            pathlib.Path(TEST_IMAGE_1).name,
        ]


@pytest.mark.test_import
def test_import_report_invalid_name():
    """test import with --report option with invalid report"""

    runner = CliRunner()
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)

    with runner.isolated_filesystem():
        result = runner.invoke(
            import_main,
            [
                test_image_1,
                "--report",
                "report",  # invalid filename, no extension
                "--verbose",
            ],
        )
        assert result.exit_code != 0


@pytest.mark.test_import
def test_import_resume(monkeypatch: MonkeyPatch, tmpdir):
    """Test import with --resume"""

    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", os.fspath(str(tmpdir)))

    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        ["--verbose", test_image_1],
        terminal_width=TERMINAL_WIDTH,
    )

    assert result.exit_code == 0

    import_data = parse_import_output(result.output)
    file_1 = pathlib.Path(test_image_1).name
    uuid_1 = import_data[file_1]
    photo_1 = Photo(uuid_1)

    assert photo_1.filename == file_1

    # test resume
    test_image_2 = os.path.join(cwd, TEST_IMAGE_2)
    result = runner.invoke(
        import_main,
        ["--verbose", "--resume", test_image_1, test_image_2],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    assert "Skipping" in result.output
    assert "1 skipped" in result.output
    assert "imported 1" in result.output


@pytest.mark.test_import
@pytest.mark.parametrize("data", PARSE_DATE_TEST_DATA)
def test_import_parse_date(tmp_path: pathlib.Path, data: tuple[str, datetime.datetime]):
    """Test import with --parse-date"""

    img_name = data[0]
    date = data[1]

    # set up test images
    os.environ["TZ"] = "US/Pacific"
    cwd = os.getcwd()
    test_image_source = os.path.join(cwd, TEST_IMAGE_NO_EXIF)

    test_file = tmp_path / img_name
    shutil.copy(test_image_source, test_file)

    # set file time to default date
    os.utime(
        test_file,
        (PARSE_DATE_DEFAULT_DATE.timestamp(), PARSE_DATE_DEFAULT_DATE.timestamp()),
    )

    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--parse-date",
            "img_*_%Y_%m_%d_%H_%M_%S|img_{4}_%Y%m%d|_%Y%m%d.|-%H%M%S.",
            str(test_file),
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    # verify that the date was parsed correctly
    photosdb = PhotosDB()
    photo = photosdb.query(QueryOptions(name=[img_name]))[0]
    assert datetime_remove_tz(photo.date) == date


@pytest.mark.test_import
def test_import_parse_folder_date(tmp_path: pathlib.Path):
    """Test import with --parse-folder-date"""

    # set up test images
    os.environ["TZ"] = "US/Pacific"
    cwd = os.getcwd()
    test_image_source = os.path.join(cwd, TEST_IMAGE_NO_EXIF)

    test_dir = tmp_path / "2021-12-11"
    img_name = "123457.jpg"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / img_name
    shutil.copy(test_image_source, test_file)

    # set file time to default date
    os.utime(
        test_file,
        (PARSE_DATE_DEFAULT_DATE.timestamp(), PARSE_DATE_DEFAULT_DATE.timestamp()),
    )

    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [
            "--verbose",
            "--parse-date",
            "%H%M%S.",
            "--parse-folder-date",
            "%Y-%m-%d",
            str(test_file),
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    # verify that the date was parsed correctly
    photosdb = PhotosDB()
    photo = photosdb.query(QueryOptions(name=[img_name]))[0]
    assert datetime_remove_tz(photo.date) == datetime.datetime(2021, 12, 11, 12, 34, 57)


@pytest.mark.test_import
def test_import_post_function():
    """Test import with --post-function"""

    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)

    runner = CliRunner()
    # pylint: disable=not-context-manager
    with runner.isolated_filesystem():
        with open("foo1.py", "w") as f:
            f.writelines(
                [
                    "def foo(photo, filepath, verbose, report_record, **kwargs):\n",
                    "    verbose('FOO BAR')\n",
                ]
            )

        tempdir = os.getcwd()
        result = runner.invoke(
            import_main,
            [
                "import",
                "--verbose",
                test_image_1,
                "--post-function",
                f"{tempdir}/foo1.py::foo",
            ],
        )
        assert result.exit_code == 0
        assert "FOO BAR" in result.output


@pytest.mark.test_import
def test_import_check():
    """test import with --check option"""
    cwd = os.getcwd()
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [f"{cwd}/{TEST_IMAGES_DIR}", "--walk", "--check", "--verbose"],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    assert "tests/test-images/IMG_3984.jpeg, not imported" in result.output
    assert "tests/test-images/IMG_3092.heic, imported" in result.output


@pytest.mark.test_import
def test_import_check_not():
    """test import with --check-not option"""
    cwd = os.getcwd()
    runner = CliRunner()
    result = runner.invoke(
        import_main,
        [f"{cwd}/{TEST_IMAGES_DIR}", "--walk", "--check-not", "--verbose"],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    assert "tests/test-images/IMG_3984.jpeg" in result.output
