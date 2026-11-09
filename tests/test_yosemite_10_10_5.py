"""Test Photos 1.0 (macOS 10.10.5 Yosemite, Photos 1.0.1) library support

The test library was created by migrating tests/Test-iPhoto-9.6.1.photolibrary to Photos 1.0.1
and contains the same assets and metadata as tests/Test-El-Capitan-10.11.6.photoslibrary
(see test_el_capitan_10_11_6.py); data common to both libraries is imported from that module.
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import shutil

import pytest
from click.testing import CliRunner

import osxphotos
from osxphotos._constants import _PHOTOS_1_0_VERSION, _UNKNOWN_PERSON
from osxphotos.cli import dbversion
from osxphotos.cli.export import export
from osxphotos.photosdb.photosdb_utils import (
    create_photos1_merged_db,
    get_db_path_for_library,
    get_db_version,
    get_photos1_library_root,
    get_photos_library_version,
)

from .conftest import repo_path
from .test_el_capitan_10_11_6 import (
    ALBUM_FOLDERS,
    ALBUMS_DICT,
    KEYWORDS_DICT,
    PHOTO_DETAILS,
    PHOTOS_COUNT,
    TRASH_COUNT,
    UUID_ELDER_PARK,
    UUID_PUMKINS1,
    UUID_PUMKINS2,
    UUID_PUMPKINS3,
    UUID_ST_JAMES_PARK,
    UUIDS_TRASH,
    library_files,
)

PHOTOS_LIBRARY = repo_path("tests/Test-Yosemite-10.10.5.photoslibrary")

# Photos 1.0 had not run face detection on Pumpkins3.jpg so there are fewer unknown faces than Photos 1.5
PERSONS_DICT = {"Katie": 2, "Suzy": 1, "Maria": 1, _UNKNOWN_PERSON: 1}

# uuid: (sorted persons, sorted albums)
PHOTO_PERSONS_ALBUMS = {
    UUID_PUMKINS1: (["Katie", "Suzy"], ["Import", "Pumpkin Farm", "Test Album"]),
    UUID_PUMKINS2: (["Katie", _UNKNOWN_PERSON], ["Import", "Pumpkin Farm"]),
    UUID_PUMPKINS3: ([], ["Import", "Pumpkin Farm"]),
    UUID_ELDER_PARK: ([], ["AlbumInFolder", "Elder Park"]),
    "RgISIEPbThGVoco5LyiLjQ": (["Maria"], ["Import"]),
}

# uuid: (filename, title, description)
PHOTO_TITLES = {
    UUID_PUMKINS1: ("Pumkins1.jpg", "Can we carry this?", "Girls with pumpkins"),
    UUID_ST_JAMES_PARK: ("St James Park.jpg", "St. James's Park", None),
    UUID_ELDER_PARK: (
        "IMG_4547.jpg",
        "Elder Park",
        "Elder Park\u2069, \u2068Adelaide\u2069, \u2068Australia",
    ),
}

# uuid: path of edited image relative to library root
PATH_EDITED = {
    UUID_ST_JAMES_PARK: "resources/modelresources/75/105/KiyfES+ESdGc1D4gPOa6xQ/St. James's Park.jpg",
    "E5FQ%pg4SRyKPi4dk6rUrg": "resources/modelresources/122/53/z5AMzOJZSpKFrl4A7hsjpA/Tulips tied together at a flower shop.jpg",
    "RgISIEPbThGVoco5LyiLjQ": "resources/modelresources/103/85/gU9Vb9GhTPOzNS2CW0cD0g/wedding.jpg",
}

# uuid: thumbnail directory relative to library root
PATH_DERIVATIVES = {
    UUID_PUMKINS1: "Thumbnails/2023/09/27/20230927-064307/7NGbu3h6RkGXxBGa9lfMVQ",
    UUID_ELDER_PARK: "Thumbnails/2023/09/27/20230927-064945/QwWcnIjYRUOOiAt0h6RYWg",
    "Hd8Cr0RsSDGYja6y41%Cwg": "Thumbnails/2023/09/27/20230927-064307/Hd8Cr0RsSDGYja6y41%Cwg",
}


@pytest.fixture(scope="module")
def photosdb() -> osxphotos.PhotosDB:
    return osxphotos.PhotosDB(dbfile=PHOTOS_LIBRARY)


@pytest.fixture
def library_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    """Copy of the test library's Database folder for tests that open the library's databases directly"""
    library = tmp_path / "Test-Yosemite-10.10.5.photoslibrary"
    shutil.copytree(
        pathlib.Path(PHOTOS_LIBRARY) / "Database", library / "Database", symlinks=True
    )
    return library


def test_db_version(photosdb: osxphotos.PhotosDB):
    """Photos 1.0 library version is 477 which is zero-padded for string comparisons"""
    assert photosdb.db_version == "0477"
    assert photosdb.db_version == _PHOTOS_1_0_VERSION
    assert photosdb.db_version < "2622"  # versions are compared as strings


def test_photos_version(photosdb: osxphotos.PhotosDB):
    assert photosdb.photos_version == 1


def test_library_path(photosdb: osxphotos.PhotosDB):
    assert pathlib.Path(photosdb.library_path) == pathlib.Path(PHOTOS_LIBRARY)
    assert pathlib.Path(photosdb.db_path).name == "Library.apdb"


def test_library_not_modified():
    """Test that opening the library doesn't create or modify any files in the library"""
    files_before = library_files(PHOTOS_LIBRARY)
    osxphotos.PhotosDB(dbfile=PHOTOS_LIBRARY)
    assert library_files(PHOTOS_LIBRARY) == files_before


