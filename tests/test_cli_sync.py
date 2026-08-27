"""Test osxphotos sync command"""

import csv
import importlib
import json
import os
import sqlite3
import time

import pytest
from click.testing import CliRunner

import osxphotos
from osxphotos.platform import is_macos

if is_macos:
    import photoscript

    from osxphotos.cli.sync import sync
    from osxphotos.cli.sync_results import SyncResults
    from osxphotos.sqlitekvstore import SQLiteKVStore
else:
    pytest.skip(allow_module_level=True)

UUID_TEST_PHOTO_1 = "D79B8D77-BFFC-460B-9312-034F2877D35B"  # Pumkins2.jpg
UUID_TEST_PHOTO_2 = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"  # wedding.jpg

TEST_ALBUM_NAME = "SyncTestAlbum"

UUID_TEST_PHOTO_3 = "D1D4040D-D141-44E8-93EA-E403D9F63E07"  # Frítest.jpg, No Location
UUID_TEST_PHOTO_4 = "D1359D09-1373-4F3B-B0E3-1A4DE573E4A3"  # Jellyfish1.mp4, Location
UUID_TEST_PHOTO_5 = "7783E8E6-9CAC-40F3-BE22-81FB7051C266"  # IMG_3092.heic, Location

TEST_PHOTO_3_SIGNATURE = "frítest.jpg:AUxIqfurFEEy1m1SphGJRmxID+1g"

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

        # verify data written correctly
        conn = sqlite3.Connection("test_location.db")
        result = conn.execute(
            "SELECT value FROM data WHERE key == ?", (TEST_PHOTO_3_SIGNATURE,)
        ).fetchone()
        data = json.loads(result[0])
        assert data["favorite"]

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
            while photo.favorite:
                photo.favorite = False
                time.sleep(0.25)
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


###############################################################################
# Tests for import_metadata() signature matching
#
# These don't require a Photos library so they run without --test-sync
###############################################################################


def _sync_module():
    """Return the osxphotos.cli.sync module.

    Note: importlib is needed because osxphotos.cli.sync resolves to the sync
    click command, not the module.
    """
    return importlib.import_module("osxphotos.cli.sync")


class SyncTestPhoto:
    """Minimal stand-in for PhotoInfo for testing import_metadata() matching"""

    def __init__(
        self,
        uuid: str,
        original_filename: str,
        fingerprint: str,
        shared: bool = False,
    ):
        self.uuid = uuid
        self.original_filename = original_filename
        self.fingerprint = fingerprint
        self.shared = shared


def _test_photo_signature(photo: SyncTestPhoto) -> str:
    """Stand-in for photo_signature() that mirrors the real signature format"""
    if photo.shared:
        # shared photo signatures contain no filename
        return f"OWNER:100:200:True:False:{photo.uuid}"
    return f"{photo.original_filename.lower()}:{photo.fingerprint}"


def _make_import_db(tmp_path, entries: dict[str, dict]) -> str:
    """Create a sync metadata export database containing entries; return its path"""
    db_path = str(tmp_path / "metadata.db")
    db = SQLiteKVStore(db_path, wal=False)
    db.about = "osxphotos metadata sync database (test)"
    for key, metadata in entries.items():
        db[key] = json.dumps(metadata)
    db.close()
    return db_path


@pytest.fixture
def sync_test_env(monkeypatch):
    """Patch the sync module so import_metadata() can run without a Photos library.

    Returns (sync module, list of (photo, metadata) passed to
    import_metadata_for_photo, list of messages passed to echo).
    """
    sync_module = _sync_module()
    imported = []
    messages = []

    def fake_import_metadata_for_photo(photo, metadata, set_, merge, dry_run, verbose):
        imported.append((photo, json.loads(metadata)))
        return SyncResults()

    monkeypatch.setattr(sync_module, "photo_signature", _test_photo_signature)
    monkeypatch.setattr(
        sync_module, "import_metadata_for_photo", fake_import_metadata_for_photo
    )
    monkeypatch.setattr(sync_module, "echo", lambda msg, **kwargs: messages.append(msg))
    return sync_module, imported, messages


def _import_metadata(sync_module, photos, import_path, unmatched=False):
    """Call import_metadata() with the options used by these tests"""
    return sync_module.import_metadata(
        photos=photos,
        import_path=import_path,
        set_=("keywords",),
        merge=(),
        dry_run=True,
        unmatched=unmatched,
        verbose=lambda *args, **kwargs: None,
    )


def test_import_metadata_matches_exact_signature(sync_test_env, tmp_path):
    """Photo whose signature is in the import database is matched"""
    sync_module, imported, _ = sync_test_env
    import_path = _make_import_db(
        tmp_path, {"img_1234.heic:FINGERPRINT1": {"keywords": ["Travel"]}}
    )
    photo = SyncTestPhoto("UUID1", "IMG_1234.HEIC", "FINGERPRINT1")

    _import_metadata(sync_module, [photo], import_path)

    assert len(imported) == 1
    assert imported[0][0] is photo
    assert imported[0][1] == {"keywords": ["Travel"]}


