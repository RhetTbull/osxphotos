import pytest

from osxphotos._constants import _UNKNOWN_PERSON

PHOTOS_DB = "./tests/Test-10.15.4.photoslibrary/database/photos.db"

TOP_LEVEL_FOLDERS = ["Folder1"]

TOP_LEVEL_CHILDREN = ["SubFolder1", "SubFolder2"]

FOLDER_ALBUM_DICT = {"Folder1": [], "SubFolder1": [], "SubFolder2": ["AlbumInFolder"]}

ALBUM_NAMES = ["Pumpkin Farm", "AlbumInFolder", "Test Album", "Test Album"]

ALBUM_PARENT_DICT = {
    "Pumpkin Farm": None,
    "AlbumInFolder": "SubFolder2",
    "Test Album": None,
}

ALBUM_FOLDER_NAMES_DICT = {
    "Pumpkin Farm": [],
    "AlbumInFolder": ["Folder1", "SubFolder2"],
    "Test Album": [],
}

ALBUM_LEN_DICT = {"Pumpkin Farm": 3, "AlbumInFolder": 2, "Test Album": 1}

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
}

UUID_DICT = {"two_albums": "F12384F6-CD17-4151-ACBA-AE0E3688539E"}


def test_folders_1():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # top level folders
    folders = photosdb.folder_info
    assert len(folders) == 1

    # check folder names
    folder_names = [f.title for f in folders]
    assert sorted(folder_names) == sorted(TOP_LEVEL_FOLDERS)


def test_folder_names():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # check folder names
    folder_names = photosdb.folders
    assert sorted(folder_names) == sorted(TOP_LEVEL_FOLDERS)


def test_folders_len():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # top level folders
    folders = photosdb.folder_info
    assert len(folders[0]) == len(TOP_LEVEL_CHILDREN)


def test_folders_children():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

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


def test_folders_parent():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # top level folders
    folders = photosdb.folder_info

    # parent of top level folder should be none
    for folder in folders:
        assert folder.parent is None
        for child in folder.subfolders:
            # children's parent uuid should match folder uuid
            assert child.parent
            assert child.parent.uuid == folder.uuid


def test_folders_albums():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

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


def test_albums_1():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    albums = photosdb.album_info
    assert len(albums) == 4

    # check names
    album_names = [a.title for a in albums]
    assert sorted(album_names) == sorted(ALBUM_NAMES)


def test_albums_parent():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    albums = photosdb.album_info

    for album in albums:
        parent = album.parent.title if album.parent else None
        assert parent == ALBUM_PARENT_DICT[album.title]


def test_albums_folder_names():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    albums = photosdb.album_info

    for album in albums:
        folder_names = album.folder_names
        assert folder_names == ALBUM_FOLDER_NAMES_DICT[album.title]


def test_albums_folders():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    albums = photosdb.album_info
    for album in albums:
        folders = album.folder_list
        folder_names = [f.title for f in folders]
        assert folder_names == ALBUM_FOLDER_NAMES_DICT[album.title]


def test_albums_len():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    albums = photosdb.album_info

    for album in albums:
        assert len(album) == ALBUM_LEN_DICT[album.title]


def test_albums_photos():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    albums = photosdb.album_info

    for album in albums:
        photos = album.photos
        assert len(photos) == ALBUM_LEN_DICT[album.title]
        assert len(photos) == len(album)
        for photo in photos:
            assert photo.uuid in ALBUM_PHOTO_UUID_DICT[album.title]


def test_photoinfo_albums():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=ALBUM_PHOTO_UUID_DICT["Pumpkin Farm"])

    albums = photos[0].albums
    assert "Pumpkin Farm" in albums


def test_photoinfo_album_info():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["two_albums"]])

    album_info = photos[0].album_info
    assert len(album_info) == 2
    assert album_info[0].title in ["Pumpkin Farm", "Test Album"]
    assert album_info[1].title in ["Pumpkin Farm", "Test Album"]

    assert photos[0] in album_info[0].photos
