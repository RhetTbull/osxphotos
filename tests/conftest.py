""" pytest test configuration """
import os
import pathlib
import shutil
import tempfile
import time

import photoscript
import pytest
from applescript import AppleScript
from photoscript.utils import ditto

from osxphotos.exiftool import _ExifToolProc

from .test_catalina_10_15_7 import UUID_DICT_LOCAL

# run timewarp tests (configured with --timewarp)
TEST_TIMEWARP = False

# run import tests (configured with --test-import)
TEST_IMPORT = False

# run sync tests (configured with --test-sync)
TEST_SYNC = False

# run add-locations tests (configured with --test-add-locations)
TEST_ADD_LOCATIONS = False

# don't clean up crash logs (configured with --no-cleanup)
NO_CLEANUP = False


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


OS_VER = get_os_version()
if OS_VER[0] == "10" and OS_VER[1] == "15":
    # Catalina
    TEST_LIBRARY = "tests/Test-10.15.7.photoslibrary"
    TEST_LIBRARY_IMPORT = TEST_LIBRARY
    TEST_LIBRARY_SYNC = TEST_LIBRARY
    from tests.config_timewarp_catalina import TEST_LIBRARY_TIMEWARP

    TEST_LIBRARY_ADD_LOCATIONS = None
elif OS_VER[0] == "13":
    # Ventura
    TEST_LIBRARY = "tests/Test-13.0.0.photoslibrary"
    TEST_LIBRARY_IMPORT = TEST_LIBRARY
    TEST_LIBRARY_SYNC = TEST_LIBRARY
    from tests.config_timewarp_ventura import TEST_LIBRARY_TIMEWARP

    TEST_LIBRARY_ADD_LOCATIONS = "tests/Test-13.0.0.photoslibrary"
else:
    TEST_LIBRARY = None
    TEST_LIBRARY_TIMEWARP = None
    TEST_LIBRARY_SYNC = None
    TEST_LIBRARY_ADD_LOCATIONS = None


@pytest.fixture(scope="session", autouse=True)
def setup_photos_timewarp():
    if not TEST_TIMEWARP:
        return
    copy_photos_library(TEST_LIBRARY_TIMEWARP, delay=5)


@pytest.fixture(scope="session", autouse=True)
def setup_photos_import():
    if not TEST_IMPORT:
        return
    copy_photos_library(TEST_LIBRARY_IMPORT, delay=10)


@pytest.fixture(scope="session", autouse=True)
def setup_photos_sync():
    if not TEST_SYNC:
        return
    copy_photos_library(TEST_LIBRARY_SYNC, delay=10)


@pytest.fixture(scope="session", autouse=True)
def setup_photos_add_locations():
    if not TEST_ADD_LOCATIONS:
        return
    copy_photos_library(TEST_LIBRARY_ADD_LOCATIONS, delay=10)


@pytest.fixture(autouse=True)
def reset_singletons():
    """Need to clean up any ExifTool singletons between tests"""
    _ExifToolProc.instance = None


def pytest_addoption(parser):
    parser.addoption(
        "--addalbum",
        action="store_true",
        default=False,
        help="run --add-exported-to-album tests",
    )
    parser.addoption(
        "--timewarp", action="store_true", default=False, help="run --timewarp tests"
    )
    parser.addoption(
        "--test-import",
        action="store_true",
        default=False,
        help="run `osxphotos import` tests",
    )
    parser.addoption(
        "--test-sync",
        action="store_true",
        default=False,
        help="run `osxphotos sync` tests",
    )
    parser.addoption(
        "--test-add-locations",
        action="store_true",
        default=False,
        help="run `osxphotos add-locations` tests",
    )
    parser.addoption(
        "--no-cleanup",
        action="store_true",
        default=False,
        help="don't clean up crash logs after tests",
    )


def pytest_configure(config):
    if (
        sum(
            bool(x)
            for x in [
                config.getoption("--addalbum"),
                config.getoption("--timewarp"),
                config.getoption("--test-import"),
                config.getoption("--test-sync"),
            ]
        )
        > 1
    ):
        pytest.exit(
            "--addalbum, --timewarp, --test-import, --test-sync are mutually exclusive"
        )

    config.addinivalue_line(
        "markers", "addalbum: mark test as requiring --addalbum to run"
    )
    config.addinivalue_line(
        "markers", "timewarp: mark test as requiring --timewarp to run"
    )
    config.addinivalue_line(
        "markers", "test_import: mark test as requiring --test-import to run"
    )
    config.addinivalue_line(
        "markers", "test_sync: mark test as requiring --test-sync to run"
    )
    config.addinivalue_line(
        "markers",
        "test_add_locations: mark test as requiring --test-add-locations to run",
    )

    # this is hacky but I can't figure out how to check config options in other fixtures
    if config.getoption("--timewarp"):
        global TEST_TIMEWARP
        TEST_TIMEWARP = True

    if config.getoption("--test-import"):
        global TEST_IMPORT
        TEST_IMPORT = True

    if config.getoption("--test-sync"):
        global TEST_SYNC
        TEST_SYNC = True

    if config.getoption("--test-add-locations"):
        global TEST_ADD_LOCATIONS
        TEST_ADD_LOCATIONS = True

    if config.getoption("--no-cleanup"):
        global NO_CLEANUP
        NO_CLEANUP = True


