import pytest

# test ability to search for edited files

PHOTOS_DB = "./tests/Test-10.14.6-path_edited.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-10.14.6-path_edited.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-10.14.6-path_edited.photoslibrary"

UUID_DICT = {
    "non_00_path": "6bxcNnzRQKGnK4uPrCJ9UQ",
    "standard_00_path": "3Jn73XpSQQCluzRBMWRsMA",
}


def test_path_edited1():
    # test a valid edited path
    import os.path

    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["standard_00_path"]])
    assert len(photos) == 1
    p = photos[0]
    path = p.path_edited
    assert path.endswith("resources/media/version/00/00/fullsizeoutput_d.jpeg")
    assert os.path.exists(path)


def test_path_edited2():
    # test a non-standard (not 00) edited path
    import os.path

    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["non_00_path"]])
    assert len(photos) == 1
    p = photos[0]
    path = p.path_edited
    assert path.endswith("resources/media/version/00/02/fullsizeoutput_9.jpeg")
    assert os.path.exists(path)
