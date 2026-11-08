"""Test Photos 1.x (macOS 10.11.6 El Capitan, Photos 1.5) library support

The test library was created by migrating tests/Test-iPhoto-9.6.1.photolibrary to Photos 1.5
and contains the same assets and metadata.
"""

from __future__ import annotations

import collections
import datetime
import json
import os
import pathlib
import shutil

import pytest
from click.testing import CliRunner

import osxphotos
from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.cli import dbversion
from osxphotos.cli.export import export
from osxphotos.photosdb.photosdb import PhotosDBReadError
from osxphotos.photosdb.photosdb_utils import (
    create_photos1_merged_db,
    get_db_path_for_library,
    get_db_version,
    get_photos1_library_root,
    get_photos_library_version,
)

from .conftest import repo_path

PHOTOS_LIBRARY = repo_path("tests/Test-El-Capitan-10.11.6.photoslibrary")
IPHOTO_LIBRARY = repo_path("tests/Test-iPhoto-9.6.1.photolibrary")
PHOTOS_2_LIBRARY = repo_path("tests/Test-10.12.6.photoslibrary")

PHOTOS_COUNT = 13  # not in trash
TRASH_COUNT = 2

KEYWORDS_DICT = {
    "Katie": 3,
    "Suzy": 2,
    "wedding": 2,
    # iPhoto ratings and flags are converted to keywords when migrated to Photos
    "1 Star": 2,
    "4 Star": 1,
    "5 Star": 1,
    "Flagged": 1,
    "England": 1,
    "London": 1,
    "London 2018": 1,
    "St. James's Park": 1,
    "UK": 1,
    "United Kingdom": 1,
    "Digital Nomad": 1,
    "Indoor": 1,
    "Reiseblogger": 1,
    "Stock Photography": 1,
    "Top Shot": 1,
    "close up": 1,
    "colorful": 1,
    "design": 1,
    "display": 1,
    "fake": 1,
    "flower": 1,
    "flowers": 1,
    "outdoor": 1,
    "photography": 1,
    "plastic": 1,
    "stock photo": 1,
    "vibrant": 1,
}

PERSONS_DICT = {"Katie": 2, "Suzy": 1, "Maria": 1, _UNKNOWN_PERSON: 4}

ALBUMS_DICT = {
    "Import": 12,
    "Pumpkin Farm": 3,
    "Test Album": 1,
    "AlbumInFolder": 1,
    "Elder Park": 1,
    "Empty Album": 0,
}

# folder names for each album
ALBUM_FOLDERS = {
    "Import": ["iPhoto Events"],
    "Elder Park": ["iPhoto Events"],
    "AlbumInFolder": ["Folder1", "SubFolder2"],
    "Pumpkin Farm": [],
    "Test Album": [],
    "Empty Album": [],
}

UUID_PUMKINS1 = "7NGbu3h6RkGXxBGa9lfMVQ"
UUID_PUMKINS2 = "L0ddFwSDTmGwDZBWpnLF4A"
UUID_PUMPKINS3 = "TeSYQT5HRJ6R6uGZRm+VOQ"
UUID_HEIC = "WvY%8CN+RLaDKrD0GQCRoQ"
UUID_ELDER_PARK = "QwWcnIjYRUOOiAt0h6RYWg"
UUID_ST_JAMES_PARK = "QtE4HvHhSnO2W8bmbzWRSg"
UUID_RAW = "UD3w1wufQy6UcuzQ31ZF1w"

# photos in the trash; these have the same master but Hd8Cr0 is stored with a different
# thumbnail path than its master
UUIDS_TRASH = ["v4bKthQ2QyiBzDuFWcR0MA", "Hd8Cr0RsSDGYja6y41%Cwg"]