def test_import_metadata_matches_filename_with_collision_counter(
    sync_test_env, tmp_path
):
    """Photo renamed by Photos with a collision counter falls back to the base filename"""
    sync_module, imported, _ = sync_test_env
    import_path = _make_import_db(
        tmp_path, {"img_1234.heic:FINGERPRINT1": {"keywords": ["Travel"]}}
    )
    # same photo, imported into a library where the filename collided
    photo = SyncTestPhoto("UUID1", "IMG_1234 2.HEIC", "FINGERPRINT1")

    _import_metadata(sync_module, [photo], import_path)

    assert len(imported) == 1
    assert imported[0][0] is photo
    assert imported[0][1] == {"keywords": ["Travel"]}


def test_import_metadata_unmatched_photo_is_skipped(sync_test_env, tmp_path):
    """Photo with no match in the import database is skipped, not an error"""
    sync_module, imported, _ = sync_test_env
    import_path = _make_import_db(
        tmp_path, {"img_1234.heic:FINGERPRINT1": {"keywords": ["Travel"]}}
    )
    photo = SyncTestPhoto("UUID2", "IMG_9999.JPG", "FINGERPRINT2")

    _import_metadata(sync_module, [photo], import_path)

    assert not imported


def test_import_metadata_unmatched_photo_with_different_fingerprint_is_skipped(
    sync_test_env, tmp_path
):
    """Photo whose filename matches after normalization but fingerprint doesn't is skipped"""
    sync_module, imported, _ = sync_test_env
    import_path = _make_import_db(
        tmp_path, {"img_1234.heic:FINGERPRINT1": {"keywords": ["Travel"]}}
    )
    photo = SyncTestPhoto("UUID2", "IMG_1234 2.HEIC", "DIFFERENT_FINGERPRINT")

    _import_metadata(sync_module, [photo], import_path)

    assert not imported


def test_import_metadata_unmatched_photo_reported_with_unmatched(
    sync_test_env, tmp_path
):
    """--unmatched reports photos with no metadata in the import database"""
    sync_module, imported, messages = sync_test_env
    import_path = _make_import_db(
        tmp_path, {"img_1234.heic:FINGERPRINT1": {"keywords": ["Travel"]}}
    )
    photo = SyncTestPhoto("UUID2", "IMG_9999.JPG", "FINGERPRINT2")

    _import_metadata(sync_module, [photo], import_path, unmatched=True)

    assert not imported
    assert any("IMG_9999.JPG" in msg and "UUID2" in msg for msg in messages)
    assert any("img_1234.heic:FINGERPRINT1" in msg for msg in messages)


def test_import_metadata_shared_photo_signature_not_normalized(sync_test_env, tmp_path):
    """Shared photo signatures contain no filename so must not be normalized"""
    sync_module, imported, _ = sync_test_env
    shared_signature = "OWNER:100:200:True:False:UUID3"
    import_path = _make_import_db(
        tmp_path, {shared_signature: {"keywords": ["Shared"]}}
    )
    photo = SyncTestPhoto("UUID3", "IMG_1234 2.HEIC", "FINGERPRINT3", shared=True)

    _import_metadata(sync_module, [photo], import_path)

    assert len(imported) == 1
    assert imported[0][1] == {"keywords": ["Shared"]}


def test_import_metadata_multiple_photos_share_normalized_key(sync_test_env, tmp_path):
    """More than one photo may match the same import key"""
    sync_module, imported, _ = sync_test_env
    import_path = _make_import_db(
        tmp_path, {"img_1234.heic:FINGERPRINT1": {"keywords": ["Travel"]}}
    )
    photos = [
        SyncTestPhoto("UUID1", "IMG_1234.HEIC", "FINGERPRINT1"),
        SyncTestPhoto("UUID2", "IMG_1234 2.HEIC", "FINGERPRINT1"),
    ]

    _import_metadata(sync_module, photos, import_path)

    assert sorted(photo.uuid for photo, _ in imported) == ["UUID1", "UUID2"]


def test_import_metadata_library_import_updates_selected_photos(
    sync_test_env, monkeypatch, tmp_path
):
    """--import <library> must update the selected photos, not the import library's photos"""
    sync_module, imported, _ = sync_test_env
    import_photo = SyncTestPhoto("IMPORT-UUID", "IMG_1234.HEIC", "FINGERPRINT1")
    selected_photo = SyncTestPhoto("SELECTED-UUID", "IMG_1234.HEIC", "FINGERPRINT1")

    class FakePhotosDB:
        def __init__(self, *args, **kwargs):
            pass

        def query(self, options):
            return [import_photo]

    def fake_export_metadata_to_db(photos, metadata_db, progress=True):
        for photo in photos:
            metadata_db[_test_photo_signature(photo)] = json.dumps(
                {"uuid": photo.uuid, "keywords": ["Travel"]}
            )

    monkeypatch.setattr(sync_module, "get_import_type", lambda path: "library")
    monkeypatch.setattr(sync_module, "PhotosDB", FakePhotosDB)
    monkeypatch.setattr(
        sync_module, "export_metadata_to_db", fake_export_metadata_to_db
    )

    _import_metadata(sync_module, [selected_photo], str(tmp_path))

    assert len(imported) == 1
    assert imported[0][0] is selected_photo
    assert imported[0][1]["uuid"] == "IMPORT-UUID"
