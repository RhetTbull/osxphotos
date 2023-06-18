import pytest

import osxphotos
from osxphotos._constants import _UNKNOWN_PERSON

PHOTOS_DB = "./tests/Test-10.13.6.photoslibrary/database/photos.db"

TOP_LEVEL_FOLDERS = ["Folder1", "TestFolder"]

TOP_LEVEL_CHILDREN = ["SubFolder1", "SubFolder2"]

FOLDER_ALBUM_DICT = {
    "Folder1": [],
    "SubFolder1": [],
    "SubFolder2": ["AlbumInFolder"],
    "TestFolder": ["TestAlbum"],
}

ALBUM_NAMES = ["Pumpkin Farm", "AlbumInFolder", "TestAlbum"]

ALBUM_PARENT_DICT = {
    "Pumpkin Farm": None,
    "AlbumInFolder": "SubFolder2",
    "TestAlbum": "TestFolder",
}

ALBUM_FOLDER_NAMES_DICT = {
    "Pumpkin Farm": [],
    "AlbumInFolder": ["Folder1", "SubFolder2"],
    "TestAlbum": ["TestFolder"],
}

ALBUM_LEN_DICT = {"Pumpkin Farm": 3, "AlbumInFolder": 1, "TestAlbum": 1}

ALBUM_PHOTO_UUID_DICT = {
    "Pumpkin Farm": [
        "vAZGdUK1QdGfWPgC+KsJag",
        "NlY8CklESxGpaKsTVHB3HQ",
        "RWmFYiDjSyKjeK8Pfna0Eg",
    ],
    "AlbumInFolder": ["RWmFYiDjSyKjeK8Pfna0Eg"],
    "TestAlbum": ["NlY8CklESxGpaKsTVHB3HQ"],
}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


######### Test FolderInfo ##########


def test_folders_1(photosdb):
    folders = photosdb.folders

    # top level folders
    folders = photosdb.folder_info
    assert len(folders) == len(TOP_LEVEL_FOLDERS)

    # check folder names
    folder_names = [f.title for f in folders]
    assert sorted(folder_names) == sorted(TOP_LEVEL_FOLDERS)


def test_folder_names(photosdb):
    # check folder names
    folder_names = photosdb.folders
    assert folder_names == TOP_LEVEL_FOLDERS
    assert sorted(folder_names) == sorted(TOP_LEVEL_FOLDERS)


def test_folders_len(photosdb):
    # top level folders
    folders = photosdb.folder_info
    assert len(folders[0]) == len(TOP_LEVEL_CHILDREN)


def test_folders_children(photosdb):
    # top level folders
    folders = photosdb.folder_info

    # children of top level folder
    children = folders[0].subfolders
    children_names = [f.title for f in children]
    assert sorted(children_names) == sorted(TOP_LEVEL_CHILDREN)

    for child in folders[0].subfolders:
        # check valid children FolderInfo
        assert child.parent
        assert child.parent.uuid == folders[0].uuid

    # check folder names
    folder_names = [f.title for f in folders]
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


def test_folders_albums(photosdb):
    # top level folders
    folders = photosdb.folder_info

    for folder in folders:
        name = folder.title
        albums = [a.title for a in folder.album_info]
        assert sorted(albums) == sorted(FOLDER_ALBUM_DICT[name])
        for child in folder.subfolders:
            name = child.title
            albums = [a.title for a in child.album_info]
            assert sorted(albums) == sorted(FOLDER_ALBUM_DICT[name])


########## Test AlbumInfo ##########


def test_albums_1(photosdb):
    albums = photosdb.album_info
    assert len(albums) == len(ALBUM_NAMES)

    # check names
    album_names = [a.title for a in albums]
    assert sorted(album_names) == sorted(ALBUM_NAMES)


def test_albums_parent(photosdb):
    albums = photosdb.album_info

    for album in albums:
        parent = album.parent.title if album.parent else None
        assert parent == ALBUM_PARENT_DICT[album.title]


def test_albums_folder_names(photosdb):
    albums = photosdb.album_info

    for album in albums:
        folder_names = album.folder_names
        assert folder_names == ALBUM_FOLDER_NAMES_DICT[album.title]


def test_albums_folders(photosdb):
    albums = photosdb.album_info

    for album in albums:
        folders = album.folder_list
        folder_names = [f.title for f in folders]
        assert folder_names == ALBUM_FOLDER_NAMES_DICT[album.title]


def test_albums_len(photosdb):
    albums = photosdb.album_info

    for album in albums:
        assert len(album) == ALBUM_LEN_DICT[album.title]


def test_albums_photos(photosdb):
    albums = photosdb.album_info

    for album in albums:
        photos = album.photos
        assert len(photos) == ALBUM_LEN_DICT[album.title]
        assert len(photos) == len(album)
        for photo in photos:
            assert photo.uuid in ALBUM_PHOTO_UUID_DICT[album.title]


def test_photoinfo_albums(photosdb):
    photos = photosdb.photos(uuid=ALBUM_PHOTO_UUID_DICT["Pumpkin Farm"])

    albums = photos[0].albums
    assert "Pumpkin Farm" in albums
