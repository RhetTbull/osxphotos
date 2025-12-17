"""Test osxphotos sync command"""

import csv
import json
import os
import time

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

UUID_TEST_PHOTO_3 = "D1D4040D-D141-44E8-93EA-E403D9F63E07"  # Frítest.jpg, No Location
UUID_TEST_PHOTO_4 = "D1359D09-1373-4F3B-B0E3-1A4DE573E4A3"  # Jellyfish1.mp4, Location
UUID_TEST_PHOTO_5 = "7783E8E6-9CAC-40F3-BE22-81FB7051C266"  # IMG_3092.heic, Location

TEST_ALBUM_NAME_LOCATION = "SyncTestAlbumLocation"

TEST_FOLDER_NAME_LOCATION = "SyncTestFolderLocation"


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
            assert not report_data[uuid]["error"]


@pytest.mark.test_sync
def test_sync_export_import_csv():
    """Test --export and --import with CSV report"""

    photoslib = photoscript.PhotosLibrary()

    # create a new album and initialize metadata
    test_album = photoslib.create_album(TEST_ALBUM_NAME)
    for uuid in [UUID_TEST_PHOTO_1, UUID_TEST_PHOTO_2]:
        photo = photoscript.Photo(uuid)
        photo.favorite = True
        photo.keywords = [k for k in photo.keywords if k != "NewKeyword"]
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
                "test_report.csv",
                "--append",
            ],
        )
        assert result.exit_code == 0
        assert os.path.exists("test_report.csv")

        # check report
        with open("test_report.csv", "r") as f:
            report_data = csv.DictReader(f)
            for row in report_data:
                if row["uuid"] == UUID_TEST_PHOTO_1:
                    assert (
                        row["keywords_after"]
                        == f'{sorted(["NewKeyword", *metadata_before[UUID_TEST_PHOTO_1]["keywords"]])}'
                    )


@pytest.mark.test_sync
def test_sync_export_import_location():
    """Test --export and --import location"""

    photoslib = photoscript.PhotosLibrary()

    # create a new album and initialize metadata
    test_album = photoslib.create_album(TEST_ALBUM_NAME_LOCATION)
    for uuid in [UUID_TEST_PHOTO_3]:
        photo = photoscript.Photo(uuid)
        # For unknown reasons, the favorite status doesn't always update when under test, #1972
        while not photo.favorite:
            photo.favorite = True
            time.sleep(0.250)
        test_album.add([photo])

    # export data
    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            sync,
            [
                "--export",
                "test_location.db",
            ],
        )
        assert result.exit_code == 0

        # preserve metadata for comparison and clear/set metadata
        metadata_before = {}
        for uuid in [UUID_TEST_PHOTO_3]:
            photo = photoscript.Photo(uuid)
            metadata_before[uuid] = {
                "title": photo.title,
                "description": photo.description,
                "keywords": photo.keywords,
                "favorites": photo.favorite,
                "location": photo.location,
            }
            photo.title = ""
            photo.description = ""
            photo.keywords = ["NewKeyword"]
            photo.favorite = False
            photo.location = (24.681666439037876, 32.88630618597232)

        # delete the test album
        photoslib.delete_album(test_album)

        # import metadata
        result = CliRunner().invoke(
            sync,
            [
                "--import",
                "test_location.db",
                "--set",
                "title,description,favorite,albums,location",
                "--merge",
                "keywords",
                "--report",
                "test_report_location.json",
            ],
        )
        assert result.exit_code == 0
        assert os.path.exists("test_report_location.json")

        # check metadata
        for uuid in [UUID_TEST_PHOTO_3]:
            photo = photoscript.Photo(uuid)
            assert photo.title == metadata_before[uuid]["title"]
            assert photo.description == metadata_before[uuid]["description"]
            assert sorted(photo.keywords) == sorted(
                ["NewKeyword", *metadata_before[uuid]["keywords"]]
            )
            assert photo.favorite == metadata_before[uuid]["favorites"]
            assert photo.location == metadata_before[uuid]["location"]
            assert TEST_ALBUM_NAME_LOCATION in [album.title for album in photo.albums]

        # check report
        with open("test_report_location.json", "r") as f:
            report = json.load(f)
        report_data = {record["uuid"]: record for record in report}
        for uuid in [UUID_TEST_PHOTO_3]:
            assert report_data[uuid]["updated"]
            assert report_data[uuid]["albums"]["updated"]
            assert report_data[uuid]["location"]["updated"]
            assert not report_data[uuid]["error"]


