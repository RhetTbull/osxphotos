"""pytest test configuration"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import tempfile
import time
from contextlib import contextmanager

import pytest

from osxphotos.datetime_utils import (
    datetime_naive_to_local,
    datetime_remove_tz,
    get_local_tz,
)
from osxphotos.platform import is_macos

if is_macos:
    import photoscript
    from applescript import AppleScript
    from photoscript.utils import ditto

    from .test_catalina_10_15_7 import UUID_DICT_LOCAL

from osxphotos.exiftool import _ExifToolProc

# run timewarp tests (configured with --timewarp)
TEST_TIMEWARP = False

# run photodates tests (configured with --photodates)
TEST_PHOTODATES = False

# run import tests (configured with --test-import)
TEST_IMPORT = False

# run import tests (configured with --test-import-takeout)
TEST_IMPORT_TAKEOUT = False

# run sync tests (configured with --test-sync)
TEST_SYNC = False

# run add-locations tests (configured with --test-add-locations)
TEST_ADD_LOCATIONS = False

# run batch-edit tests (configured with --test-batch-edit)
TEST_BATCH_EDIT = False

# don't clean up crash logs (configured with --no-cleanup)
NO_CLEANUP = False

LIBRARY_COPY_DELAY = 5


def get_os_version():
    if not is_macos:
        return (None, None, None)

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


# Configure test libraries for different OS versions
# TODO: this is hacky and should be refactored
TEST_LIBRARY = None
TEST_LIBRARY_TIMEWARP = None
TEST_LIBRARY_SYNC = None
TEST_LIBRARY_ADD_LOCATIONS = None
TEST_LIBRARY_TAKEOUT = None
TEST_LIBRARY_PHOTODATES = None

OS_VER = get_os_version() if is_macos else [None, None]
if is_macos and (OS_VER[0] == "10" and OS_VER[1] in ("15", "16")):
    # Catalina
    TEST_LIBRARY = "tests/Test-10.15.7.photoslibrary"
    TEST_LIBRARY_IMPORT = TEST_LIBRARY
    TEST_LIBRARY_SYNC = TEST_LIBRARY
    TEST_LIBRARY_TAKEOUT = None
    TEST_LIBRARY_TIMEWARP = None  # these tests do not run on macOS < 13
    TEST_LIBRARY_PHOTODATES = TEST_LIBRARY
    TEST_LIBRARY_ADD_LOCATIONS = None

if is_macos and (OS_VER[0] == "15"):
    # Sequoia
    TEST_LIBRARY = "tests/Test-15.4.1.photoslibrary"
    TEST_LIBRARY_IMPORT = TEST_LIBRARY
    TEST_LIBRARY_SYNC = "tests/Test-10.15.7.photoslibrary"
    TEST_LIBRARY_TAKEOUT = TEST_LIBRARY
    from tests.config_timewarp_ventura import TEST_LIBRARY_TIMEWARP

    TEST_LIBRARY_PHOTODATES = TEST_LIBRARY
    TEST_LIBRARY_ADD_LOCATIONS = TEST_LIBRARY

elif is_macos and (OS_VER[0] == "12" and OS_VER[1] in ("7",)):
    # Monterey
    TEST_LIBRARY = "tests/Test-12.0.1.photoslibrary"
    TEST_LIBRARY_IMPORT = TEST_LIBRARY
    TEST_LIBRARY_SYNC = TEST_LIBRARY
    TEST_LIBRARY_TAKEOUT = None
    TEST_LIBRARY_TIMEWARP = None  # these tests do not run on macOS < 13
    TEST_LIBRARY_PHOTODATES = TEST_LIBRARY
    TEST_LIBRARY_ADD_LOCATIONS = None

elif not is_macos or int(OS_VER[0]) >= 13:
    # Ventura
    TEST_LIBRARY = "tests/Test-13.0.0.photoslibrary"
    TEST_LIBRARY_IMPORT = TEST_LIBRARY
    TEST_LIBRARY_SYNC = "tests/Test-10.15.7.photoslibrary"
    TEST_LIBRARY_TAKEOUT = "tests/Test-Empty-Library-Ventura-13-5.photoslibrary"
    from tests.config_timewarp_ventura import TEST_LIBRARY_TIMEWARP

    TEST_LIBRARY_PHOTODATES = TEST_LIBRARY
    TEST_LIBRARY_ADD_LOCATIONS = "tests/Test-13.0.0.photoslibrary"


@pytest.fixture(scope="session", autouse=is_macos)
def setup_photos_timewarp():
    if not TEST_TIMEWARP:
        return
    copy_photos_library(TEST_LIBRARY_TIMEWARP, delay=LIBRARY_COPY_DELAY)


@pytest.fixture(scope="session", autouse=is_macos)
def setup_photos_batchedit():
    if not TEST_BATCH_EDIT:
        return
    copy_photos_library(TEST_LIBRARY, delay=LIBRARY_COPY_DELAY)


@pytest.fixture(scope="session", autouse=is_macos)
def setup_photos_photodates():
    if not TEST_PHOTODATES:
        return
    copy_photos_library(TEST_LIBRARY_PHOTODATES, delay=LIBRARY_COPY_DELAY)


@pytest.fixture(scope="session", autouse=is_macos)
def setup_photos_import():
    if not TEST_IMPORT:
        return
    copy_photos_library(TEST_LIBRARY_IMPORT, delay=LIBRARY_COPY_DELAY)


@pytest.fixture(scope="session", autouse=is_macos)
def setup_photos_import_takeout():
    if not TEST_IMPORT_TAKEOUT:
        return
    copy_photos_library(TEST_LIBRARY_TAKEOUT, delay=LIBRARY_COPY_DELAY)


@pytest.fixture(scope="session", autouse=is_macos)
def setup_photos_sync():
    if not TEST_SYNC:
        return
    copy_photos_library(TEST_LIBRARY_SYNC, delay=LIBRARY_COPY_DELAY)


@pytest.fixture(scope="session", autouse=is_macos)
def setup_photos_add_locations():
    if not TEST_ADD_LOCATIONS:
        return
    copy_photos_library(TEST_LIBRARY_ADD_LOCATIONS, delay=LIBRARY_COPY_DELAY)


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
        "--photodates",
        action="store_true",
        default=False,
        help="run --photodates tests",
    )
    parser.addoption(
        "--test-import",
        action="store_true",
        default=False,
        help="run `osxphotos import` tests",
    )
    parser.addoption(
        "--test-import-takeout",
        action="store_true",
        default=False,
        help="run `osxphotos import` tests with Google Takeout archive",
    )
    parser.addoption("--test-batch-edit", action="store_true", default=False)
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
                config.getoption("--photodates"),
                config.getoption("--test-import"),
                config.getoption("--test-import-takeout"),
                config.getoption("--test-sync"),
                config.getoption("--test-batch-edit"),
                0,
            ]
        )
        > 1
    ):
        pytest.exit(
            "--addalbum, --timewarp, --test-import, --test-import-takeout, --test-sync, --test-batch-edit are mutually exclusive"
        )

    config.addinivalue_line(
        "markers", "addalbum: mark test as requiring --addalbum to run"
    )
    config.addinivalue_line(
        "markers", "timewarp: mark test as requiring --timewarp to run"
    )
    config.addinivalue_line(
        "markers", "photodates: mark test as requiring --photodates to run"
    )
    config.addinivalue_line(
        "markers", "test_import: mark test as requiring --test-import to run"
    )
    config.addinivalue_line(
        "markers",
        "test_import_takeout: mark test as requiring --test-import-takeout to run",
    )
    config.addinivalue_line(
        "markers", "test_sync: mark test as requiring --test-sync to run"
    )
    config.addinivalue_line(
        "markers",
        "test_add_locations: mark test as requiring --test-add-locations to run",
    )
    config.addinivalue_line(
        "markers", "test_batch_edit: mark test as requiring --test-batch-edit to run"
    )

    # this is hacky but I can't figure out how to check config options in other fixtures
    if config.getoption("--timewarp"):
        global TEST_TIMEWARP
        TEST_TIMEWARP = True

    if config.getoption("--photodates"):
        global TEST_PHOTODATES
        TEST_PHOTODATES = True

    if config.getoption("--test-import"):
        global TEST_IMPORT
        TEST_IMPORT = True

    if config.getoption("--test-import-takeout"):
        global TEST_IMPORT_TAKEOUT
        TEST_IMPORT_TAKEOUT = True

    if config.getoption("--test-sync"):
        global TEST_SYNC
        TEST_SYNC = True

    if config.getoption("--test-add-locations"):
        global TEST_ADD_LOCATIONS
        TEST_ADD_LOCATIONS = True

    if config.getoption("--no-cleanup"):
        global NO_CLEANUP
        NO_CLEANUP = True

    if config.getoption("--test-batch-edit"):
        global TEST_BATCH_EDIT
        TEST_BATCH_EDIT = True


def pytest_collection_modifyitems(config, items):
    if not (config.getoption("--addalbum") and TEST_LIBRARY is not None):
        skip_addalbum = pytest.mark.skip(reason="need --addalbum option to run")
        for item in items:
            if "addalbum" in item.keywords:
                item.add_marker(skip_addalbum)

    if not (config.getoption("--timewarp") and TEST_LIBRARY_TIMEWARP is not None):
        skip_timewarp = pytest.mark.skip(reason="need --timewarp option to run")
        for item in items:
            if "timewarp" in item.keywords:
                item.add_marker(skip_timewarp)

    if not (config.getoption("--photodates") and TEST_LIBRARY_PHOTODATES is not None):
        skip_photodates = pytest.mark.skip(reason="need --photodates option to run")
        for item in items:
            if "photodates" in item.keywords:
                item.add_marker(skip_photodates)

    if not (config.getoption("--test-import") and TEST_LIBRARY_IMPORT is not None):
        skip_test_import = pytest.mark.skip(reason="need --test-import option to run")
        for item in items:
            if "test_import" in item.keywords:
                item.add_marker(skip_test_import)

    if not (
        config.getoption("--test-import-takeout") and TEST_LIBRARY_TAKEOUT is not None
    ):
        skip_test_import_takeout = pytest.mark.skip(
            reason="need --test-import-takeout option to run"
        )
        for item in items:
            if "test_import_takeout" in item.keywords:
                item.add_marker(skip_test_import_takeout)

    if not (config.getoption("--test-sync") and TEST_LIBRARY_SYNC is not None):
        skip_test_sync = pytest.mark.skip(reason="need --test-sync option to run")
        for item in items:
            if "test_sync" in item.keywords:
                item.add_marker(skip_test_sync)

    if not (config.getoption("--test-batch-edit")):
        skip_test_batch_edit = pytest.mark.skip(
            reason="need --test-batch-edit option to run"
        )
        for item in items:
            if "test_batch_edit" in item.keywords:
                item.add_marker(skip_test_batch_edit)

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
    if is_macos:
        ditto(photos_library_path, dest_path)
    else:
        shutil.copytree(photos_library_path, dest_path)
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


@contextmanager
def set_timezone(timezone):
    try:
        old_tz = os.environ.get("TZ")
        os.environ["TZ"] = timezone
        time.tzset()
        yield
    finally:
        if old_tz is None:
            del os.environ["TZ"]
        else:
            os.environ["TZ"] = old_tz
        time.tzset()


@pytest.fixture
def set_tz_pacific():
    timezone = "America/Los_Angeles"
    with set_timezone(timezone):
        yield


@pytest.fixture
def set_tz_central():
    timezone = "America/Chicago"
    with set_timezone(timezone):
        yield


@pytest.fixture
def set_tz_cest():
    timezone = "CEST"
    with set_timezone(timezone):
        yield


@pytest.fixture
def set_tz_jerusalem():
    timezone = "Asia/Jerusalem"
    with set_timezone(timezone):
        yield


_UUID_PATTERN = re.compile(
    r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}"
)

# Header: "Exporting FILENAME (UUID_INFO) (N/M)" or
#          "Exporting edited version of FILENAME (UUID_INFO)"
_HEADER_RE = re.compile(
    r"Exporting (?:edited version of )?(.+?) \((.+?)\)(?:\s+\(\d+/\d+\))?\s*$"
)

# "Skipping missing ... photo [for] FILENAME (UUID)"
_MISSING_RE = re.compile(r"Skipping missing .+? \(([^)]+)\)\s*$")


def parse_export_output(output: str) -> dict[str, dict]:
    """Parse verbose export output into a dict keyed on photo UUID.

    Returns a dict where each key is a UUID string and the value is::

        {
            "filename": str,      # original filename from the Exporting header
            "action": str,        # "exported" | "updated" | "skipped" | "missing"
            "files": list[str],   # absolute paths of exported/skipped files
        }

    Action priority when an asset has mixed per-file outcomes:
    exported > updated > missing > skipped
    """
    lines = output.splitlines()

    # Split output into per-asset blocks delimited by "Exporting ..." headers.
    # Each block is (uuid | None, original_filename, [lines]).
    blocks: list[tuple[str | None, str, list[str]]] = []
    cur_uuid: str | None = None
    cur_filename: str = ""
    cur_lines: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        m = _HEADER_RE.match(line)
        if m:
            filename = m.group(1)
            uuid_info = m.group(2)
            uuid_match = _UUID_PATTERN.search(uuid_info)
            uuid = uuid_match.group(0) if uuid_match else None

            # "Exporting edited version of ..." is a continuation of the same
            # asset; keep appending to the current block.
            if "edited version of" in line and uuid and uuid == cur_uuid:
                continue

            # Save previous block and start a new one.
            if cur_lines:
                blocks.append((cur_uuid, cur_filename, cur_lines))
            cur_uuid = uuid
            cur_filename = filename
            cur_lines = []
            continue

        # If the header didn't contain a UUID (e.g. "Pumpkins4.jpg"),
        # try to pick it up from a "Skipping missing" line.
        if cur_uuid is None:
            mm = _MISSING_RE.match(line)
            if mm:
                uuid_match = _UUID_PATTERN.search(mm.group(1))
                if uuid_match:
                    cur_uuid = uuid_match.group(0)

        cur_lines.append(line)

    # Save final block.
    if cur_lines:
        blocks.append((cur_uuid, cur_filename, cur_lines))

    # Process each block: extract actions and file paths.
    result: dict[str, dict] = {}

    for uuid, filename, block_lines in blocks:
        if not uuid:
            continue

        actions: set[str] = set()
        files: list[str] = []

        for line in block_lines:
            # --- action + optional path patterns (most specific first) ---

            if line.startswith("Exported new file"):
                actions.add("exported")
                rest = line[len("Exported new file") :].strip()
                if rest.startswith("/"):
                    files.append(rest)
                continue

            if line.startswith("Exported updated file"):
                actions.add("updated")
                rest = line[len("Exported updated file") :].strip()
                if rest.startswith("/"):
                    files.append(rest)
                continue

            if line.startswith("Skipped up to date file"):
                actions.add("skipped")
                rest = line[len("Skipped up to date file") :].strip()
                if rest.startswith("/"):
                    files.append(rest)
                continue

            if line.startswith("Skipping missing"):
                actions.add("missing")
                continue

            # "Exported /path" — non-update mode result from CLI
            if line.startswith("Exported /"):
                actions.add("exported")
                files.append(line[len("Exported ") :])
                continue

            # "Exported FILENAME to /path" — verbose message from _export_photo
            if line.startswith("Exported "):
                to_match = re.search(r" to (/.+)$", line)
                if to_match:
                    files.append(to_match.group(1))
                continue

            # Bare path line (continuation from line-wrapped output)
            if line.startswith("/"):
                files.append(line)
                continue

        # Determine primary action by priority.
        if "exported" in actions:
            action = "exported"
        elif "updated" in actions:
            action = "updated"
        elif "missing" in actions:
            action = "missing"
        elif "skipped" in actions:
            action = "skipped"
        else:
            action = "exported"

        # Deduplicate paths preserving order.
        seen: set[str] = set()
        unique_files: list[str] = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        # Merge with existing entry for the same UUID
        # (e.g. original + edited version of the same photo).
        if uuid in result:
            existing = result[uuid]
            existing_set = set(existing["files"])
            for f in unique_files:
                if f not in existing_set:
                    existing_set.add(f)
                    existing["files"].append(f)
            both = {existing["action"], action}
            if "exported" in both:
                existing["action"] = "exported"
            elif "updated" in both:
                existing["action"] = "updated"
            elif "missing" in both:
                existing["action"] = "missing"
        else:
            result[uuid] = {
                "filename": filename,
                "action": action,
                "files": unique_files,
            }

    return result
