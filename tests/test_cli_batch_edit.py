"""Test osxphotos batch-edit command"""

from __future__ import annotations

import os
import time

import pytest
from click.testing import CliRunner

import osxphotos
from osxphotos.platform import is_macos

if is_macos:
    import photoscript

    from osxphotos.cli.batch_edit import batch_edit
else:
    pytest.skip(allow_module_level=True)


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


TEST_DATA_BATCH_EDIT = {
    "uuid": "F12384F6-CD17-4151-ACBA-AE0E3688539E",  # Pumkins1.jpg,
    "data": [
        (
            ["--title", "Pumpkin Farm {created.year}-{created.mm}-{created.dd}"],
            {"title": "Pumpkin Farm 2018-09-28"},
        ),
        (
            [
                "--description",
                "Pumpkin Farm {created.year}",
                "--keyword",
                "kids",
                "--keyword",
                "holiday",
            ],
            {
                "description": "Pumpkin Farm 2018",
                "keywords": sorted(["kids", "holiday"]),
            },
        ),
        (
            ["--location", "34.052235", "-118.243683"],
            {"location": (34.052235, -118.243683)},
        ),
    ],
}


def say(msg: str) -> None:
    """Say message with text to speech"""
    os.system(f"say {msg}")


def ask_user_to_make_selection(
    photoslib: photoscript.PhotosLibrary, suspend_capture, msg: str
) -> list[photoscript.Photo]:
    """Ask user to make selection in Photos and press enter when done"""
    with suspend_capture:
        photoslib.activate()
        say(f"Select the photo of the {msg} in Photos and press enter when done")
        input("Press enter when done")
        return photoslib.selection


@pytest.mark.test_batch_edit
def test_select_photo(photoslib, suspend_capture):
    """Test batch-edit command"""
    photos = ask_user_to_make_selection(
        photoslib, suspend_capture, "children lifting the pumpkins"
    )
    assert len(photos) == 1
    photo = photos[0]
    assert photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]

    # initialize the photo's metadata
    photo.title = None
    photo.description = None
    photo.keywords = None
    photo.location = None


@pytest.mark.test_batch_edit
@pytest.mark.parametrize("args,expected", TEST_DATA_BATCH_EDIT["data"])
def test_batch_edit(args, expected):
    """Test batch-edit command"""
    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            [*args, "--dry-run"],
        )
        assert result.exit_code == 0

        photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        for key, expected_value in expected.items():
            got = getattr(photo, key)
            if isinstance(got, list):
                got = sorted(got)
            assert got != expected_value

        result = CliRunner().invoke(
            batch_edit,
            [*args],
        )
        assert result.exit_code == 0

        photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        for key, expected_value in expected.items():
            got = getattr(photo, key)
            if isinstance(got, list):
                got = sorted(got)
            assert got == expected_value


@pytest.mark.test_batch_edit
def test_batch_edit_undo(photoslib):
    """Test batch-edit command with --undo"""
    photo = photoslib.selection[0]
    assert photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]
    photo.title = "Pumpkin Farm"
    photo.description = "Pumpkin Farm"
    photo.keywords = ["kids"]
    photo.location = (41.256566, -95.940257)

    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            [
                "--title",
                "Test",
                "--description",
                "Test",
                "--keyword",
                "test",
                "--replace-keywords",
                "--location",
                "34.052235",
                "-118.243683",
            ],
        )
        assert result.exit_code == 0
        photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert photo.title == "Test"
        assert photo.description == "Test"
        assert photo.keywords == ["test"]
        assert photo.location == (34.052235, -118.243683)

        result = CliRunner().invoke(
            batch_edit,
            ["--undo", "--dry-run"],
        )
        assert result.exit_code == 0
        photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert photo.title == "Test"
        assert photo.description == "Test"
        assert photo.keywords == ["test"]
        assert photo.location == (34.052235, -118.243683)

        result = CliRunner().invoke(
            batch_edit,
            ["--undo"],
        )
        assert result.exit_code == 0
        photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert photo.title == "Pumpkin Farm"
        assert photo.description == "Pumpkin Farm"
        assert photo.keywords == ["kids"]
        assert photo.location == (41.256566, -95.940257)


@pytest.mark.test_batch_edit
def test_batch_edit_replace_keywords(photoslib):
    """Test batch-edit command with --replace-keywords"""
    photo = photoslib.selection[0]
    assert photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]
    photo.title = "Pumpkin Farm"
    photo.description = "Pumpkin Farm"
    photo.keywords = ["kids"]

    with CliRunner().isolated_filesystem():
        # First test that omitting --replace-keywords adds keywords
        result = CliRunner().invoke(
            batch_edit,
            [
                "--keyword",
                "test",
            ],
        )
        assert result.exit_code == 0
        photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert sorted(photo.keywords) == ["kids", "test"]

        result = CliRunner().invoke(
            batch_edit,
            [
                "--keyword",
                "test2",
                "--replace-keywords",
            ],
        )
        assert result.exit_code == 0
        photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert photo.keywords == ["test2"]


@pytest.mark.test_batch_edit
def test_batch_edit_replace_keywords_error(photoslib):
    """Test batch-edit command with --replace-keywords when no keywords specified"""
    photo = photoslib.selection[0]
    assert photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]

    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            [
                "--title",
                "test",
                "--replace-keywords",
            ],
        )
        assert result.exit_code != 0
