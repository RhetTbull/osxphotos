""" Tests which require user interaction to run for osxphotos import command; run with pytest --test-import """

import os
import os.path
import pathlib
import re
import time
from typing import Dict

import pytest
from click.testing import CliRunner
from photoscript import Photo
from pytest import approx

from osxphotos import PhotosDB
from osxphotos.cli.import_cli import import_cli
from osxphotos.exiftool import ExifTool, get_exiftool_path
from tests.conftest import get_os_version

TERMINAL_WIDTH = 250

TEST_IMAGE_1 = "tests/test-images/IMG_4179.jpeg"
TEST_VIDEO_1 = "tests/test-images/Jellyfish.mov"
TEST_VIDEO_2 = "tests/test-images/IMG_0670B_NOGPS.MOV"

TEST_DATA = {
    TEST_IMAGE_1: {
        "title": "Waves crashing on rocks",
        "description": "Used for testing osxphotos",
        "keywords": ["osxphotos"],
        "lat": 33.7150638888889,
        "lon": -118.319672222222,
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
}

# set timezone to avoid issues with comparing dates
os.environ["TZ"] = "US/Pacific"
time.tzset()


# determine if exiftool installed so exiftool tests can be skipped
try:
    exiftool_path = get_exiftool_path()
except FileNotFoundError:
    exiftool_path = None

OS_VER = get_os_version()[1]
if OS_VER != "15":
    pytest.skip(allow_module_level=True)


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
        pattern = re.compile(
            r"Imported ([\w\.]+)\s.*UUID\s([0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12})"
        )
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
        import_cli,
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
def test_import_dup_check():
    """Test basic import with --dup-check"""
    say("Please click Import when prompted by Photos to import duplicate photo.")

    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_cli,
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
def test_import_album():
    """Test basic import to an album"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_cli,
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
        import_cli,
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
def test_import_album_slit_folder():
    """Test basic import to an album with a "/" in it and --split-folder"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_cli,
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
        import_cli,
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
        import_cli,
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
        import_cli,
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
        import_cli,
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
        import_cli,
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
        import_cli,
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
        import_cli,
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
        import_cli,
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
        import_cli,
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
    assert sorted(photo_1.keywords) == ["Bar", "Foo", "osxphotos"]


@pytest.mark.test_import
def test_import_location():
    """Test import file with --location"""
    cwd = os.getcwd()
    test_image_1 = os.path.join(cwd, TEST_IMAGE_1)
    runner = CliRunner()
    result = runner.invoke(
        import_cli,
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
