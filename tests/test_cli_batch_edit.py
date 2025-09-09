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


TEST_UUID = "F12384F6-CD17-4151-ACBA-AE0E3688539E"
TEST_UUID_IN_ALBUM = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"
TEST_DATA_BATCH_EDIT = {
    "uuid": TEST_UUID,  # Pumkins1.jpg,
    "data": [
        (
            [
                "--title",
                "Pumpkin Farm {created.year}-{created.mm}-{created.dd}",
                "--uuid",
                TEST_UUID,
            ],
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
                "--uuid",
                TEST_UUID,
            ],
            {
                "description": "Pumpkin Farm 2018",
                "keywords": sorted(["kids", "holiday"]),
            },
        ),
        (
            ["--location", "34.052235", "-118.243683", "--uuid", TEST_UUID],
            {"location": (34.052235, -118.243683)},
        ),
    ],
}


# def say(msg: str) -> None:
#     """Say message with text to speech"""
#     os.system(f"say {msg}")


# def ask_user_to_make_selection(
#     photoslib: photoscript.PhotosLibrary, suspend_capture, msg: str
# ) -> list[photoscript.Photo]:
#     """Ask user to make selection in Photos and press enter when done"""
#     with suspend_capture:
#         photoslib.activate()
#         say(f"Select the photo of the {msg} in Photos and press enter when done")
#         input("Press enter when done")
#         return photoslib.selection


@pytest.fixture
def test_photo():
    return photoscript.Photo(uuid=TEST_UUID)


@pytest.mark.test_batch_edit
def test_setup_photo(test_photo, suspend_capture):
    """Setup photo for test of batch-edit command"""

    # initialize the photo's metadata
    test_photo.title = None
    test_photo.description = None
    test_photo.keywords = None
    test_photo.location = None


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
def test_batch_edit_undo(test_photo):
    """Test batch-edit command with --undo"""
    assert test_photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]
    test_photo.title = "Pumpkin Farm"
    test_photo.description = "Pumpkin Farm"
    test_photo.keywords = ["kids"]
    test_photo.location = (41.256566, -95.940257)

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
                "--uuid",
                TEST_UUID,
            ],
        )
        assert result.exit_code == 0
        test_photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert test_photo.title == "Test"
        assert test_photo.description == "Test"
        assert test_photo.keywords == ["test"]
        assert test_photo.location == (34.052235, -118.243683)

        result = CliRunner().invoke(
            batch_edit,
            ["--undo", "--dry-run", "--uuid", TEST_UUID],
        )
        assert result.exit_code == 0
        test_photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert test_photo.title == "Test"
        assert test_photo.description == "Test"
        assert test_photo.keywords == ["test"]
        assert test_photo.location == (34.052235, -118.243683)

        result = CliRunner().invoke(
            batch_edit,
            ["--undo", "--uuid", TEST_UUID],
        )
        assert result.exit_code == 0
        test_photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert test_photo.title == "Pumpkin Farm"
        assert test_photo.description == "Pumpkin Farm"
        assert test_photo.keywords == ["kids"]
        assert test_photo.location == (41.256566, -95.940257)


@pytest.mark.test_batch_edit
def test_batch_edit_replace_keywords(test_photo):
    """Test batch-edit command with --replace-keywords"""
    assert test_photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]
    test_photo.title = "Pumpkin Farm"
    test_photo.description = "Pumpkin Farm"
    test_photo.keywords = ["kids"]

    with CliRunner().isolated_filesystem():
        # First test that omitting --replace-keywords adds keywords
        result = CliRunner().invoke(
            batch_edit,
            [
                "--keyword",
                "test",
                "--uuid",
                TEST_UUID,
            ],
        )
        assert result.exit_code == 0
        test_photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert sorted(test_photo.keywords) == ["kids", "test"]

        result = CliRunner().invoke(
            batch_edit,
            [
                "--keyword",
                "test2",
                "--replace-keywords",
                "--uuid",
                TEST_UUID,
            ],
        )
        assert result.exit_code == 0
        test_photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert test_photo.keywords == ["test2"]


@pytest.mark.test_batch_edit
def test_batch_edit_replace_keywords_error():
    """Test batch-edit command with --replace-keywords when no keywords specified"""

    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            [
                "--title",
                "test",
                "--replace-keywords",
                "--uuid",
                TEST_UUID,
            ],
        )
        assert result.exit_code != 0