# uuid: (filename, title, description, sorted keywords, sorted persons, sorted albums)
PHOTO_DATA = {
    UUID_RAW: ("DSC03584.dng", None, None, [], [], ["Import"]),
    UUID_PUMKINS1: (
        "Pumkins1.jpg",
        "Can we carry this?",
        "Girls with pumpkins",
        ["Katie", "Suzy"],
        ["Katie", "Suzy"],
        ["Import", "Pumpkin Farm", "Test Album"],
    ),
    UUID_PUMKINS2: (
        "Pumkins2.jpg",
        "I found one!",
        "Girl holding pumpkin",
        ["4 Star", "Katie"],
        ["Katie", _UNKNOWN_PERSON],
        ["Import", "Pumpkin Farm"],
    ),
    UUID_PUMPKINS3: (
        "Pumpkins3.jpg",
        None,
        "Kids in pumpkin field",
        ["Katie", "Suzy"],
        [_UNKNOWN_PERSON, _UNKNOWN_PERSON, _UNKNOWN_PERSON],
        ["Import", "Pumpkin Farm"],
    ),
    UUID_ST_JAMES_PARK: (
        "St James Park.jpg",
        "St. James's Park",
        None,
        [
            "England",
            "London",
            "London 2018",
            "St. James's Park",
            "UK",
            "United Kingdom",
        ],
        [],
        ["Import"],
    ),
    UUID_ELDER_PARK: (
        "IMG_4547.jpg",
        "Elder Park",
        "Elder Park\u2069, \u2068Adelaide\u2069, \u2068Australia",
        [],
        [],
        ["AlbumInFolder", "Elder Park"],
    ),
    "RgISIEPbThGVoco5LyiLjQ": (
        "wedding.jpg",
        None,
        "Bride Wedding day",
        ["5 Star", "Flagged", "wedding"],
        ["Maria"],
        ["Import"],
    ),
}

# uuid: (date, width, height, orientation, uti, israw)
PHOTO_DETAILS = {
    UUID_RAW: (
        "2020-04-12T10:30:23-07:00",
        4000,
        6000,
        8,
        "com.adobe.raw-image",
        True,
    ),
    "TiiIk8KsQn+ZUVyBGno4iA": (
        "2020-04-15T10:25:51-07:00",
        4416,
        3312,
        1,
        "com.canon.cr2-raw-image",
        True,
    ),
    "ReMuru2aQOWFGSt0%%j7pg": (
        "2020-04-15T10:25:51-07:00",
        4416,
        3312,
        1,
        "public.jpeg",
        False,
    ),
    UUID_HEIC: (
        "2020-09-19T14:36:26-07:00",
        3024,
        4032,
        1,
        "public.heic",
        False,
    ),
    UUID_PUMKINS1: (
        "2018-09-28T15:35:49-07:00",
        2048,
        1365,
        1,
        "public.jpeg",
        False,
    ),
}

# uuid: path of edited image relative to library root
PATH_EDITED = {
    UUID_ST_JAMES_PARK: "resources/modelresources/122/77/zMKHfkMHSfOSLiqIlxowCQ/St James Park.jpg",
    "E5FQ%pg4SRyKPi4dk6rUrg": "resources/modelresources/119/97/waCtROxOQsCtMZoYfsOXEg/Tulips tied together at a flower shop.jpg",
    "RgISIEPbThGVoco5LyiLjQ": "resources/modelresources/51/82/3R8NEkeCTOytKCmZZ7O%Ww/wedding.jpg",
}

# uuid: thumbnail directory relative to library root
PATH_DERIVATIVES = {
    UUID_PUMKINS1: "Thumbnails/2023/09/27/20230927-064307/7NGbu3h6RkGXxBGa9lfMVQ",
    UUID_ELDER_PARK: "Thumbnails/2023/09/27/20230927-064945/QwWcnIjYRUOOiAt0h6RYWg",
    # thumbnails not stored in the same directory as the master image
    "Hd8Cr0RsSDGYja6y41%Cwg": "Thumbnails/2023/09/27/20230927-064307/Hd8Cr0RsSDGYja6y41%Cwg",
}


def library_files(library: str | os.PathLike) -> set[str]:
    """Return set of all files in library"""
    return {
        str(path.relative_to(library))
        for path in pathlib.Path(library).rglob("*")
        if path.is_file()
    }


@pytest.fixture(scope="module")
def photosdb() -> osxphotos.PhotosDB:
    return osxphotos.PhotosDB(dbfile=PHOTOS_LIBRARY)


