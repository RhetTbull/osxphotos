"""Tests that require access to the author's local library"""

import logging
import os
import os.path
import pathlib
import tempfile
import time

import pytest
from click.testing import CliRunner

import osxphotos
import osxphotos.exiftool
from osxphotos import PhotosDB
from osxphotos.cli import export
from osxphotos.platform import get_macos_version, is_macos

OS_VERSION = get_macos_version() if is_macos else (None, None, None)
SKIP_TEST_NOT_LOCAL = "OSXPHOTOS_TEST_LOCAL" not in os.environ
PHOTOS_DB_LOCAL = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")

# Note: when upgrading to a new macOS version these UUIDs may need to be updated
UUID_DICT_LOCAL = {
    "not_visible": "6D38B780-711D-42B6-91EF-468B4752CF73",  # IMG_9815.JPG
    "burst": "7BC2ABB0-7821-4A85-B573-AD52B31815B5",  # IMG_9812.JPG
    "burst_key": "7BC2ABB0-7821-4A85-B573-AD52B31815B5",  # IMG_9812.JPG
    "burst_not_key": "6D38B780-711D-42B6-91EF-468B4752CF73",  # IMG_9815.JPG
    "burst_selected": "8C85ECF2-DE8A-4556-8C76-4FBF9AACD808",  # IMG_9814.JPG
    "burst_not_selected": "1AFBB0EC-EFFA-4D38-B257-B040F4D61894",  # IMG_9813.JPG
    "burst_default": "80899C10-BCB3-4C3E-8839-2271764F2C06",  # IMG_9816.JPG
    "burst_not_default": "8C85ECF2-DE8A-4556-8C76-4FBF9AACD808",  # IMG_9814.JPG
    "not_burst": "ADDEC5FD-F3DC-418A-B358-717C748C34BC",  # IMG_1929.JPG
    "has_adjustments": "ADDEC5FD-F3DC-418A-B358-717C748C34BC",  # IMG_1929.JPG
    "no_adjustments": "ED9BCC94-C73C-416D-AA92-B6ABA8CDC6F0",  # IMG_9847.JPG
    "live": "50B35845-9C2B-45AF-A68F-83BE394A7FB1",  # IMG_3259.HEIC
}

UUID_SKIP_LIVE_PHOTOKIT = {
    "5220373D-9AD4-4EE6-84E0-CB21F6BE3EC4": ["IMG_3203_edited.jpeg"],
    "E22A7BCA-442D-46A6-B064-8E0345961EC8": ["IMG_4179.jpeg"],
}

UUID_BURSTS = {
    UUID_DICT_LOCAL["burst"]: {
        "selected": False,
        "filename": "IMG_9812.JPG",
        "burst_albums": ["TestBurst", "osxphotos"],
        "albums": ["TestBurst", "osxphotos"],
    },
    UUID_DICT_LOCAL["burst_not_selected"]: {
        "selected": False,
        "filename": "IMG_9813.JPG",
        "burst_albums": ["TestBurst", "osxphotos"],
        "albums": [],
    },
    UUID_DICT_LOCAL["burst_selected"]: {
        "selected": True,
        "filename": "IMG_9814.JPG",
        "burst_albums": ["TestBurst", "osxphotos"],
        "albums": ["osxphotos"],
    },
    UUID_DICT_LOCAL["not_visible"]: {
        "selected": False,
        "filename": "IMG_9815.JPG",
        "burst_albums": ["TestBurst", "osxphotos"],
        "albums": [],
    },
    UUID_DICT_LOCAL["burst_default"]: {
        "selected": True,
        "filename": "IMG_9816.JPG",
        "burst_albums": ["TestBurst", "osxphotos"],
        "albums": [],
    },
}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_LOCAL)


if SKIP_TEST_NOT_LOCAL:
    pytest.skip(
        allow_module_level=True, reason="Skip if not running on author's local machine."
    )


def test_not_visible_burst(photosdb):
    """test not visible and burst (needs image from local library)"""
    photo = photosdb.get_photo(UUID_DICT_LOCAL["not_visible"])
    assert not photo.visible
    assert photo.burst


def test_visible_burst(photosdb):
    """test not visible and burst (needs image from local library)"""
    photo = photosdb.get_photo(UUID_DICT_LOCAL["burst"])
    assert photo.visible
    assert photo.burst
    assert len(photo.burst_photos) == 4


def test_burst_key(photosdb):
    """test burst_key"""
    photo = photosdb.get_photo(UUID_DICT_LOCAL["burst_key"])
    assert photo.burst_key

    photo = photosdb.get_photo(UUID_DICT_LOCAL["burst_not_key"])
    assert not photo.burst_key


