import pytest

from osxphotos._constants import _UNKNOWN_PERSON

PHOTOS_DB = "./tests/Test-10.14.6.photoslibrary/database/photos.db"

# TOP_LEVEL_FOLDERS = ["Folder1"]

# TOP_LEVEL_CHILDREN = ["SubFolder1", "SubFolder2"]

# FOLDER_ALBUM_DICT = {"Folder1": [], "SubFolder1": [], "SubFolder2": ["AlbumInFolder"]}

# ALBUM_NAMES = ["Pumpkin Farm", "AlbumInFolder", "Test Album", "Test Album"]
ALBUM_NAMES = ["Pumpkin Farm", "Test Album", "Test Album (1)"]

# ALBUM_PARENT_DICT = {
#     "Pumpkin Farm": None,
#     "AlbumInFolder": "SubFolder2",
#     "Test Album": None,
# }

# ALBUM_FOLDER_NAMES_DICT = {
#     "Pumpkin Farm": [],
#     "AlbumInFolder": ["Folder1", "SubFolder2"],
#     "Test Album": [],
# }

ALBUM_LEN_DICT = {
    "Pumpkin Farm": 3,
    "Test Album": 1,
    "Test Album (1)": 1,
    # "AlbumInFolder": 2,
}

ALBUM_PHOTO_UUID_DICT = {
    "Pumpkin Farm": [
        "HrK3ZQdlQ7qpDA0FgOYXLA",
        "15uNd7%8RguTEgNPKHfTWw",
        "8SOE9s0XQVGsuq4ONohTng",
    ],
    "Test Album": ["8SOE9s0XQVGsuq4ONohTng"],
    "Test Album (1)": ["15uNd7%8RguTEgNPKHfTWw"],
    # "AlbumInFolder": [
    #     "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
    #     "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    # ],
}

UUID_DICT = {"two_albums": "8SOE9s0XQVGsuq4ONohTng"}

######### Test FolderInfo ##########


def test_folders_1(caplog):
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    folders = photosdb.folders
    assert folders == []
    assert "Folders not yet implemented for this DB version" in caplog.text

    # # top level folders
    # folders = photosdb.folders
    # assert len(folders) == 1

    # # check folder names
    # folder_names = [f.title for f in folders]
    # assert sorted(folder_names) == sorted(TOP_LEVEL_FOLDERS)


def test_folder_names(caplog):
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # check folder names
    folder_names = photosdb.folders
    assert folder_names == []
    assert "Folders not yet implemented for this DB version" in caplog.text
    # assert sorted(folder_names) == sorted(TOP_LEVEL_FOLDERS)


@pytest.mark.skip(reason="Folders not yet impleted in Photos < 5")
def test_folders_len():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # top level folders
    folders = photosdb.folders
    assert len(folders[0]) == len(TOP_LEVEL_CHILDREN)


@pytest.mark.skip(reason="Folders not yet impleted in Photos < 5")
def test_folders_children():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # top level folders
    folders = photosdb.folders

    # children of top level folder
    children = folders[0].folders
    children_names = [f.title for f in children]
    assert sorted(children_names) == sorted(TOP_LEVEL_CHILDREN)

    for child in folders[0].folders:
        # check valid children FolderInfo
        assert child.parent
        assert child.parent.uuid == folders[0].uuid

    # check folder names
    folder_names = [f.title for f in folders]
    assert sorted(folder_names) == sorted(TOP_LEVEL_FOLDERS)


@pytest.mark.skip(reason="Folders not yet impleted in Photos < 5")
def test_folders_parent():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # top level folders
    folders = photosdb.folders

    # parent of top level folder should be none
    for folder in folders:
        assert folder.parent is None
        for child in folder.folders:
            # children's parent uuid should match folder uuid
            assert child.parent
            assert child.parent.uuid == folder.uuid


@pytest.mark.skip(reason="Folders not yet impleted in Photos < 5")
def test_folders_albums():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # top level folders
    folders = photosdb.folders

    for folder in folders:
        name = folder.title
        albums = [a.title for a in folder.album_info]
        assert sorted(albums) == sorted(FOLDER_ALBUM_DICT[name])
        for child in folder.folders:
            name = child.title
            albums = [a.title for a in child.album_info]
            assert sorted(albums) == sorted(FOLDER_ALBUM_DICT[name])


########## Test AlbumInfo ##########


def test_albums_1():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    albums = photosdb.album_info
    assert len(albums) == 3

    # check names
    album_names = [a.title for a in albums]
    assert sorted(album_names) == sorted(ALBUM_NAMES)


def test_albums_parent(caplog):
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    albums = photosdb.album_info

    for album in albums:
        parent = album.parent.title if album.parent else None
        assert "Folders not yet implemented for this DB version" in caplog.text
        # assert parent == ALBUM_PARENT_DICT[album.title]


def test_albums_folder_names(caplog):
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    albums = photosdb.album_info

    for album in albums:
        folder_names = album.folder_names
        assert "Folders not yet implemented for this DB version" in caplog.text
        # assert folder_names == ALBUM_FOLDER_NAMES_DICT[album.title]


def test_albums_folders(caplog):
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    albums = photosdb.album_info

    for album in albums:
        folders = album.folder_list
        assert "Folders not yet implemented for this DB version" in caplog.text
        # folder_names = [f.title for f in folders]
        # assert folder_names == ALBUM_FOLDER_NAMES_DICT[album.title]


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
