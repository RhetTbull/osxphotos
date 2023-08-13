import pytest

import osxphotos
from osxphotos._constants import _UNKNOWN_PERSON

PHOTOS_DB = "./tests/Test-10.13.6.photoslibrary/database/photos.db"
KEYWORDS = [
    "Kids",
    "wedding",
    "flowers",
    "England",
    "London",
    "London 2018",
    "St. James's Park",
    "UK",
    "United Kingdom",
]
PERSONS = ["Katie", "Suzy", "Maria", _UNKNOWN_PERSON]
ALBUMS = ["Pumpkin Farm", "AlbumInFolder", "TestAlbum"]
KEYWORDS_DICT = {
    "Kids": 4,
    "wedding": 2,
    "flowers": 1,
    "England": 1,
    "London": 1,
    "London 2018": 1,
    "St. James's Park": 1,
    "UK": 1,
    "United Kingdom": 1,
}
PERSONS_DICT = {"Katie": 3, "Suzy": 2, "Maria": 1, _UNKNOWN_PERSON: 1}
ALBUM_DICT = {"Pumpkin Farm": 3, "TestAlbum": 1, "AlbumInFolder": 1}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_init(photosdb):
    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_db_version(photosdb):
    assert photosdb.db_version == "3301"
    # assert photosdb.db_version in osxphotos._TESTED_DB_VERSIONS


def test_photos_version(photosdb):
    assert photosdb.photos_version == 3


def test_persons(photosdb):
    import collections

    assert "Katie" in photosdb.persons
    assert collections.Counter(PERSONS) == collections.Counter(photosdb.persons)


def test_keywords(photosdb):
    import collections

    assert "wedding" in photosdb.keywords
    assert collections.Counter(KEYWORDS) == collections.Counter(photosdb.keywords)


def test_album_names(photosdb):
    import collections

    assert "Pumpkin Farm" in photosdb.albums
    assert collections.Counter(ALBUMS) == collections.Counter(photosdb.albums)


def test_keywords_dict(photosdb):
    keywords = photosdb.keywords_as_dict
    assert keywords["wedding"] == 2
    assert keywords == KEYWORDS_DICT


def test_persons_as_dict(photosdb):
    persons = photosdb.persons_as_dict
    assert persons["Maria"] == 1
    assert persons == PERSONS_DICT


def test_albums_as_dict(photosdb):
    albums = photosdb.albums_as_dict
    assert albums["Pumpkin Farm"] == 3
    assert albums == ALBUM_DICT


def test_attributes(photosdb):
    import datetime

    photos = photosdb.photos(uuid=["RWmFYiDjSyKjeK8Pfna0Eg"])
    assert len(photos) == 1
    p = photos[0]
    assert p.keywords == ["Kids"]
    assert p.original_filename == "Pumkins2.jpg"
    assert p.filename == "Pumkins2.jpg"
    assert p.date == datetime.datetime(
        2018, 9, 28, 16, 7, 7, 0, datetime.timezone(datetime.timedelta(seconds=-14400))
    )
    assert p.description == "Girl holding pumpkin"
    assert p.title == "I found one!"
    assert sorted(p.albums) == ["AlbumInFolder", "Pumpkin Farm"]
    assert p.persons == ["Katie"]
    assert p.path.endswith(
        "/tests/Test-10.13.6.photoslibrary/Masters/2019/07/26/20190726-203227/Pumkins2.jpg"
    )
    assert not p.ismissing


def test_missing(photosdb):
    photos = photosdb.photos(uuid=["6iAZJP7ZQ5iXxapoJb3ytA"])
    assert len(photos) == 1
    p = photos[0]
    assert p.path is None
    assert p.ismissing


def test_count(photosdb):
    photos = photosdb.photos()
    assert len(photos) == 7


def test_keyword_2(photosdb):
    photos = photosdb.photos(keywords=["wedding"])
    assert len(photos) == 2


def test_keyword_not_in_album(photosdb):
    # find all photos with keyword "Kids" not in the album "Pumpkin Farm"
    photos1 = photosdb.photos(albums=["Pumpkin Farm"])
    photos2 = photosdb.photos(keywords=["Kids"])
    photos3 = [p for p in photos2 if p not in photos1]
    assert len(photos3) == 1
    assert photos3[0].uuid == "6iAZJP7ZQ5iXxapoJb3ytA"