@pytest.mark.test_batch_edit
def test_batch_edit_set_clear_favorite(test_photo):
    """Test batch-edit command with --set-favorite option"""
    assert test_photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]
    test_photo.favorite = False

    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            ["--set-favorite", "--uuid", TEST_UUID],
        )
        assert result.exit_code == 0
        test_photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert test_photo.favorite

        result = CliRunner().invoke(
            batch_edit,
            ["--clear-favorite", "--uuid", TEST_UUID],
        )
        assert result.exit_code == 0
        test_photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert not test_photo.favorite


@pytest.mark.test_batch_edit
def test_batch_edit_add_to_album(test_photo):
    """Test batch-edit with --add-to-album"""
    assert test_photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]

    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            [
                "--add-to-album",
                "Folder/Subfolder/{keyword}",
                "--split-folder",
                "/",
                "--uuid",
                TEST_UUID,
            ],
        )
        assert result.exit_code == 0

        test_photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        album_paths = []
        for album in test_photo.album_info:
            folders = album.folder_names
            if folders:
                album_paths.append("/".join(folders) + "/" + album.title)
            else:
                album_paths.append(album.title)

        for keyword in test_photo.keywords:
            assert f"Folder/Subfolder/{keyword}" in album_paths


@pytest.mark.test_batch_edit
def test_batch_edit_uuid_from_file(test_photo):
    """Test batch-edit with --uuid-from-file"""
    assert test_photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]
    test_photo.favorite = False
    test_photo.keywords = []

    with CliRunner().isolated_filesystem():
        with open("uuids.txt", "w") as f:
            f.write("#uuid\n")
            f.write(TEST_UUID)
        result = CliRunner().invoke(
            batch_edit,
            [
                "--keyword",
                "test",
                "--set-favorite",
                "--uuid-from-file",
                "uuids.txt",
            ],
        )
        assert result.exit_code == 0
        test_photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert test_photo.favorite
        assert test_photo.keywords == ["test"]


@pytest.mark.test_batch_edit
def test_batch_edit_error_if_no_photos(photoslib):
    """Test batch-edit command with no photos to process"""
    # fail if user has photos selected
    assert not photoslib.selection

    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            [
                "--keyword",
                "test",
            ],
        )
        assert result.exit_code != 0


@pytest.mark.test_batch_edit
def test_batch_edit_album_filter(test_photo):
    """Test batch-edit command with --album"""

    assert test_photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]
    test_photo.title = "Pumpkin Farm"
    test_photo.description = "Pumpkin Farm"
    test_photo.keywords = ["kids"]

    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            ["--title", "test", "--album", "Folder/Subfolder/test2"],
        )
        assert result.exit_code == 0
        test_photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert test_photo.title == "test"


@pytest.mark.test_batch_edit
def test_batch_edit_album_filter_no_match(test_photo):
    """Test batch-edit command with --album but no matching album"""

    assert test_photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]
    test_photo.title = "Pumpkin Farm"
    test_photo.description = "Pumpkin Farm"
    test_photo.keywords = ["kids"]

    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            ["--title", "test", "--album", "Folder/Subfolder/IDontExist", "--verbose"],
        )
        assert result.exit_code != 0
        assert "No photos found to process" in result.stderr


@pytest.mark.test_batch_edit
def test_batch_edit_album_filter_ignore_case(test_photo):
    """Test batch-edit command with --album with --ignore-case"""

    assert test_photo.uuid == TEST_DATA_BATCH_EDIT["uuid"]
    test_photo.title = "Pumpkin Farm"
    test_photo.description = "Pumpkin Farm"
    test_photo.keywords = ["kids"]

    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            ["--title", "test", "--album", "FOLDER/Subfolder/Test2", "--ignore-case"],
        )
        assert result.exit_code == 0
        test_photo = osxphotos.PhotosDB().get_photo(TEST_DATA_BATCH_EDIT["uuid"])
        assert test_photo.title == "test"


@pytest.mark.test_batch_edit
def test_batch_edit_album_filter_uuid(test_photo):
    """Test batch-edit command with --album and --uuid"""

    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            [
                "--title",
                "test",
                "--album",
                "Folder1/SubFolder2/AlbumInFolder",
                "--uuid",
                TEST_UUID_IN_ALBUM,
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Processing 1 photo" in result.output


@pytest.mark.test_batch_edit
def test_batch_edit_year(test_photo):
    """Test batch-edit command with --year"""

    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            batch_edit,
            [
                "--title",
                "test",
                "--year",
                "2019",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Processing 2 photos" in result.output
