"""Test osxphotos sync command"""

import json
import os

import pytest
from click.testing import CliRunner

from osxphotos.platform import is_macos

if is_macos:
    import photoscript

    from osxphotos.cli.sync import sync
else:
    pytest.skip(allow_module_level=True)

UUID_TEST_PHOTO_1 = "D79B8D77-BFFC-460B-9312-034F2877D35B"  # Pumkins2.jpg
UUID_TEST_PHOTO_2 = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"  # wedding.jpg

TEST_ALBUM_NAME = "SyncTestAlbum"


@pytest.mark.test_sync
def test_sync_export():
    """Test --export"""
    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            sync,
            [
                "--export",
                "test.db",
            ],
        )
        assert result.exit_code == 0
        assert os.path.exists("test.db")


@pytest.mark.test_sync
def test_sync_export_import():
    """Test --export and --import"""

    photoslib = photoscript.PhotosLibrary()

    # create a new album and initialize metadata
    test_album = photoslib.create_album(TEST_ALBUM_NAME)
    for uuid in [UUID_TEST_PHOTO_1, UUID_TEST_PHOTO_2]:
        photo = photoscript.Photo(uuid)
        photo.favorite = True
        test_album.add([photo])

    # export data
    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            sync,
            [
                "--export",
                "test.db",
            ],
        )
        assert result.exit_code == 0

        # preserve metadata for comparison and clear metadata
        metadata_before = {}
        for uuid in [UUID_TEST_PHOTO_1, UUID_TEST_PHOTO_2]:
            photo = photoscript.Photo(uuid)
            metadata_before[uuid] = {
                "title": photo.title,
                "description": photo.description,
                "keywords": photo.keywords,
                "favorites": photo.favorite,
            }
            photo.title = ""
            photo.description = ""
            photo.keywords = ["NewKeyword"]
            photo.favorite = False

        # delete the test album
        photoslib.delete_album(test_album)

        # import metadata
        result = CliRunner().invoke(
            sync,
            [
                "--import",
                "test.db",
                "--set",
                "title,description,favorite,albums",
                "--merge",
                "keywords",
                "--report",
                "test_report.json",
            ],
        )
        assert result.exit_code == 0
        assert os.path.exists("test_report.json")

        # check metadata
        for uuid in [UUID_TEST_PHOTO_1, UUID_TEST_PHOTO_2]:
            photo = photoscript.Photo(uuid)
            assert photo.title == metadata_before[uuid]["title"]
            assert photo.description == metadata_before[uuid]["description"]
            assert sorted(photo.keywords) == sorted(
                ["NewKeyword", *metadata_before[uuid]["keywords"]]
            )
            assert photo.favorite == metadata_before[uuid]["favorites"]
            assert TEST_ALBUM_NAME in [album.title for album in photo.albums]

        # check report
        with open("test_report.json", "r") as f:
            report = json.load(f)
        report_data = {record["uuid"]: record for record in report}
        for uuid in [UUID_TEST_PHOTO_1, UUID_TEST_PHOTO_2]:
            assert report_data[uuid]["updated"]
            assert report_data[uuid]["albums"]["updated"]
