"""Tests which require user interaction to run for osxphotos import command; run with pytest --test-import"""

import os
import os.path
import pathlib
import re
import shutil
import sqlite3
import sys
import time
from tempfile import TemporaryDirectory
from typing import Dict

import pytest
from click.testing import CliRunner

from osxphotos._constants import UUID_PATTERN
from osxphotos.exiftool import get_exiftool_path
from osxphotos.platform import is_macos

if is_macos:
    from photoscript import Photo

    from osxphotos.cli.import_cli import import_main
else:
    pytest.skip(allow_module_level=True)

TERMINAL_WIDTH = 250

TEST_IMAGES_DIR = "tests/test-images"
TAKEOUT_ARCHIVE = "tests/test-images/Takeout/Google Photos"


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


@pytest.fixture(autouse=True)
def xdg_patch(monkeypatch):
    """Patch XDG_CONFIG_HOME to point to temporary directory"""
    with TemporaryDirectory() as tmpdir:
        if sys.version_info[0:2] <= (3, 9):
            monkeypatch.setattr("xdg.xdg_data_home", lambda: pathlib.Path(tmpdir))
        else:
            monkeypatch.setattr(
                "xdg_base_dirs.xdg_data_home", lambda: pathlib.Path(tmpdir)
            )
        yield


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


@pytest.mark.test_import_takeout
def test_import_google_takeout(tmp_path):
    """Test import of a Google Takeout archive"""
    cwd = os.getcwd()
    test_takeout = os.path.join(cwd, TAKEOUT_ARCHIVE)

    runner = CliRunner(env={"TZ": "US/Pacific"})
    with runner.isolated_filesystem(tmp_path):
        result = runner.invoke(
            import_main,
            [
                test_takeout,
                "--walk",
                "--album",
                "{filepath.parent.name}",
                "--skip-dups",
                "--dup-albums",
                "--sidecar",
                "--keyword",
                "{person}",
                "--verbose",
                "--report",
                "takeout.db",
            ],
            terminal_width=TERMINAL_WIDTH,
        )
        assert result.exit_code == 0

        # spot check the report database to make sure it has the expected data
        conn = sqlite3.connect("takeout.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM report")
        assert c.fetchone()[0] == 31

        # test a photo that was imported
        row = c.execute(
            "SELECT * FROM report WHERE filepath LIKE '%Pumpkins3.jpg'"
        ).fetchall()
        assert len(row) == 2
        # check --skip-dups
        assert sorted([row[0]["imported"], row[1]["imported"]]) == [0, 1]
        assert sorted([row[0]["albums"], row[1]["albums"]]) == [
            "Photos from 2018",
            "Pumpkin Farm",
        ]

        row = c.execute(
            "SELECT * FROM report WHERE filepath LIKE '%wedding.jpg'"
        ).fetchone()

        assert row["description"] == "Bride Wedding day"
        assert row["title"] == "wedding.jpg"
        assert row["albums"] == "Photos from 2019"
        assert sorted(row["keywords"].split(",")) == ["Maria"]
        assert row["datetime"] == "2019-04-15T14:40:24"

        row = c.execute(
            "SELECT * FROM report WHERE filepath LIKE '%IMG_1760.jpg'"
        ).fetchone()
        lat, lon = [float(x) for x in row["location"].split(",")]
        assert lat == pytest.approx(18.9555889)
        assert lon == pytest.approx(-72.7274778)