@pytest.fixture
def library_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    """Copy of the test library's Database folder for tests that open the library's databases directly"""
    library = tmp_path / "Test-El-Capitan-10.11.6.photoslibrary"
    shutil.copytree(
        pathlib.Path(PHOTOS_LIBRARY) / "Database", library / "Database", symlinks=True
    )
    return library


def test_init(photosdb: osxphotos.PhotosDB):
    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_db_version(photosdb: osxphotos.PhotosDB):
    assert photosdb.db_version == "1801"


def test_photos_version(photosdb: osxphotos.PhotosDB):
    assert photosdb.photos_version == 1


def test_library_path(photosdb: osxphotos.PhotosDB):
    assert pathlib.Path(photosdb.library_path) == pathlib.Path(PHOTOS_LIBRARY)


def test_db_path(photosdb: osxphotos.PhotosDB):
    db_path = pathlib.Path(photosdb.db_path)
    assert db_path.name == "Library.apdb"
    assert db_path.is_file()


@pytest.mark.parametrize(
    "dbfile",
    [
        "Database/Library.apdb",
        "Database/apdb/Library.apdb",
        "Database/metaSchema.db",
    ],
)
def test_init_with_db_file(dbfile: str):
    """Test PhotosDB can be opened with path to one of the library's database files"""
    photosdb = osxphotos.PhotosDB(dbfile=os.path.join(PHOTOS_LIBRARY, dbfile))
    assert photosdb.photos_version == 1
    assert pathlib.Path(photosdb.library_path).resolve() == (
        pathlib.Path(PHOTOS_LIBRARY).resolve()
    )
    assert len(photosdb.photos()) == PHOTOS_COUNT


def test_library_not_modified():
    """Test that opening the library doesn't create or modify any files in the library"""
    files_before = library_files(PHOTOS_LIBRARY)
    osxphotos.PhotosDB(dbfile=PHOTOS_LIBRARY)
    assert library_files(PHOTOS_LIBRARY) == files_before


def test_photos_count(photosdb: osxphotos.PhotosDB):
    assert len(photosdb.photos()) == PHOTOS_COUNT
    assert len(photosdb.photos(intrash=True)) == TRASH_COUNT
    assert sorted(p.uuid for p in photosdb.photos(intrash=True)) == sorted(UUIDS_TRASH)


def test_keywords_dict(photosdb: osxphotos.PhotosDB):
    assert photosdb.keywords_as_dict == KEYWORDS_DICT


def test_persons(photosdb: osxphotos.PhotosDB):
    assert collections.Counter(photosdb.persons) == collections.Counter(
        PERSONS_DICT.keys()
    )


def test_persons_dict(photosdb: osxphotos.PhotosDB):
    assert photosdb.persons_as_dict == PERSONS_DICT


def test_person_info(photosdb: osxphotos.PhotosDB):
    persons = {p.name: p for p in photosdb.person_info}
    assert sorted(persons) == sorted(PERSONS_DICT)
    katie = persons["Katie"]
    assert katie.uuid == "d%YZTuXcTQqnfDWsiRmsTw"
    assert sorted(p.uuid for p in katie.photos) == sorted(
        [UUID_PUMKINS1, UUID_PUMKINS2]
    )
    assert katie.keyphoto.uuid == UUID_PUMKINS1
    assert persons[_UNKNOWN_PERSON].uuid is None


def test_albums_dict(photosdb: osxphotos.PhotosDB):
    assert photosdb.albums_as_dict == ALBUMS_DICT


@pytest.mark.parametrize("album,folders", list(ALBUM_FOLDERS.items()))
def test_album_folder_names(photosdb: osxphotos.PhotosDB, album: str, folders):
    album_info = [a for a in photosdb.album_info if a.title == album]
    assert len(album_info) == 1
    assert album_info[0].folder_names == folders


def test_folders(photosdb: osxphotos.PhotosDB):
    folders = {f.title: f for f in photosdb.folder_info}
    assert sorted(folders) == ["Folder1", "iPhoto Events"]
    assert sorted(f.title for f in folders["Folder1"].subfolders) == [
        "SubFolder1",
        "SubFolder2",
    ]
    assert sorted(a.title for a in folders["iPhoto Events"].album_info) == [
        "Elder Park",
        "Import",
    ]


