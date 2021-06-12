import pytest

import osxphotos

from osxphotos._constants import _UNKNOWN_PERSON

PHOTOS_DB = "./tests/Test-10.15.4.photoslibrary/database/photos.db"

TOP_LEVEL_FOLDERS = ["Folder1", "Folder2"]

TOP_LEVEL_CHILDREN = ["SubFolder1", "SubFolder2"]

FOLDER_ALBUM_DICT = {
    "Folder1": [],
    "SubFolder1": [],
    "SubFolder2": ["AlbumInFolder"],
    "Folder2": ["Raw"],
}

ALBUM_NAMES = ["Pumpkin Farm", "AlbumInFolder", "Test Album", "Test Album", "Raw"]

ALBUM_PARENT_DICT = {
    "Pumpkin Farm": None,
    "AlbumInFolder": "SubFolder2",
    "Test Album": None,
    "Raw": "Folder2",
}

ALBUM_FOLDER_NAMES_DICT = {
    "Pumpkin Farm": [],
    "AlbumInFolder": ["Folder1", "SubFolder2"],
    "Test Album": [],
    "Raw": ["Folder2"],
}

ALBUM_LEN_DICT = {"Pumpkin Farm": 3, "AlbumInFolder": 2, "Test Album": 1, "Raw": 4}

ALBUM_PHOTO_UUID_DICT = {
    "Pumpkin Farm": [
        "F12384F6-CD17-4151-ACBA-AE0E3688539E",
        "D79B8D77-BFFC-460B-9312-034F2877D35B",
        "1EB2B765-0765-43BA-A90C-0D0580E6172C",
    ],
    "Test Album": [
        "F12384F6-CD17-4151-ACBA-AE0E3688539E",
        "D79B8D77-BFFC-460B-9312-034F2877D35B",
    ],
    "AlbumInFolder": [
        "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
        "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    ],
    "Raw": [
        "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068",
        "A92D9C26-3A50-4197-9388-CB5F7DB9FA91",
        "4D521201-92AC-43E5-8F7C-59BC41C37A96",
        "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A",
    ],
}

UUID_DICT = {
    "two_albums": "F12384F6-CD17-4151-ACBA-AE0E3688539E",
    "album_dates": "0C514A98-7B77-4E4F-801B-364B7B65EAFA",
}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


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


def test_album_dates(photosdb):
    """Test album date methods"""
    import datetime

    album = [a for a in photosdb.album_info if a.uuid == UUID_DICT["album_dates"]][0]
    assert album.creation_date == datetime.datetime(
        2019,
        7,
        27,
        6,
        19,
        13,
        706262,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), "PDT"),
    )
    assert album.start_date == datetime.datetime(
        2018,
        9,
        28,
        12,
        35,
        49,
        63000,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), "PDT"),
    )
    assert album.end_date == datetime.datetime(
        2018,
        9,
        28,
        13,
        9,
        33,
        22000,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), "PDT"),
    )


def test_photoinfo_albums(photosdb):
    """Test PhotoInfo.albums"""
    photos = photosdb.photos(uuid=ALBUM_PHOTO_UUID_DICT["Pumpkin Farm"])

    albums = photos[0].albums
    assert "Pumpkin Farm" in albums


def test_photoinfo_albums_2(photosdb):
    """Test that PhotoInfo.albums returns only number albums expected"""
    photos = photosdb.photos(uuid=[UUID_DICT["two_albums"]])

    albums = photos[0].albums
    assert len(albums) == 2


def test_photoinfo_album_info(photosdb):
    """test PhotoInfo.album_info"""
    photos = photosdb.photos(uuid=[UUID_DICT["two_albums"]])

    album_info = photos[0].album_info
    assert len(album_info) == 2
    assert album_info[0].title in ["Pumpkin Farm", "Test Album"]
    assert album_info[1].title in ["Pumpkin Farm", "Test Album"]

    assert photos[0].uuid in [photo.uuid for photo in album_info[0].photos]
