import pytest

# TODO: put some of this code into a pre-function

PHOTOS_DB = "./tests/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-10.14.6.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-10.14.6.photoslibrary"

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
ALBUMS = ["Pumpkin Farm", "AlbumInFolder", "Test Album", "Test Album (1)"]
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
ALBUM_DICT = {
    "Pumpkin Farm": 3,
    "AlbumInFolder": 1,
    "Test Album": 1,
    "Test Album (1)": 1,
}

UUID_DICT = {
    "favorite": "6bxcNnzRQKGnK4uPrCJ9UQ",
    "not_favorite": "8SOE9s0XQVGsuq4ONohTng",
    "date_invalid": "YZFCPY24TUySvpu7owiqxA",
    "intrash": "3tljdX43R8+k6peNHVrJNQ",
    "not_intrash": "6bxcNnzRQKGnK4uPrCJ9UQ",
}

PHOTOS_DB_LEN = 8
PHOTOS_NOT_IN_TRASH_LEN = 7
PHOTOS_IN_TRASH_LEN = 1


def test_init():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_db_version():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert photosdb.db_version in osxphotos._constants._TESTED_DB_VERSIONS
    assert photosdb.db_version == "4025"


def test_db_len():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    # assert photosdb.db_version in osxphotos._TESTED_DB_VERSIONS
    assert len(photosdb) == PHOTOS_DB_LEN


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
    assert sorted(p.albums) == sorted(
        ["Pumpkin Farm", "AlbumInFolder", "Test Album (1)"]
    )
    assert p.persons == ["Katie"]
    assert p.path.endswith(
        "/tests/Test-10.14.6.photoslibrary/Masters/2019/07/27/20190727-131650/Pumkins2.jpg"
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


def test_favorite():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["favorite"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.favorite == True


def test_not_favorite():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["od0fmC7NQx+ayVr+%i06XA"])
    assert len(photos) == 1
    p = photos[0]
    assert p.favorite == False


def test_hidden():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["od0fmC7NQx+ayVr+%i06XA"])
    assert len(photos) == 1
    p = photos[0]
    assert p.hidden == True


def test_not_hidden():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["6bxcNnzRQKGnK4uPrCJ9UQ"])
    assert len(photos) == 1
    p = photos[0]
    assert p.hidden == False


def test_location_1():
    # test photo with lat/lon info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["3Jn73XpSQQCluzRBMWRsMA"])
    assert len(photos) == 1
    p = photos[0]
    lat, lon = p.location
    assert lat == pytest.approx(51.50357167)
    assert lon == pytest.approx(-0.1318055)


def test_location_2():
    # test photo with no location info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["YZFCPY24TUySvpu7owiqxA"])
    assert len(photos) == 1
    p = photos[0]
    lat, lon = p.location
    assert lat is None
    assert lon is None


def test_hasadjustments1():
    # test hasadjustments == True
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["6bxcNnzRQKGnK4uPrCJ9UQ"])
    assert len(photos) == 1
    p = photos[0]
    assert p.hasadjustments == True


def test_hasadjustments2():
    # test hasadjustments == False
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["15uNd7%8RguTEgNPKHfTWw"])
    assert len(photos) == 1
    p = photos[0]
    assert p.hasadjustments == False


def test_external_edit1():
    # test image has been edited in external editor
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["3Jn73XpSQQCluzRBMWRsMA"])
    assert len(photos) == 1
    p = photos[0]

    assert p.external_edit == True


def test_external_edit2():
    # test image has not been edited in external editor
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["6bxcNnzRQKGnK4uPrCJ9UQ"])
    assert len(photos) == 1
    p = photos[0]

    assert p.external_edit == False


def test_path_edited1():
    # test a valid edited path
    import os.path
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["6bxcNnzRQKGnK4uPrCJ9UQ"])
    assert len(photos) == 1
    p = photos[0]
    path = p.path_edited
    assert path.endswith("resources/media/version/00/00/fullsizeoutput_9.jpeg")
    assert os.path.exists(path)


def test_path_edited2():
    # test an invalid edited path
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["15uNd7%8RguTEgNPKHfTWw"])
    assert len(photos) == 1
    p = photos[0]
    path = p.path_edited
    assert path is None


def test_count():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos()
    assert len(photos) == PHOTOS_NOT_IN_TRASH_LEN


def test_photos_intrash_1():
    """ test PhotosDB.photos(intrash=True) """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(intrash=True)
    assert len(photos) == PHOTOS_IN_TRASH_LEN


def test_photos_intrash_2():
    """ test PhotosDB.photos(intrash=True) """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(intrash=True)
    for p in photos:
        assert p.intrash


def test_photos_intrash_2():
    """ test PhotosDB.photos(intrash=False) """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(intrash=False)
    for p in photos:
        assert not p.intrash


def test_photoinfo_intrash_1():
    """ Test PhotoInfo.intrash """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    p = photosdb.photos(uuid=[UUID_DICT["intrash"]], intrash=True)[0]
    assert p.intrash


def test_photoinfo_intrash_2():
    """ Test PhotoInfo.intrash and intrash=default"""
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    p = photosdb.photos(uuid=[UUID_DICT["intrash"]])
    assert not p


def test_photoinfo_not_intrash():
    """ Test PhotoInfo.intrash """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    p = photosdb.photos(uuid=[UUID_DICT["not_intrash"]])[0]
    assert not p.intrash


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


def test_get_db_path():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    db_path = photosdb.db_path
    assert db_path.endswith(PHOTOS_DB_PATH)


def test_get_library_path():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    lib_path = photosdb.library_path
    assert lib_path.endswith(PHOTOS_LIBRARY_PATH)


def test_photosdb_repr():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photosdb2 = eval(repr(photosdb))

    ignore_keys = ["_tmp_db", "_tempdir", "_tempdir_name"]
    assert {k: v for k, v in photosdb.__dict__.items() if k not in ignore_keys} == {
        k: v for k, v in photosdb2.__dict__.items() if k not in ignore_keys
    }


def test_photosinfo_repr():
    import osxphotos
    import datetime

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["favorite"]])
    photo = photos[0]
    photo2 = eval(repr(photo))

    assert {k: str(v).encode("utf-8") for k, v in photo.__dict__.items()} == {
        k: str(v).encode("utf-8") for k, v in photo2.__dict__.items()
    }


def test_multi_uuid():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["favorite"], UUID_DICT["not_favorite"]])

    assert len(photos) == 2


def test_multi_keyword():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    photos = photosdb.photos(keywords=["Kids", "wedding"])

    assert len(photos) == 6


def test_multi_album():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    photos = photosdb.photos(albums=["Pumpkin Farm", "Test Album"])

    assert len(photos) == 3


def test_multi_person():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    photos = photosdb.photos(persons=["Katie", "Suzy"])

    assert len(photos) == 3


def test_date_invalid():
    """ Test date is invalid """
    from datetime import datetime, timedelta, timezone
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["date_invalid"]])
    assert len(photos) == 1
    p = photos[0]
    delta = timedelta(seconds=p.tzoffset)
    tz = timezone(delta)
    assert p.date == datetime(1970, 1, 1).astimezone(tz=tz)


def test_date_modified_invalid():
    """ Test date modified is invalid """
    from datetime import datetime, timedelta, timezone
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["date_invalid"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.date_modified is None