def pytest_collection_modifyitems(config, items):
    if not (config.getoption("--addalbum") and TEST_LIBRARY is not None):
        skip_addalbum = pytest.mark.skip(
            reason="need --addalbum option and MacOS Catalina to run"
        )
        for item in items:
            if "addalbum" in item.keywords:
                item.add_marker(skip_addalbum)

    if not (config.getoption("--timewarp") and TEST_LIBRARY_TIMEWARP is not None):
        skip_timewarp = pytest.mark.skip(
            reason="need --timewarp option and MacOS Catalina to run"
        )
        for item in items:
            if "timewarp" in item.keywords:
                item.add_marker(skip_timewarp)

    if not (config.getoption("--test-import") and TEST_LIBRARY_IMPORT is not None):
        skip_test_import = pytest.mark.skip(
            reason="need --test-import option and MacOS Catalina or Ventura to run"
        )
        for item in items:
            if "test_import" in item.keywords:
                item.add_marker(skip_test_import)

    if not (config.getoption("--test-sync") and TEST_LIBRARY_SYNC is not None):
        skip_test_sync = pytest.mark.skip(
            reason="need --test-sync option and MacOS Catalina to run"
        )
        for item in items:
            if "test_sync" in item.keywords:
                item.add_marker(skip_test_sync)

    if not (
        config.getoption("--test-add-locations")
        and TEST_LIBRARY_ADD_LOCATIONS is not None
    ):
        skip_test_sync = pytest.mark.skip(
            reason="need --test-add-locations option and MacOS Ventura to run"
        )
        for item in items:
            if "test_add_locations" in item.keywords:
                item.add_marker(skip_test_sync)


def copy_photos_library(photos_library, delay=0, open=True):
    """copy the test library and open Photos, returns path to copied library"""

    # quit Photos if it's running
    photoslib = photoscript.PhotosLibrary()
    photoslib.quit()

    src = pathlib.Path(os.getcwd()) / photos_library
    picture_folder = (
        pathlib.Path(os.environ["PHOTOSCRIPT_PICTURES_FOLDER"])
        if "PHOTOSCRIPT_PICTURES_FOLDER" in os.environ
        else pathlib.Path("~/Pictures")
    )
    picture_folder = picture_folder.expanduser()
    if not picture_folder.is_dir():
        pytest.exit(f"Invalid picture folder: '{picture_folder}'")
    dest = picture_folder / pathlib.Path(photos_library).name

    # copy src directory to dest directory, removing it if it already exists
    shutil.rmtree(str(dest), ignore_errors=True)

    print(f"copying {src} to {picture_folder} ...")
    copyFolder = AppleScript(
        """
        on copyFolder(sourceFolder, destinationFolder)
            -- sourceFolder and destinationFolder are strings of POSIX paths
            set sourceFolder to POSIX file sourceFolder
            set destinationFolder to POSIX file destinationFolder
            tell application "Finder"
                duplicate sourceFolder to destinationFolder
            end tell
        end copyFolder
        """
    )
    copyFolder.call("copyFolder", str(src), str(picture_folder))

    # open Photos
    if open:
        # sometimes doesn't open the first time
        time.sleep(delay)
        photoslib.open(str(dest))
        time.sleep(delay)
        photoslib.open(str(dest))

    return dest


@pytest.fixture
def addalbum_library():
    copy_photos_library(TEST_LIBRARY, delay=10)


def copy_photos_library_to_path(photos_library_path: str, dest_path: str) -> str:
    """Copy a photos library to a folder"""
    ditto(photos_library_path, dest_path)
    return dest_path


@pytest.fixture(scope="session", autouse=True)
def delete_crash_logs():
    """Delete left over crash logs from tests that were supposed to crash"""
    yield
    path = pathlib.Path(os.getcwd()) / "osxphotos_crash.log"
    if path.is_file() and not NO_CLEANUP:
        path.unlink()


@pytest.fixture
def photoslib():
    return photoscript.PhotosLibrary()


@pytest.fixture
def suspend_capture(pytestconfig):
    class suspend_guard:
        def __init__(self):
            self.capmanager = pytestconfig.pluginmanager.getplugin("capturemanager")

        def __enter__(self):
            self.capmanager.suspend_global_capture(in_=True)

        def __exit__(self, _1, _2, _3):
            self.capmanager.resume_global_capture()

    yield suspend_guard()


@pytest.fixture
def output_file():
    """Create a temporary filename for writing output"""
    tempdir = tempfile.gettempdir()
    fd, filename = tempfile.mkstemp(dir=tempdir)
    os.close(fd)
    yield filename
    os.remove(filename)
