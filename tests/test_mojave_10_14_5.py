import pytest

# TODO: put some of this code into a pre-function

PHOTOS_DB = "./tests/Test-10.14.5.photoslibrary/database/photos.db"
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
PERSONS = ["Katie", "Suzy", "Maria"]
ALBUMS = ["Pumpkin Farm"]
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
PERSONS_DICT = {"Katie": 3, "Suzy": 2, "Maria": 1}
ALBUM_DICT = {"Pumpkin Farm": 3}


def test_init():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_db_version():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    # assert photosdb.db_version in osxphotos._TESTED_DB_VERSIONS
    assert photosdb.db_version == "4016"


def test_os_version():
    import osxphotos

    (_, major, _) = osxphotos.utils._get_os_version()
    assert major in osxphotos._constants._TESTED_OS_VERSIONS


def test_persons():
    import osxphotos
    import collections

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert "Katie" in photosdb.persons
    assert collections.Counter(PERSONS) == collections.Counter(photosdb.persons)


def test_keywords():
    import osxphotos
    import collections

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert "wedding" in photosdb.keywords
    assert collections.Counter(KEYWORDS) == collections.Counter(photosdb.keywords)


def test_album_names():
    import osxphotos
    import collections

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert "Pumpkin Farm" in photosdb.albums
    assert collections.Counter(ALBUMS) == collections.Counter(photosdb.albums)


def test_keywords_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    keywords = photosdb.keywords_as_dict
    assert keywords["wedding"] == 2
    assert keywords == KEYWORDS_DICT


def test_persons_as_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    persons = photosdb.persons_as_dict
    assert persons["Maria"] == 1
    assert persons == PERSONS_DICT


def test_albums_as_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums = photosdb.albums_as_dict
    assert albums["Pumpkin Farm"] == 3
    assert albums == ALBUM_DICT


def test_attributes():
    import datetime
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["15uNd7%8RguTEgNPKHfTWw"])
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
    assert p.albums == ["Pumpkin Farm"]
    assert p.persons == ["Katie"]
    assert p.path.endswith(
        "/tests/Test-10.14.5.photoslibrary/Masters/2019/07/27/20190727-131650/Pumkins2.jpg"
    )
    assert p.ismissing == False


def test_missing():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["od0fmC7NQx+ayVr+%i06XA"])
    assert len(photos) == 1
    p = photos[0]
    assert p.path == None
    assert p.ismissing == True


def test_count():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos()
    assert len(photos) == 7


def test_keyword_2():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(keywords=["wedding"])
    assert len(photos) == 2


def test_keyword_not_in_album():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # find all photos with keyword "Kids" not in the album "Pumpkin Farm"
    photos1 = photosdb.photos(albums=["Pumpkin Farm"])
    photos2 = photosdb.photos(keywords=["Kids"])
    photos3 = [p for p in photos2 if p not in photos1]
    assert len(photos3) == 1
    assert photos3[0].uuid == "od0fmC7NQx+ayVr+%i06XA"