def test_burst_selected(photosdb):
    """test burst_selected"""
    photo = photosdb.get_photo(UUID_DICT_LOCAL["burst_selected"])
    assert photo.burst_selected

    photo = photosdb.get_photo(UUID_DICT_LOCAL["burst_not_selected"])
    assert not photo.burst_selected


def test_burst_default_pic(photosdb):
    """test burst_default_pick"""
    photo = photosdb.get_photo(UUID_DICT_LOCAL["burst_default"])
    assert photo.burst_default_pick

    photo = photosdb.get_photo(UUID_DICT_LOCAL["burst_not_default"])
    assert not photo.burst_default_pick


def test_burst_key_photo(photosdb: PhotosDB):
    """test burst template"""
    photo = photosdb.get_photo(UUID_DICT_LOCAL["burst_not_selected"])
    assert photo.burst_key_photo.uuid == UUID_DICT_LOCAL["burst_key"]


def test_burst_key_photo_not_burst(photosdb: PhotosDB):
    """test burst template"""
    photo = photosdb.get_photo(UUID_DICT_LOCAL["not_burst"])
    assert photo.burst_key_photo is None


def test_burst_template(photosdb: PhotosDB):
    """test burst template"""
    photo = photosdb.get_photo(UUID_DICT_LOCAL["burst_not_selected"])
    assert photo.render_template("{burst}") == (["IMG_9812"], [])


def test_burst_template_not_burst(photosdb: PhotosDB):
    """test burst template"""
    photo = photosdb.get_photo(UUID_DICT_LOCAL["not_burst"])
    assert not photo.burst
    assert photo.render_template("{burst}") == (["_"], [])


def test_export_default_name(photosdb):
    """test basic export"""
    # get an unedited image and export it using default filename
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT_LOCAL["no_adjustments"]])

    filename = photos[0].original_filename
    expected_dest = pathlib.Path(dest) / filename
    got_dest = photos[0].export(dest, use_photos_export=True)[0]

    assert got_dest == str(expected_dest)
    assert os.path.isfile(got_dest)


def test_export_supplied_name(photosdb):
    """test export with user provided filename"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT_LOCAL["no_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpeg"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename, use_photos_export=True)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_edited(photosdb):
    """test export edited file"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT_LOCAL["has_adjustments"]])

    suffix = pathlib.Path(photos[0].path_edited).suffix
    filename = f"{pathlib.Path(photos[0].original_filename).stem}_edited{suffix}"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, use_photos_export=True, edited=True)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(expected_dest)


def test_export_edited_exiftool(photosdb):
    """test export edited file"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT_LOCAL["has_adjustments"]])

    got_dest = photos[0].export(
        dest, use_photos_export=True, edited=True, exiftool=True
    )
    logging.warning(got_dest)
    got_dest = got_dest[0]

    assert os.path.isfile(got_dest)
    exif = osxphotos.exiftool.ExifTool(got_dest)
    assert exif.data["IPTC:Keywords"] == "osxphotos"


def test_export_edited_supplied_name(photosdb):
    """test export with user provided filename"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT_LOCAL["has_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpeg"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename, use_photos_export=True, edited=True)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_edited_no_edit(photosdb):
    """test export edited file if not actually edited"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT_LOCAL["no_adjustments"]])

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, use_photos_export=True, edited=True)
    assert e.type == ValueError


def test_burst_albums(photosdb):
    """Test burst_selected, burst_albums"""
    for uuid in UUID_BURSTS:
        photo = photosdb.get_photo(uuid)
        assert photo.burst
        assert photo.burst_selected == UUID_BURSTS[uuid]["selected"]
        assert sorted(photo.albums) == sorted(UUID_BURSTS[uuid]["albums"])
        assert sorted(photo.burst_albums) == sorted(UUID_BURSTS[uuid]["burst_albums"])


def test_export_skip_live_photokit():
    """test that --skip-live works with --use-photokit (issue #537)"""

    runner = CliRunner()
    cwd = os.getcwd()
    # pylint: disable=not-context-manager
    for uuid in UUID_SKIP_LIVE_PHOTOKIT:
        with runner.isolated_filesystem():
            result = runner.invoke(
                export,
                [
                    ".",
                    "--library",
                    os.path.join(cwd, PHOTOS_DB_LOCAL),
                    "-V",
                    "-F",
                    "--uuid",
                    uuid,
                    "--use-photos-export",
                    "--use-photokit",
                    "--skip-live",
                    "--skip-original-if-edited",
                    "--convert-to-jpeg",
                ],
            )
            assert result.exit_code == 0
            files = [str(p) for p in pathlib.Path(".").glob("IMG*")]
            assert sorted(files) == sorted(UUID_SKIP_LIVE_PHOTOKIT[uuid])