def test_album_sort_order(photosdb: osxphotos.PhotosDB):
    album = [a for a in photosdb.album_info if a.title == "Pumpkin Farm"][0]
    assert [p.uuid for p in album.photos] == [
        UUID_PUMKINS1,
        UUID_PUMKINS2,
        UUID_PUMPKINS3,
    ]


@pytest.mark.parametrize("uuid,data", list(PHOTO_DATA.items()))
def test_photo_metadata(photosdb: osxphotos.PhotosDB, uuid: str, data):
    filename, title, description, keywords, persons, albums = data
    photo = photosdb.get_photo(uuid)
    assert photo.filename == filename
    assert photo.original_filename == filename
    assert photo.title == title
    assert photo.description == description
    assert sorted(photo.keywords) == keywords
    assert sorted(photo.persons) == persons
    assert sorted(photo.albums) == albums


@pytest.mark.parametrize("uuid,data", list(PHOTO_DETAILS.items()))
def test_photo_details(photosdb: osxphotos.PhotosDB, uuid: str, data):
    date, width, height, orientation, uti, israw = data
    photo = photosdb.get_photo(uuid)
    assert photo.date == datetime.datetime.fromisoformat(date)
    assert photo.width == width
    assert photo.height == height
    assert photo.orientation == orientation
    assert photo.uti == uti
    assert photo.uti_original == uti
    assert photo.israw == israw
    assert photo.isphoto
    assert not photo.ismovie
    assert not photo.has_raw
    assert not photo.hasadjustments
    assert photo.uti_edited is None
    assert photo.path_edited is None


def test_photo_date_added(photosdb: osxphotos.PhotosDB):
    photo = photosdb.get_photo(UUID_ELDER_PARK)
    assert photo.date_added.astimezone(datetime.timezone.utc) == datetime.datetime(
        2023, 9, 27, 6, 49, 45, tzinfo=datetime.timezone.utc
    )


def test_photo_unsupported_type(photosdb: osxphotos.PhotosDB):
    """Photos 1.x doesn't support HEIC; type and UTI should be determined from file extension"""
    photo = photosdb.get_photo(UUID_HEIC)
    assert photo.isphoto
    assert photo.uti == "public.heic"
    assert photo.path.endswith("IMG_3092.heic")


def test_photo_location(photosdb: osxphotos.PhotosDB):
    photo = photosdb.get_photo(UUID_ST_JAMES_PARK)
    assert photo.location == pytest.approx((51.50357167, -0.1318055))
    photo = photosdb.get_photo(UUID_PUMKINS1)
    assert photo.location == (None, None)


@pytest.mark.parametrize("photo", osxphotos.PhotosDB(PHOTOS_LIBRARY).photos())
def test_photo_path(photo: osxphotos.PhotoInfo):
    assert photo.path is not None
    assert pathlib.Path(photo.path).is_file()
    assert photo.path.startswith(os.path.join(PHOTOS_LIBRARY, "Masters"))
    assert not photo.ismissing


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
    photo = photosdb.get_photo(uuid)
    derivatives = photo.path_derivatives
    assert len(derivatives) == 2
    for derivative in derivatives:
        assert derivative.startswith(os.path.join(PHOTOS_LIBRARY, path))
        assert pathlib.Path(derivative).is_file()
    # sorted largest first
    assert os.path.getsize(derivatives[0]) >= os.path.getsize(derivatives[1])


def test_path_live_photo(photosdb: osxphotos.PhotosDB):
    for photo in photosdb.photos():
        assert not photo.live_photo
        assert photo.path_live_photo is None
        assert photo.path_edited_live_photo is None


def test_face_info(photosdb: osxphotos.PhotosDB):
    photo = photosdb.get_photo(UUID_PUMKINS1)
    faces = {face.name: face for face in photo.face_info}
    assert sorted(faces) == ["Katie", "Suzy"]
    katie = faces["Katie"]
    assert katie.uuid == "DVfOXk+4SIKxlAvpkr5EQg"
    assert katie.center_x == pytest.approx(0.70166015625)
    assert katie.center_y == pytest.approx(0.56923076923076921)
    assert katie.source_width == 2048
    assert katie.source_height == 1365
    assert katie.person_info.name == "Katie"


