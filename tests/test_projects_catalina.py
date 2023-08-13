"""Test ProjectInfo class"""

import pytest

import osxphotos
from osxphotos._constants import _UNKNOWN_PERSON, AlbumSortOrder

PHOTOS_DB = "./tests/Test-iPhoto-Projects-10.15.7.photoslibrary"

TOP_LEVEL_FOLDERS = ["Folder1", "iPhoto Events"]

ALBUM_NAMES = ["Album1", "Pumpkin Farm", "Event 1"]

ALBUM_PHOTO_DATA = [
    (
        "Pumpkin Farm",
        [
            "65757433-36CE-49FE-B9AB-CD9EBE7E86EE",
            "E3BC179B-B87A-45F1-9100-209D71B2E208",
            "14EDAAE6-4840-4BDC-B83B-D0A48E9B986B",
        ],
    ),
    (
        "Album1",
        [
            "14EDAAE6-4840-4BDC-B83B-D0A48E9B986B",
        ],
    ),
]

PHOTO_ALBUM_DATA = {
    "14EDAAE6-4840-4BDC-B83B-D0A48E9B986B": ["Pumpkin Farm", "Album1", "Event 1"],
    "65757433-36CE-49FE-B9AB-CD9EBE7E86EE": ["Pumpkin Farm", "Event 1"],
}

PROJECT_NAMES = ["Photos Calendar", "Photos Card", "Slideshow1"]

PROJECT_PHOTOS = {
    "Photos Calendar": ["EF16E453-7C86-4628-9161-63563708910F"],
    "Photos Card": ["96615063-993E-458B-A9E5-7A68C75A04B6"],
    "Slideshow1": [
        "65757433-36CE-49FE-B9AB-CD9EBE7E86EE",
        "14EDAAE6-4840-4BDC-B83B-D0A48E9B986B",
        "E3BC179B-B87A-45F1-9100-209D71B2E208",
    ],
}

PHOTO_PROJECTS = {
    "EF16E453-7C86-4628-9161-63563708910F": ["Photos Calendar"],
    "96615063-993E-458B-A9E5-7A68C75A04B6": ["Photos Card"],
    "65757433-36CE-49FE-B9AB-CD9EBE7E86EE": ["Slideshow1"],
    "14EDAAE6-4840-4BDC-B83B-D0A48E9B986B": ["Slideshow1"],
    "E3BC179B-B87A-45F1-9100-209D71B2E208": ["Slideshow1"],
    "C4EA300F-50AD-4FCB-9173-D29B57B52BCF": [],
}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


#### First, test folders and albums to ensure they're working correctly (and not reporting projects as albums) #####


def test_folders_1(photosdb):
    # top level folders
    folders = photosdb.folder_info
    assert len(folders) == len(TOP_LEVEL_FOLDERS)

    # check folder names
    folder_names = [f.title for f in folders]
    assert sorted(folder_names) == sorted(TOP_LEVEL_FOLDERS)


def test_folder_names(photosdb):
    # check folder names
    folder_names = photosdb.folders
    assert sorted(folder_names) == sorted(TOP_LEVEL_FOLDERS)


def test_folders_parent(photosdb):
    # top level folders
    folders = photosdb.folder_info

    # parent of top level folder should be none
    for folder in folders:
        assert folder.parent is None
        for child in folder.subfolders:
            # children's parent uuid should match folder uuid
            assert child.parent
            assert child.parent.uuid == folder.uuid


def test_albums_1(photosdb):
    albums = photosdb.album_info
    assert len(albums) == len(ALBUM_NAMES)

    # check names
    album_names = [a.title for a in albums]
    assert sorted(album_names) == sorted(ALBUM_NAMES)


@pytest.mark.parametrize("album_name,album_uuids", ALBUM_PHOTO_DATA)
def test_photoinfo_albums_1(photosdb, album_name, album_uuids):
    """Test PhotoInfo.albums"""
    photos = photosdb.photos(uuid=album_uuids)

    albums = photos[0].albums
    assert album_name in albums


@pytest.mark.parametrize("uuid,expected_albums", PHOTO_ALBUM_DATA.items())
def test_photoinfo_albums_2(photosdb, uuid, expected_albums):
    """Test PhotoInfo.albums"""
    photo = photosdb.get_photo(uuid)

    albums = photo.albums
    assert sorted(albums) == sorted(expected_albums)


##### Now test ProjectInfo #####


def test_photosdb_project_info(photosdb):
    """Test PhotosDB.project_info"""
    projects = photosdb.project_info
    assert len(projects) == len(PROJECT_NAMES)

    # check names
    project_names = [p.title for p in projects]
    assert sorted(project_names) == sorted(PROJECT_NAMES)


@pytest.mark.parametrize("project_name,photo_uuids", PROJECT_PHOTOS.items())
def test_photosdb_project_info_photos(photosdb, project_name, photo_uuids):
    """Test PhotosDB.project_info photos"""
    projects = photosdb.project_info

    for project in projects:
        if project.title == project_name:
            assert sorted(p.uuid for p in project.photos) == sorted(photo_uuids)


@pytest.mark.parametrize("uuid,expected_projects", PHOTO_PROJECTS.items())
def test_photoinfo_project_info(photosdb, uuid, expected_projects):
    """Test PhotoInfo.project_info"""
    photo = photosdb.get_photo(uuid)

    project_names = [p.title for p in photo.project_info]
    assert sorted(project_names) == sorted(expected_projects)


@pytest.mark.parametrize("uuid,expected_projects", PHOTO_PROJECTS.items())
def test_photoinfo_project_info_asdict(photosdb, uuid, expected_projects):
    """Test PhotoInfo.project_info.asdict() #999"""
    photo = photosdb.get_photo(uuid)
    for p in photo.project_info:
        assert p.asdict()