@pytest.mark.test_sync
def test_sync_export_import_location_in_folder():
    """Test --export and --import location"""

    photoslib = photoscript.PhotosLibrary()

    # create a new album under a folder and initialize metadata
    test_folder = photoslib.create_folder(TEST_FOLDER_NAME_LOCATION)
    test_album_folder = photoslib.create_album(TEST_ALBUM_NAME_LOCATION, test_folder)
    for uuid in [UUID_TEST_PHOTO_4, UUID_TEST_PHOTO_5]:
        photo = photoscript.Photo(uuid)
        photo.favorite = True
        test_album_folder.add([photo])

    # export data
    with CliRunner().isolated_filesystem():
        result = CliRunner().invoke(
            sync,
            [
                "--export",
                "test_location_folder.db",
            ],
        )
        assert result.exit_code == 0

        # preserve metadata for comparison and clear/set metadata
        metadata_before = {}
        for uuid in [UUID_TEST_PHOTO_4, UUID_TEST_PHOTO_5]:
            photo = photoscript.Photo(uuid)
            metadata_before[uuid] = {
                "title": photo.title,
                "description": photo.description,
                "keywords": photo.keywords,
                "favorites": photo.favorite,
                "location": photo.location,
                "albums": sorted(a.path_str() for a in photo.albums),
            }
            photo.title = ""
            photo.description = ""
            photo.keywords = ["OnFolder_and_Album_Keyword"]
            photo.favorite = False
            photo.location = (24.681666439037876, 32.88630618597232)

        # delete the test album and folder
        photoslib.delete_album(test_album_folder)
        photoslib.delete_folder(test_folder)

        # import metadata
        result = CliRunner().invoke(
            sync,
            [
                "--import",
                "test_location_folder.db",
                "--set",
                "title,description,favorite,albums,location",
                "--merge",
                "keywords",
                "--report",
                "test_report_location_folder.json",
            ],
        )
        assert result.exit_code == 0
        assert os.path.exists("test_report_location_folder.json")

        # check metadata
        for uuid in [UUID_TEST_PHOTO_4, UUID_TEST_PHOTO_5]:
            photo = photoscript.Photo(uuid)
            assert photo.title == metadata_before[uuid]["title"]
            assert photo.description == metadata_before[uuid]["description"]
            assert sorted(photo.keywords) == sorted(
                ["OnFolder_and_Album_Keyword", *metadata_before[uuid]["keywords"]]
            )
            assert photo.favorite == metadata_before[uuid]["favorites"]
            assert photo.location == metadata_before[uuid]["location"]
            assert TEST_ALBUM_NAME_LOCATION in [album.title for album in photo.albums]
            assert "/".join([TEST_FOLDER_NAME_LOCATION, TEST_ALBUM_NAME_LOCATION]) in [
                album.path_str() for album in photo.albums
            ]
            assert metadata_before[uuid]["albums"] == sorted(
                a.path_str() for a in photo.albums
            )

        # check report
        with open("test_report_location_folder.json", "r") as f:
            report = json.load(f)
        report_data = {record["uuid"]: record for record in report}
        for uuid in [UUID_TEST_PHOTO_4, UUID_TEST_PHOTO_5]:
            assert report_data[uuid]["updated"]
            assert report_data[uuid]["albums"]["updated"]
            assert report_data[uuid]["location"]["updated"]
            assert not report_data[uuid]["error"]
