""" pytest test configuration """
import os
import pathlib

import pytest
from applescript import AppleScript
from photoscript.utils import ditto

from osxphotos.exiftool import _ExifToolProc


def get_os_version():
    import platform

    # returns tuple containing OS version
    # e.g. 10.13.6 = (10, 13, 6)
    version = platform.mac_ver()[0].split(".")
    if len(version) == 2:
        (ver, major) = version
        minor = "0"
    elif len(version) == 3:
        (ver, major, minor) = version
    else:
        raise (
            ValueError(
                f"Could not parse version string: {platform.mac_ver()} {version}"
            )
        )
    return (ver, major, minor)


OS_VER = get_os_version()[1]
if OS_VER == "15":
    TEST_LIBRARY = "tests/Test-10.15.7.photoslibrary"
else:
    TEST_LIBRARY = None
    pytest.exit("This test suite currently only runs on MacOS Catalina ")


@pytest.fixture(autouse=True)
def reset_singletons():
    """ Need to clean up any ExifTool singletons between tests """
    _ExifToolProc.instance = None


def pytest_addoption(parser):
    parser.addoption(
        "--addalbum",
        action="store_true",
        default=False,
        help="run --add-exported-to-album tests",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "addalbum: mark test as requiring --addalbum to run"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--addalbum"):
        # --addalbum given in cli: do not skip addalbum tests (these require interactive test)
        return
    skip_addalbum = pytest.mark.skip(reason="need --addalbum option to run")
    for item in items:
        if "addalbum" in item.keywords:
            item.add_marker(skip_addalbum)


def copy_photos_library(photos_library=TEST_LIBRARY, delay=0):
    """ copy the test library and open Photos, returns path to copied library """
    script = AppleScript(
        """
        tell application "Photos"
            quit
        end tell
        """
    )
    script.run()
    src = pathlib.Path(os.getcwd()) / photos_library
    picture_folder = (
        pathlib.Path(os.environ["PHOTOSCRIPT_PICTURES_FOLDER"])
        if "PHOTOSCRIPT_PICTURES_FOLDER" in os.environ
        else pathlib.Path("~/Pictures")
    )
    picture_folder = picture_folder.expanduser()
    if not picture_folder.is_dir():
        pytest.exit(f"Invalid picture folder: '{picture_folder}'")
    dest = picture_folder / photos_library
    ditto(src, dest)
    script = AppleScript(
        f"""
            set tries to 0
            repeat while tries < 5
                try
                    tell application "Photos"
                        activate
                        delay 3 
                        open POSIX file "{dest}"
                        delay {delay}
                    end tell
                    set tries to 5
                on error
                    set tries to tries + 1
                end try
            end repeat
        """
    )
    script.run()
    return dest


@pytest.fixture
def addalbum_library():
    copy_photos_library(delay=10)
