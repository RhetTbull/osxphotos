"""Test ProjectInfo class"""

import pytest

import osxphotos
from osxphotos._constants import _UNKNOWN_PERSON, AlbumSortOrder

PHOTOS_DB = "./tests/Test-iPhoto-Projects-10.12.6.photoslibrary"

TOP_LEVEL_FOLDERS = ["Folder1", "iPhoto Events"]

ALBUM_NAMES = ["Album1", "Pumpkin Farm", "Event 1"]

PHOTO_ALBUM_DATA = {
    "FO2q5khAS9y4O9CkjpuYaw": ["Pumpkin Farm", "Album1", "Event 1"],
    "ZXV0MzbOSf65q82evn6G7g": ["Pumpkin Farm", "Event 1"],
}

PROJECT_NAMES = ["Photos Calendar", "Photos Card", "Slideshow1"]

PROJECT_PHOTOS = {
    "Photos Calendar": ["7xbkU3yGRiiRYWNWNwiRDw"],
    "Photos Card": ["lmFQY5k+RYup5Xpox1oEtg"],
    "Slideshow1": [
        "FO2q5khAS9y4O9CkjpuYaw",
        "ZXV0MzbOSf65q82evn6G7g",
        "47wXm7h6RfGRACCdcbLiCA",
    ],
}

PHOTO_PROJECTS = {
    "7xbkU3yGRiiRYWNWNwiRDw": ["Photos Calendar"],
    "lmFQY5k+RYup5Xpox1oEtg": ["Photos Card"],
    "FO2q5khAS9y4O9CkjpuYaw": ["Slideshow1"],
    "ZXV0MzbOSf65q82evn6G7g": ["Slideshow1"],
    "47wXm7h6RfGRACCdcbLiCA": ["Slideshow1"],
    "xOowD1CtT8uRc9KbV7Urzw": [],
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


@pytest.mark.parametrize("uuid,expected_albums", PHOTO_ALBUM_DATA.items())
def test_photoinfo_albums(photosdb, uuid, expected_albums):
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
