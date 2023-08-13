import pytest

PHOTOS_DB = "./tests/Test-Movie-4_0.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-Movie-4_0.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-Movie-4_0.photoslibrary"

KEYWORDS = ["test"]
PERSONS = []
ALBUMS = []
KEYWORDS_DICT = {"test": 1}
PERSONS_DICT = {}
ALBUM_DICT = {}

UUID_DICT = {"movie": "CfnR005YQ1uvNdq8UcnFtw", "image": "XuKdBnARTB+fPyyY+uh4fQ"}

PHOTOS_LEN = 6
MOVIES_LEN = 1


def test_init():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_db_version():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert photosdb.db_version in osxphotos._constants._TESTED_DB_VERSIONS
    assert photosdb.db_version == "4025"


def test_keywords():
    import collections

    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert "test" in photosdb.keywords


def test_attributes():
    import datetime

    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["movie"]], movies=True)
    assert len(photos) == 1
    p = photos[0]
    assert p.keywords == ["test"]
    assert p.original_filename == "IMG_0670B_NOGPS.MOV"
    assert p.filename == "IMG_0670B_NOGPS.MOV"
    assert p.date == datetime.datetime(
        2019,
        12,
        28,
        12,
        19,
        54,
        0,
        datetime.timezone(datetime.timedelta(seconds=-28800)),
    )
    assert p.title == "Flickering Flame"
    assert p.description == "Movie of a fireplace"
    assert p.path.endswith(
        "tests/Test-Movie-4_0.photoslibrary/Masters/2019/12/28/20191228-202119/IMG_0670B_NOGPS.MOV"
    )
    assert not p.ismissing
    assert p.hasadjustments
    assert p.path_edited.endswith(
        "tests/Test-Movie-4_0.photoslibrary/resources/media/version/00/00/fullsizeoutput_7.mov"
    )


def test_hasadjustments1():
    # test hasadjustments
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["movie"]], movies=True)
    assert len(photos) == 1
    p = photos[0]
    assert p.hasadjustments


def test_path_edited1():
    # test a valid edited path
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["movie"]], movies=True)
    assert len(photos) == 1
    p = photos[0]
    path = p.path_edited
    assert path.endswith("resources/media/version/00/00/fullsizeoutput_7.mov")


def test_count_photos():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(movies=False)
    assert len(photos) == PHOTOS_LEN


def test_count_movies():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(movies=True, images=False)
    assert len(photos) == MOVIES_LEN


def test_count_movies_2():
    import osxphotos

    # if don't ask for movies=True, won't get any
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["movie"]], movies=False)
    assert len(photos) == 0


def test_count_all():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(images=True, movies=True)
    assert len(photos) == PHOTOS_LEN + MOVIES_LEN


def test_uti_movie():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["movie"]], movies=True)

    assert photos[0].uti == "com.apple.quicktime-movie"


def test_uti_photo():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["image"]])

    assert photos[0].uti == "public.jpeg"


def test_ismovie():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["movie"]], movies=True)

    assert photos[0].ismovie
    assert not photos[0].isphoto


def test_ismovie_not():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["image"]])

    assert not photos[0].ismovie
    assert photos[0].isphoto


def test_isphoto():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["image"]])

    assert photos[0].isphoto
    assert not photos[0].ismovie


def test_isphoto_false():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["movie"]], movies=True)

    assert not photos[0].isphoto
    assert photos[0].ismovie