def test_photos_count(photosdb: osxphotos.PhotosDB):
    assert len(photosdb.photos()) == PHOTOS_COUNT
    assert sorted(p.uuid for p in photosdb.photos(intrash=True)) == sorted(UUIDS_TRASH)
    assert len(UUIDS_TRASH) == TRASH_COUNT


def test_keywords_dict(photosdb: osxphotos.PhotosDB):
    assert photosdb.keywords_as_dict == KEYWORDS_DICT


def test_persons_dict(photosdb: osxphotos.PhotosDB):
    assert photosdb.persons_as_dict == PERSONS_DICT


def test_albums_dict(photosdb: osxphotos.PhotosDB):
    assert photosdb.albums_as_dict == ALBUMS_DICT


@pytest.mark.parametrize("album,folders", list(ALBUM_FOLDERS.items()))
def test_album_folder_names(photosdb: osxphotos.PhotosDB, album: str, folders):
    album_info = [a for a in photosdb.album_info if a.title == album]
    assert len(album_info) == 1
    assert album_info[0].folder_names == folders


@pytest.mark.parametrize("uuid,data", list(PHOTO_PERSONS_ALBUMS.items()))
def test_photo_persons_albums(photosdb: osxphotos.PhotosDB, uuid: str, data):
    persons, albums = data
    photo = photosdb.get_photo(uuid)
    assert sorted(photo.persons) == persons
    assert sorted(photo.albums) == albums


@pytest.mark.parametrize("uuid,data", list(PHOTO_TITLES.items()))
def test_photo_titles(photosdb: osxphotos.PhotosDB, uuid: str, data):
    filename, title, description = data
    photo = photosdb.get_photo(uuid)
    assert photo.filename == filename
    assert photo.title == title
    assert photo.description == description


@pytest.mark.parametrize("uuid,data", list(PHOTO_DETAILS.items()))
def test_photo_details(photosdb: osxphotos.PhotosDB, uuid: str, data):
    date, width, height, orientation, uti, israw = data
    photo = photosdb.get_photo(uuid)
    assert photo.date == datetime.datetime.fromisoformat(date)
    assert photo.width == width
    assert photo.height == height
    assert photo.orientation == orientation
    assert photo.uti == uti
    assert photo.israw == israw
    assert photo.isphoto
    assert not photo.hasadjustments
    assert photo.path_edited is None


@pytest.mark.parametrize("photo", osxphotos.PhotosDB(PHOTOS_LIBRARY).photos())
def test_photo_path(photo: osxphotos.PhotoInfo):
    assert photo.path is not None
    assert pathlib.Path(photo.path).is_file()
    assert photo.path.startswith(os.path.join(PHOTOS_LIBRARY, "Masters"))