def test_face_info_unknown_person(photosdb: osxphotos.PhotosDB):
    """Faces not assigned to a person should be assigned to the unknown person"""
    photo = photosdb.get_photo(UUID_PUMPKINS3)
    assert len(photo.face_info) == 3
    for face in photo.face_info:
        assert face.name is None
        assert face.person_info.name == _UNKNOWN_PERSON


def test_asdict_json(photosdb: osxphotos.PhotosDB):
    """Test that asdict/json work for all photos"""
    for photo in photosdb.photos() + photosdb.photos(intrash=True):
        assert photo.asdict()["uuid"] == photo.uuid
        assert json.loads(photo.json())["uuid"] == photo.uuid


def test_query(photosdb: osxphotos.PhotosDB):
    photos = photosdb.query(osxphotos.QueryOptions(person=["Katie"]))
    assert sorted(p.uuid for p in photos) == sorted([UUID_PUMKINS1, UUID_PUMKINS2])
    photos = photosdb.query(osxphotos.QueryOptions(edited=True))
    assert sorted(p.uuid for p in photos) == sorted(PATH_EDITED)
    photos = photosdb.query(osxphotos.QueryOptions(album=["Pumpkin Farm"]))
    assert len(photos) == 3


def test_get_photos1_library_root():
    library = pathlib.Path(PHOTOS_LIBRARY)
    assert get_photos1_library_root(library) == library
    assert get_photos1_library_root(library / "Database" / "Library.apdb") == library
    assert (
        get_photos1_library_root(library / "Database" / "apdb" / "Library.apdb")
        == library
    )


@pytest.mark.parametrize("library", [IPHOTO_LIBRARY, PHOTOS_2_LIBRARY])
def test_get_photos1_library_root_not_photos1(library: str):
    assert get_photos1_library_root(library) is None


def test_get_photos_library_version():
    assert get_photos_library_version(PHOTOS_LIBRARY) == 1


def test_get_db_path_for_library():
    db_path = get_db_path_for_library(PHOTOS_LIBRARY)
    assert db_path.name == "Library.apdb"
    assert db_path.is_file()


def test_get_db_version(library_copy: pathlib.Path):
    db_path = get_db_path_for_library(library_copy)
    assert get_db_version(db_path) == "1801"


def test_create_photos1_merged_db(tmp_path: pathlib.Path):
    merged_db = create_photos1_merged_db(PHOTOS_LIBRARY, tmp_path)
    assert merged_db.is_file()
    # merged database should be the only file left in the destination directory
    assert [p.name for p in tmp_path.iterdir()] == [merged_db.name]
    assert get_db_version(merged_db) == "1801"


def test_create_photos1_merged_db_not_photos1(tmp_path: pathlib.Path):
    with pytest.raises(ValueError):
        create_photos1_merged_db(PHOTOS_2_LIBRARY, tmp_path)


def test_iphoto_library_not_photos():
    """iPhoto libraries share the Library.apdb format but should not be opened by PhotosDB"""
    with pytest.raises(PhotosDBReadError):
        osxphotos.PhotosDB(dbfile=IPHOTO_LIBRARY)


def test_cli_dbversion(library_copy: pathlib.Path):
    runner = CliRunner()
    result = runner.invoke(dbversion, [str(library_copy)])
    assert result.exit_code == 0
    assert "Photos version: 1" in result.output
    assert "DB version: 1801" in result.output


def test_cli_export(tmp_path: pathlib.Path):
    runner = CliRunner()
    result = runner.invoke(
        export,
        [
            str(tmp_path),
            "--library",
            PHOTOS_LIBRARY,
            "--album",
            "Pumpkin Farm",
            "--sidecar",
            "json",
            "-V",
        ],
    )
    assert result.exit_code == 0
    files = sorted(p.name for p in tmp_path.glob("*.jpg"))
    assert files == ["Pumkins1.jpg", "Pumkins2.jpg", "Pumpkins3.jpg"]
    sidecar = json.loads((tmp_path / "Pumkins1.jpg.json").read_text())[0]
    assert sidecar["XMP:Title"] == "Can we carry this?"
    assert sorted(sidecar["XMP:PersonInImage"]) == ["Katie", "Suzy"]


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