@pytest.mark.parametrize("uuid,path_edited", list(PATH_EDITED.items()))
def test_path_edited(photosdb: osxphotos.PhotosDB, uuid: str, path_edited: str):
    photo = photosdb.get_photo(uuid)
    assert photo.hasadjustments
    assert photo.path_edited == os.path.join(PHOTOS_LIBRARY, path_edited)
    assert photo.uti_edited == "public.jpeg"


def test_path_edited_count(photosdb: osxphotos.PhotosDB):
    edited = [p.uuid for p in photosdb.photos() if p.path_edited]
    assert sorted(edited) == sorted(PATH_EDITED)


@pytest.mark.parametrize("uuid,path", list(PATH_DERIVATIVES.items()))
def test_path_derivatives(photosdb: osxphotos.PhotosDB, uuid: str, path: str):
    derivatives = photosdb.get_photo(uuid).path_derivatives
    assert len(derivatives) == 2
    for derivative in derivatives:
        assert derivative.startswith(os.path.join(PHOTOS_LIBRARY, path))
        assert pathlib.Path(derivative).is_file()


def test_path_live_photo(photosdb: osxphotos.PhotosDB):
    for photo in photosdb.photos():
        assert not photo.live_photo
        assert photo.path_live_photo is None


def test_face_info(photosdb: osxphotos.PhotosDB):
    photo = photosdb.get_photo(UUID_PUMKINS1)
    faces = {face.name: face for face in photo.face_info}
    assert sorted(faces) == ["Katie", "Suzy"]
    katie = faces["Katie"]
    assert katie.uuid == "3fOD79gwQ+6faz5WuzhgDA"
    assert katie.center_x == pytest.approx(0.70166015625)
    assert katie.center_y == pytest.approx(0.5692307692307692)
    assert katie.person_info.name == "Katie"


def test_face_info_unknown_person(photosdb: osxphotos.PhotosDB):
    photo = photosdb.get_photo(UUID_PUMKINS2)
    names = sorted(face.person_info.name for face in photo.face_info)
    assert names == ["Katie", _UNKNOWN_PERSON]


def test_asdict_json(photosdb: osxphotos.PhotosDB):
    for photo in photosdb.photos() + photosdb.photos(intrash=True):
        assert photo.asdict()["uuid"] == photo.uuid
        assert json.loads(photo.json())["uuid"] == photo.uuid


def test_get_photos1_library_root():
    library = pathlib.Path(PHOTOS_LIBRARY)
    assert get_photos1_library_root(library) == library
    assert (
        get_photos1_library_root(library / "Database" / "apdb" / "Library.apdb")
        == library
    )


def test_get_photos_library_version():
    assert get_photos_library_version(PHOTOS_LIBRARY) == 1


def test_get_db_version(library_copy: pathlib.Path):
    assert get_db_version(get_db_path_for_library(library_copy)) == "0477"


def test_create_photos1_merged_db(tmp_path: pathlib.Path):
    merged_db = create_photos1_merged_db(PHOTOS_LIBRARY, tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == [merged_db.name]
    assert get_db_version(merged_db) == "0477"


def test_cli_dbversion(library_copy: pathlib.Path):
    runner = CliRunner()
    result = runner.invoke(dbversion, [str(library_copy)])
    assert result.exit_code == 0
    assert "Photos version: 1" in result.output
    assert "DB version: 0477" in result.output


def test_cli_export_edited(tmp_path: pathlib.Path):
    runner = CliRunner()
    result = runner.invoke(
        export,
        [str(tmp_path), "--library", PHOTOS_LIBRARY, "--edited", "-V"],
    )
    assert result.exit_code == 0
    files = sorted(p.name for p in tmp_path.glob("[!.]*"))
    assert files == [
        "St James Park.jpg",
        "St James Park_edited.jpeg",
        "Tulips.jpg",
        "Tulips_edited.jpeg",
        "wedding.jpg",
        "wedding_edited.jpeg",
    ]
