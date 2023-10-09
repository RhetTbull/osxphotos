""" Basic tests for Photos 7 on macOS 12.0.0 Developer Beta """

import datetime
import os
import os.path
import pathlib
import sqlite3
import tempfile
import time
from collections import Counter, namedtuple

import pytest

import osxphotos
from osxphotos._constants import _UNKNOWN_PERSON
from osxphotos.exifwriter import ExifWriter
from osxphotos.platform import get_macos_version, is_macos

OS_VERSION = get_macos_version() if is_macos else (None, None, None)
# SKIP_TEST = "OSXPHOTOS_TEST_EXPORT" not in os.environ or OS_VERSION[1] != "17"
SKIP_TEST = True  # don't run any of the local library tests
PHOTOS_DB_LOCAL = os.path.expanduser("~/Pictures/Photos Library.photoslibrary")

PHOTOS_DB = "tests/Test-12.0.0.dev-beta.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-12.0.0.dev-beta.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-12.0.0.dev-beta.photoslibrary"

PHOTOS_DB_LEN = 21
PHOTOS_NOT_IN_TRASH_LEN = 19
PHOTOS_IN_TRASH_LEN = 2
PHOTOS_DB_IMPORT_SESSIONS = 15

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
    "foo/bar",
    "Travel",
    "Maria",
    "Drink",
    "Val d'Isère",
    "Wine",
    "Wine Bottle",
]
# Photos 5 includes blank person for detected face
PERSONS = ["Katie", "Suzy", "Maria", _UNKNOWN_PERSON]
ALBUMS = [
    "Pumpkin Farm",
    "Test Album",  # there are 2 albums named "Test Album" for testing duplicate album names
    "AlbumInFolder",
    "Raw",
    "I have a deleted twin",  # there's an empty album with same name that has been deleted
    "EmptyAlbum",
    "2018-10 - Sponsion, Museum, Frühstück, Römermuseum",
    "2019-10/11 Paris Clermont",
    "Multi Keyword",
]

KEYWORDS_DICT = {
    "Kids": 4,
    "wedding": 3,
    "Travel": 2,
    "Wine": 2,
    "Val d'Isère": 2,
    "Drink": 2,
    "Wine Bottle": 2,
    "UK": 1,
    "England": 1,
    "London": 1,
    "United Kingdom": 1,
    "London 2018": 1,
    "St. James's Park": 1,
    "flowers": 1,
    "foo/bar": 1,
    "Maria": 1,
    "Birthday": 0,
    "Digital Nomad": 0,
    "Family": 0,
    "Indoor": 0,
    "Reiseblogger": 0,
    "Stock Photography": 0,
    "Top Shot": 0,
    "Vacation": 0,
    "close up": 0,
    "colorful": 0,
    "design": 0,
    "display": 0,
    "fake": 0,
    "flower": 0,
    "kids": 0,
    "outdoor": 0,
    "photography": 0,
    "plastic": 0,
    "raw-only": 0,
    "stock photo": 0,
    "vibrant": 0,
    "we": 0,
}

PERSONS_DICT = {"Katie": 3, "Suzy": 2, "Maria": 2, _UNKNOWN_PERSON: 1}

ALBUM_DICT = {
    "Pumpkin Farm": 3,
    "Test Album": 2,
    "AlbumInFolder": 2,
    "Raw": 4,
    "I have a deleted twin": 1,
    "EmptyAlbum": 0,
    "2018-10 - Sponsion, Museum, Frühstück, Römermuseum": 1,
    "2019-10/11 Paris Clermont": 1,
    "Multi Keyword": 2,
}  # Note: there are 2 albums named "Test Album" for testing duplicate album names

UUID_DICT = {
    "missing": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "favorite": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "not_favorite": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "hidden": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "not_hidden": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "has_adjustments": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "adjustments_info": "7783E8E6-9CAC-40F3-BE22-81FB7051C266",
    "no_adjustments": "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068",
    "location": "DC99FBDD-7A52-4100-A5BB-344131646C30",
    "no_location": "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "external_edit": "DC99FBDD-7A52-4100-A5BB-344131646C30",
    "no_external_edit": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "export": "D79B8D77-BFFC-460B-9312-034F2877D35B",  # "Pumkins2.jpg"
    "export_tif": "8846E3E6-8AC8-4857-8448-E3D025784410",
    "in_album": "D79B8D77-BFFC-460B-9312-034F2877D35B",  # "Pumkins2.jpg"
    "date_invalid": "8846E3E6-8AC8-4857-8448-E3D025784410",
    "intrash": "71E3E212-00EB-430D-8A63-5E294B268554",
    "not_intrash": "DC99FBDD-7A52-4100-A5BB-344131646C30",
    "intrash_person_keywords": "6FD38366-3BF2-407D-81FE-7153EB6125B6",
    "import_session": "8846E3E6-8AC8-4857-8448-E3D025784410",
    "movie": "D1359D09-1373-4F3B-B0E3-1A4DE573E4A3",
    "description_newlines": "7F74DD34-5920-4DA3-B284-479887A34F66",
    "no_duplicates": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "multi_query_1": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "multi_query_2": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
}

UUID_DICT_LOCAL = {
    "not_visible": "4A836160-51B2-4E32-907D-ECDDB2CEC657",  # IMG_9815.JPG
    "burst": "9A5B4CE6-6A9F-4917-95D4-1C98D14FCE4F",  # IMG_9812.JPG
    "burst_key": "9A5B4CE6-6A9F-4917-95D4-1C98D14FCE4F",  # IMG_9812.JPG
    "burst_not_key": "4A836160-51B2-4E32-907D-ECDDB2CEC657",  # IMG_9815.JPG
    "burst_selected": "75154738-83AA-4DCD-A913-632D5D1C0FEE",  # IMG_9814.JPG
    "burst_not_selected": "89E235DD-B9AC-4E8D-BDA2-986981CA7582",  # IMG_9813.JPG
    "burst_default": "F5E6BD24-B493-44E9-BDA2-7AD9D2CC8C9D",  # IMG_9816.JPG
    "burst_not_default": "75154738-83AA-4DCD-A913-632D5D1C0FEE",  # IMG_9814.JPG
}

UUID_PUMPKIN_FARM = [
    "F12384F6-CD17-4151-ACBA-AE0E3688539E",
    "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "1EB2B765-0765-43BA-A90C-0D0580E6172C",
]

ALBUM_SORT_ORDER = [
    "1EB2B765-0765-43BA-A90C-0D0580E6172C",
    "F12384F6-CD17-4151-ACBA-AE0E3688539E",
    "D79B8D77-BFFC-460B-9312-034F2877D35B",
]
ALBUM_KEY_PHOTO = "D79B8D77-BFFC-460B-9312-034F2877D35B"

UTI_DICT = {
    "8846E3E6-8AC8-4857-8448-E3D025784410": "public.tiff",
    "7783E8E6-9CAC-40F3-BE22-81FB7051C266": "public.jpeg",
    "1EB2B765-0765-43BA-A90C-0D0580E6172C": "public.jpeg",
}


UTI_ORIGINAL_DICT = {
    "8846E3E6-8AC8-4857-8448-E3D025784410": "public.tiff",
    "7783E8E6-9CAC-40F3-BE22-81FB7051C266": "public.heic",
    "1EB2B765-0765-43BA-A90C-0D0580E6172C": "public.jpeg",
}


RawInfo = namedtuple(
    "RawInfo",
    [
        "comment",
        "original_filename",
        "has_raw",
        "israw",
        "raw_original",
        "uti",
        "uti_original",
        "uti_raw",
    ],
)

RAW_DICT = {
    "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068": RawInfo(
        "raw image, no jpeg pair",
        "DSC03584.dng",
        False,
        True,
        False,
        "com.adobe.raw-image",
        "com.adobe.raw-image",
        None,
    ),
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91": RawInfo(
        "raw+jpeg, jpeg original",
        "IMG_1994.JPG",
        True,
        False,
        False,
        "public.jpeg",
        "public.jpeg",
        "com.canon.cr2-raw-image",
    ),
    "4D521201-92AC-43E5-8F7C-59BC41C37A96": RawInfo(
        "raw+jpeg, raw original",
        "IMG_1997.JPG",
        True,
        False,
        True,
        "public.jpeg",
        "public.jpeg",
        "com.canon.cr2-raw-image",
    ),
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51": RawInfo(
        "jpeg, no raw",
        "wedding.jpg",
        False,
        False,
        False,
        "public.jpeg",
        "public.jpeg",
        None,
    ),
}

ORIGINAL_FILENAME_DICT = {
    "uuid": "D79B8D77-BFFC-460B-9312-034F2877D35B",
    "filename": "D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg",
    "original_filename": "Pumkins2.jpg",
}

UUID_IS_REFERENCE = "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"
UUID_NOT_REFERENCE = "F12384F6-CD17-4151-ACBA-AE0E3688539E"

UUID_DUPLICATE = ""


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


@pytest.fixture(scope="module")
def photosdb_local():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_LOCAL)


def test_init1():
    # test named argument

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_init2():
    # test positional argument

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_init3():
    # test positional and named argument (raises exception)

    with pytest.raises(Exception):
        assert osxphotos.PhotosDB(PHOTOS_DB, dbfile=PHOTOS_DB)


def test_init4():
    # test invalid db

    (bad_db, bad_db_name) = tempfile.mkstemp(suffix=".db", prefix="osxphotos-")
    os.close(bad_db)

    with pytest.raises(Exception):
        assert osxphotos.PhotosDB(bad_db_name)

    with pytest.raises(Exception):
        assert osxphotos.PhotosDB(dbfile=bad_db_name)

    try:
        os.remove(bad_db_name)
    except:
        pass


def test_init5(mocker):
    # test failed get_last_library_path

    def bad_library():
        return None

    # get_last_library actually in utils but need to patch it in photosdb because it's imported into photosdb
    # because of the layout of photosdb/ need to patch it this way...don't really understand why, but it works
    mocker.patch("osxphotos.photosdb.photosdb.get_last_library_path", new=bad_library)

    with pytest.raises(Exception):
        assert osxphotos.PhotosDB()


def test_db_len(photosdb):
    # assert photosdb.db_version in osxphotos._TESTED_DB_VERSIONS
    assert len(photosdb) == PHOTOS_DB_LEN


def test_db_version(photosdb):
    # assert photosdb.db_version in osxphotos._TESTED_DB_VERSIONS
    assert photosdb.db_version == "6000"


def test_photos_version(photosdb):
    assert photosdb.photos_version == 7


def test_persons(photosdb):
    assert "Katie" in photosdb.persons
    assert Counter(PERSONS) == Counter(photosdb.persons)


def test_keywords(photosdb):
    assert "wedding" in photosdb.keywords
    assert Counter(KEYWORDS) == Counter(photosdb.keywords)


def test_album_names(photosdb):
    assert "Pumpkin Farm" in photosdb.albums
    assert Counter(ALBUMS) == Counter(photosdb.albums)


def test_keywords_dict(photosdb):
    keywords = photosdb.keywords_as_dict
    assert keywords["wedding"] == 3
    assert keywords == KEYWORDS_DICT


def test_persons_as_dict(photosdb):
    persons = photosdb.persons_as_dict
    assert persons["Maria"] == 2
    assert persons == PERSONS_DICT


def test_albums_as_dict(photosdb):
    albums = photosdb.albums_as_dict
    assert albums["Pumpkin Farm"] == 3
    assert albums == ALBUM_DICT


def test_album_sort_order(photosdb):
    album = [a for a in photosdb.album_info if a.title == "Pumpkin Farm"][0]
    photos = album.photos

    uuids = [p.uuid for p in photos]
    assert uuids == ALBUM_SORT_ORDER


def test_album_empty_album(photosdb):
    album = [a for a in photosdb.album_info if a.title == "EmptyAlbum"][0]
    photos = album.photos
    assert photos == []


def test_attributes(photosdb):
    photos = photosdb.photos(uuid=["D79B8D77-BFFC-460B-9312-034F2877D35B"])
    assert len(photos) == 1
    p = photos[0]
    assert p.keywords == ["Kids"]
    assert p.original_filename == "Pumkins2.jpg"
    assert p.filename == "D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg"
    assert p.date == datetime.datetime(
        2018, 9, 28, 16, 7, 7, 0, datetime.timezone(datetime.timedelta(seconds=-14400))
    )
    assert p.date_added == datetime.datetime(
        2019,
        7,
        27,
        9,
        16,
        49,
        778432,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
    )
    assert p.description == "Girl holding pumpkin"
    assert p.title == "I found one!"
    assert sorted(p.albums) == ["Multi Keyword", "Pumpkin Farm", "Test Album"]
    assert p.persons == ["Katie"]
    assert p.path.endswith(
        f"{PHOTOS_LIBRARY_PATH}/originals/D/D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg"
    )
    assert not p.ismissing


def test_attributes_2(photosdb):
    """Test attributes including height, width, etc"""

    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])
    assert len(photos) == 1
    p = photos[0]
    assert sorted(p.keywords) == ["Maria", "wedding"]
    assert p.original_filename == "wedding.jpg"
    assert p.filename == "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51.jpeg"
    assert p.date == datetime.datetime(
        2019,
        4,
        15,
        14,
        40,
        24,
        86000,
        datetime.timezone(datetime.timedelta(seconds=-14400)),
    )
    assert p.description == "Bride Wedding day"
    assert p.title is None
    assert sorted(p.albums) == [
        "AlbumInFolder",
        "I have a deleted twin",
        "Multi Keyword",
    ]
    assert p.persons == ["Maria"]
    assert p.path.endswith(
        f"{PHOTOS_LIBRARY_PATH}/originals/E/E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51.jpeg"
    )
    assert not p.ismissing
    assert p.hasadjustments
    assert p.height == 1325
    assert p.width == 1526
    assert p.original_height == 1367
    assert p.original_width == 2048
    assert p.orientation == 1
    assert p.original_orientation == 1
    assert p.original_filesize == 460483


def test_missing(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["missing"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.path is None
    assert p.ismissing


def test_favorite(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["favorite"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.favorite


def test_not_favorite(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["not_favorite"]])
    assert len(photos) == 1
    p = photos[0]
    assert not p.favorite


def test_hidden(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["hidden"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.hidden


def test_not_hidden(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["not_hidden"]])
    assert len(photos) == 1
    p = photos[0]
    assert not p.hidden


def test_visible(photosdb):
    """test visible"""
    photos = photosdb.photos(uuid=[UUID_DICT["not_hidden"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.visible


def test_not_burst(photosdb):
    """test not burst"""
    photos = photosdb.photos(uuid=[UUID_DICT["not_hidden"]])
    assert len(photos) == 1
    p = photos[0]
    assert not p.burst


def test_location_1(photosdb):
    # test photo with lat/lon info

    photos = photosdb.photos(uuid=[UUID_DICT["location"]])
    assert len(photos) == 1
    p = photos[0]
    lat, lon = p.location
    assert lat == pytest.approx(51.50357167)
    assert lon == pytest.approx(-0.1318055)


def test_location_2(photosdb):
    # test photo with no location info

    photos = photosdb.photos(uuid=[UUID_DICT["no_location"]])
    assert len(photos) == 1
    p = photos[0]
    lat, lon = p.location
    assert lat is None
    assert lon is None


def test_hasadjustments1(photosdb):
    # test hasadjustments

    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.hasadjustments


def test_hasadjustments2(photosdb):
    # test hasadjustments == False

    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])
    assert len(photos) == 1
    p = photos[0]
    assert not p.hasadjustments


def test_external_edit1(photosdb):
    # test image has been edited in external editor

    photos = photosdb.photos(uuid=[UUID_DICT["external_edit"]])
    assert len(photos) == 1
    p = photos[0]

    assert p.external_edit


def test_external_edit2(photosdb):
    # test image has not been edited in external editor

    photos = photosdb.photos(uuid=[UUID_DICT["no_external_edit"]])
    assert len(photos) == 1
    p = photos[0]

    assert not p.external_edit


def test_path_edited1(photosdb):
    # test a valid edited path

    photos = photosdb.photos(uuid=["E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"])
    assert len(photos) == 1
    p = photos[0]
    path = p.path_edited
    assert path.endswith(
        "resources/renders/E/E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51_1_201_a.jpeg"
    )
    assert os.path.exists(path)


def test_path_edited2(photosdb):
    # test an invalid edited path

    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])
    assert len(photos) == 1
    p = photos[0]
    path = p.path_edited
    assert path is None


def test_path_derivatives(photosdb):
    # test an path_derivatives

    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])
    assert len(photos) == 1
    p = photos[0]
    path = p.path_derivatives
    derivs = [
        "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068_1_100_o.jpeg",
        "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068_1_105_c.jpeg",
        "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068_4_5005_c.jpeg",
    ]
    for i, p in enumerate(path):
        assert p.endswith(derivs[i])


def test_ismovie(photosdb):
    # test ismovie

    photos = photosdb.photos(uuid=[UUID_DICT["movie"]])
    p = photos[0]
    assert p.ismovie


def test_not_ismovie(photosdb):
    # test ismovie == False

    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])
    p = photos[0]
    assert not p.ismovie


def test_count(photosdb):
    photos = photosdb.photos()
    assert len(photos) == PHOTOS_NOT_IN_TRASH_LEN


def test_photos_intrash_1(photosdb):
    """test PhotosDB.photos(intrash=True)"""

    photos = photosdb.photos(intrash=True)
    assert len(photos) == PHOTOS_IN_TRASH_LEN


def test_photos_intrash_2(photosdb):
    """test PhotosDB.photos(intrash=True)"""

    photos = photosdb.photos(intrash=True)
    for p in photos:
        assert p.intrash


def test_photos_intrash_3(photosdb):
    """test PhotosDB.photos(intrash=False)"""

    photos = photosdb.photos(intrash=False)
    for p in photos:
        assert not p.intrash


def test_photoinfo_intrash_1(photosdb):
    """Test PhotoInfo.intrash"""

    p = photosdb.photos(uuid=[UUID_DICT["intrash"]], intrash=True)[0]
    assert p.intrash
    assert p.date_trashed.isoformat() == "2120-06-10T11:24:47.685857-05:00"


def test_photoinfo_intrash_2(photosdb):
    """Test PhotoInfo.intrash and intrash=default"""

    p = photosdb.photos(uuid=[UUID_DICT["intrash"]])
    assert not p


def test_photoinfo_intrash_3(photosdb):
    """Test PhotoInfo.intrash and photo has keyword and person"""

    p = photosdb.photos(uuid=[UUID_DICT["intrash_person_keywords"]], intrash=True)[0]
    assert p.intrash
    assert "Maria" in p.persons
    assert "wedding" in p.keywords


def test_photoinfo_intrash_4(photosdb):
    """Test PhotoInfo.intrash and photo has keyword and person"""

    p = photosdb.photos(persons=["Maria"], intrash=True)[0]
    assert p.intrash
    assert "Maria" in p.persons
    assert "wedding" in p.keywords


def test_photoinfo_intrash_5(photosdb):
    """Test PhotoInfo.intrash and photo has keyword and person"""

    p = photosdb.photos(keywords=["wedding"], intrash=True)[0]
    assert p.intrash
    assert "Maria" in p.persons
    assert "wedding" in p.keywords


def test_photoinfo_not_intrash(photosdb):
    """Test PhotoInfo.intrash"""

    p = photosdb.photos(uuid=[UUID_DICT["not_intrash"]])[0]
    assert not p.intrash
    assert p.date_trashed is None


def test_keyword_2(photosdb):
    photos = photosdb.photos(keywords=["wedding"])
    assert len(photos) == 2  # won't show the one in the trash


def test_keyword_not_in_album(photosdb):
    # find all photos with keyword "Kids" not in the album "Pumpkin Farm"
    photos1 = photosdb.photos(albums=["Pumpkin Farm"])
    photos2 = photosdb.photos(keywords=["Kids"])
    photos3 = [p for p in photos2 if p not in photos1]
    assert len(photos3) == 1
    assert photos3[0].uuid == "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"


def test_album_folder_name(photosdb):
    """Test query with album name same as a folder name"""

    photos = photosdb.photos(albums=["Pumpkin Farm"])
    assert sorted(p.uuid for p in photos) == sorted(UUID_PUMPKIN_FARM)


def test_multi_person(photosdb):
    photos = photosdb.photos(persons=["Katie", "Suzy"])

    assert len(photos) == 3


def test_get_db_path(photosdb):
    db_path = photosdb.db_path
    assert db_path.endswith(PHOTOS_DB_PATH)


def test_get_library_path(photosdb):
    lib_path = photosdb.library_path
    assert lib_path.endswith(PHOTOS_LIBRARY_PATH)


def test_get_db_connection(photosdb):
    """Test PhotosDB.get_db_connection"""

    conn, cursor = photosdb.get_db_connection()

    assert isinstance(conn, sqlite3.Connection)
    assert isinstance(cursor, sqlite3.Cursor)

    results = conn.execute("SELECT ZUUID FROM ZASSET WHERE ZFAVORITE = 1;").fetchall()
    assert len(results) == 1
    assert results[0][0] == "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"  # uuid

    conn.close()


def test_export_1(photosdb):
    # test basic export
    # get an unedited image and export it using default filename

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].original_filename
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_2(photosdb):
    # test export with user provided filename

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_3(photosdb):
    # test file already exists and test increment=True (default)

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].original_filename
    filename2 = pathlib.Path(filename)
    filename2 = f"{filename2.stem} (1){filename2.suffix}"
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest = photos[0].export(dest)[0]
    got_dest_2 = photos[0].export(dest)[0]

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)


def test_export_4(photosdb):
    # test user supplied file already exists and test increment=True (default)

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    filename2 = f"osxphotos-export-2-test-{timestamp} (1).jpg"
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest = photos[0].export(dest, filename)[0]
    got_dest_2 = photos[0].export(dest, filename)[0]

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)


def test_export_5(photosdb):
    # test file already exists and test increment=True (default)
    # and overwrite = True

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].original_filename
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)[0]
    got_dest_2 = photos[0].export(dest, overwrite=True)[0]

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)


def test_export_6(photosdb):
    # test user supplied file already exists and test increment=True (default)
    # and overwrite = True

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename)[0]
    got_dest_2 = photos[0].export(dest, filename, overwrite=True)[0]

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)


def test_export_7(photosdb):
    # test file already exists and test increment=False (not default), overwrite=False (default)
    # should raise exception

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename

    got_dest = photos[0].export(dest)[0]
    with pytest.raises(Exception) as e:
        # try to export again with increment = False
        assert photos[0].export(dest, increment=False)
    assert e.type == type(FileExistsError())


def test_export_8(photosdb):
    # try to export missing file

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["missing"]])

    assert photos[0].export(dest) == []


def test_export_9(photosdb):
    # try to export edited file that's not edited
    # should raise exception

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    filename = photos[0].filename

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, edited=True)
    assert e.type == ValueError


def test_export_10(photosdb):
    # try to export edited file that's not edited and name provided
    # should raise exception

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, filename, edited=True)
    assert e.type == ValueError


def test_export_11(photosdb):
    # export edited file with name provided

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename, edited=True)[0]
    assert got_dest == expected_dest


def test_export_12(photosdb):
    # export edited file with default name

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    edited_name = pathlib.Path(photos[0].path_edited).name
    edited_suffix = pathlib.Path(edited_name).suffix
    filename = (
        pathlib.Path(photos[0].original_filename).stem + "_edited" + edited_suffix
    )
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, edited=True)[0]
    assert got_dest == expected_dest


def test_export_13(photosdb):
    # export to invalid destination
    # should raise exception

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name

    # create a folder that doesn't exist
    i = 0
    while os.path.isdir(dest):
        dest = os.path.join(dest, str(i))
        i += 1

    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest)
    assert e.type == type(FileNotFoundError())


def test_export_14(photosdb, caplog):
    # test export with user provided filename with different (but valid) extension than source

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export_tif"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.tif"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)

    assert "Invalid destination suffix" not in caplog.text


def test_export_no_original_filename(photosdb):
    # test export OK if original filename is null
    # issue #267

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    # monkey patch original_filename for testing
    original_filename = photos[0]._info["originalFilename"]
    photos[0]._info["originalFilename"] = None
    filename = f"{photos[0].uuid}.jpeg"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)

    photos[0]._info["originalFilename"] = original_filename


def test_eq():
    """Test equality of two PhotoInfo objects"""

    photosdb1 = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photosdb2 = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos1 = photosdb1.photos(uuid=[UUID_DICT["export"]])
    photos2 = photosdb2.photos(uuid=[UUID_DICT["export"]])
    assert photos1[0] == photos2[0]


def test_eq_2():
    """Test equality of two PhotoInfo objects when one has memoized property"""

    photosdb1 = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photosdb2 = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos1 = photosdb1.photos(uuid=[UUID_DICT["in_album"]])
    photos2 = photosdb2.photos(uuid=[UUID_DICT["in_album"]])

    # memoize a value
    albums = photos1[0].albums
    assert albums

    assert photos1[0] == photos2[0]


def test_not_eq(photosdb):
    photos1 = photosdb.photos(uuid=[UUID_DICT["export"]])
    photos2 = photosdb.photos(uuid=[UUID_DICT["missing"]])
    assert photos1[0] != photos2[0]


def test_photosdb_repr():
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photosdb2 = eval(repr(photosdb))

    ignore_keys = ["_tmp_db", "_tempdir", "_tempdir_name", "_db_connection"]
    assert {k: v for k, v in photosdb.__dict__.items() if k not in ignore_keys} == {
        k: v for k, v in photosdb2.__dict__.items() if k not in ignore_keys
    }


def test_photosinfo_repr(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["favorite"]])
    photo = photos[0]
    photo2 = eval(repr(photo))

    assert {k: str(v).encode("utf-8") for k, v in photo.__dict__.items()} == {
        k: str(v).encode("utf-8") for k, v in photo2.__dict__.items()
    }


@pytest.mark.usefixtures("set_tz_pacific")
def test_from_to_date(photosdb):
    """test from_date / to_date"""

    photos = photosdb.photos(from_date=datetime.datetime(2018, 10, 28))
    assert len(photos) == 12

    photos = photosdb.photos(to_date=datetime.datetime(2018, 10, 28))
    assert len(photos) == 7

    photos = photosdb.photos(
        from_date=datetime.datetime(2018, 9, 28), to_date=datetime.datetime(2018, 9, 29)
    )
    assert len(photos) == 4


@pytest.mark.usefixtures("set_tz_pacific")
def test_from_to_date_tz(photosdb):
    """Test from_date / to_date with and without timezone"""

    photos = photosdb.photos(
        from_date=datetime.datetime(2018, 9, 28, 13, 7, 0),
        to_date=datetime.datetime(2018, 9, 28, 13, 9, 0),
    )
    assert len(photos) == 1
    assert photos[0].uuid == "D79B8D77-BFFC-460B-9312-034F2877D35B"

    photos = photosdb.photos(
        from_date=datetime.datetime(
            2018,
            9,
            28,
            16,
            7,
            0,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
        ),
        to_date=datetime.datetime(
            2018,
            9,
            28,
            16,
            9,
            0,
            tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
        ),
    )
    assert len(photos) == 1
    assert photos[0].uuid == "D79B8D77-BFFC-460B-9312-034F2877D35B"


def test_date_invalid():
    """Test date is invalid"""
    # doesn't run correctly with the module-level fixture
    from datetime import datetime, timedelta, timezone

    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["date_invalid"]])
    assert len(photos) == 1
    p = photos[0]
    delta = timedelta(seconds=p.tzoffset)
    tz = timezone(delta)
    assert p.date == datetime(1970, 1, 1).astimezone(tz=tz)


def test_date_modified_invalid(photosdb):
    """Test date modified is invalid"""

    photos = photosdb.photos(uuid=[UUID_DICT["date_invalid"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.date_modified is None


def test_import_session_count(photosdb):
    """Test PhotosDB.import_session"""

    import_sessions = photosdb.import_info
    assert len(import_sessions) == PHOTOS_DB_IMPORT_SESSIONS


def test_import_session_photo(photosdb):
    """Test photo.import_session"""

    photo = photosdb.get_photo(UUID_DICT["import_session"])
    import_session = photo.import_info
    assert import_session.creation_date == datetime.datetime(
        2020,
        6,
        6,
        7,
        15,
        24,
        729811,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), "PDT"),
    )
    assert import_session.start_date == datetime.datetime(
        2020,
        6,
        6,
        7,
        15,
        24,
        725564,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), "PDT"),
    )
    assert import_session.end_date == datetime.datetime(
        2020,
        6,
        6,
        7,
        15,
        24,
        725564,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), "PDT"),
    )
    assert len(import_session.photos) == 1


def test_uti(photosdb):
    """test uti"""

    for uuid, uti in UTI_DICT.items():
        photo = photosdb.get_photo(uuid)
        assert photo.uti == uti
        assert photo.uti_original == UTI_ORIGINAL_DICT[uuid]


def test_raw(photosdb):
    """Test various raw properties"""

    for uuid, rawinfo in RAW_DICT.items():
        photo = photosdb.get_photo(uuid)
        assert photo.original_filename == rawinfo.original_filename
        assert photo.has_raw == rawinfo.has_raw
        assert photo.israw == rawinfo.israw
        assert photo.uti == rawinfo.uti
        assert photo.uti_original == rawinfo.uti_original
        assert photo.uti_raw == rawinfo.uti_raw


def test_verbose(capsys):
    """test verbose output in PhotosDB()"""

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB, verbose=print)
    captured = capsys.readouterr()
    assert "Processing database" in captured.out


def test_original_filename(photosdb):
    """test original filename"""
    uuid = ORIGINAL_FILENAME_DICT["uuid"]
    photo = photosdb.get_photo(uuid)
    assert photo.original_filename == ORIGINAL_FILENAME_DICT["original_filename"]
    assert photo.filename == ORIGINAL_FILENAME_DICT["filename"]

    # monkey patch
    original_filename = photo._info["originalFilename"]
    photo._info["originalFilename"] = None
    assert photo.original_filename == ORIGINAL_FILENAME_DICT["filename"]
    photo._info["originalFilename"] = original_filename


# The following tests only run on the author's personal library
# They test things difficult to test in the test libraries
@pytest.mark.skipif(SKIP_TEST, reason="Skip if not running on author's local machine.")
def test_not_visible_burst(photosdb_local):
    """test not visible and burst (needs image from local library)"""
    photo = photosdb_local.get_photo(UUID_DICT_LOCAL["not_visible"])
    assert not photo.visible
    assert photo.burst


@pytest.mark.skipif(SKIP_TEST, reason="Skip if not running on author's local machine.")
def test_visible_burst(photosdb_local):
    """test not visible and burst (needs image from local library)"""
    photo = photosdb_local.get_photo(UUID_DICT_LOCAL["burst"])
    assert photo.visible
    assert photo.burst
    assert len(photo.burst_photos) == 4


@pytest.mark.skipif(SKIP_TEST, reason="Skip if not running on author's local machine.")
def test_burst_key(photosdb_local):
    """test burst_key"""
    photo = photosdb_local.get_photo(UUID_DICT_LOCAL["burst_key"])
    assert photo.burst_key

    photo = photosdb_local.get_photo(UUID_DICT_LOCAL["burst_not_key"])
    assert not photo.burst_key


@pytest.mark.skipif(SKIP_TEST, reason="Skip if not running on author's local machine.")
def test_burst_selected(photosdb_local):
    """test burst_selected"""
    photo = photosdb_local.get_photo(UUID_DICT_LOCAL["burst_selected"])
    assert photo.burst_selected

    photo = photosdb_local.get_photo(UUID_DICT_LOCAL["burst_not_selected"])
    assert not photo.burst_selected


@pytest.mark.skipif(SKIP_TEST, reason="Skip if not running on author's local machine.")
def test_burst_default_pic(photosdb_local):
    """test burst_default_pick"""
    photo = photosdb_local.get_photo(UUID_DICT_LOCAL["burst_default"])
    assert photo.burst_default_pick

    photo = photosdb_local.get_photo(UUID_DICT_LOCAL["burst_not_default"])
    assert not photo.burst_default_pick


def test_is_reference(photosdb):
    """test isreference"""

    photo = photosdb.get_photo(UUID_IS_REFERENCE)
    assert photo.isreference
    photo = photosdb.get_photo(UUID_NOT_REFERENCE)
    assert not photo.isreference


def test_adjustments(photosdb):
    """test adjustments/AdjustmentsInfo"""
    from osxphotos.adjustmentsinfo import AdjustmentsInfo

    photo = photosdb.get_photo(UUID_DICT["adjustments_info"])
    adjustments = photo.adjustments
    assert isinstance(adjustments, AdjustmentsInfo)
    assert adjustments.asdict() == {
        "data": b"mW[\xb7\xa2:\xb3\xfd/\xbe\xda\xa3\x17((\xf4\x18\xdf\x03H\xc2E\xb9%\\\xc4\xb3\xce\x03\x02\x12.\x82\n\x1at\x8f\xfd\xdf\xbf\xb8\xba\xfb\xec\xdec\x1c\xde\x92\xaa\xcc\x9aU\t\xa9\x99\xbff\x8f\xe26T}gv\xa7~\xf6\xe3\xaf\xd9\xf1^\xb5\xb9s?\x1f\x8b\xdb\xec\xc7\x8c\x97\xf5\xf5r\xf6m\x96^.\xd1O\xbf\xf7\xe4\x8a\xff\xce}\xe7\x17\x1c3\x0c\x19)\xce)*\x1e\xd5O#\xffmvi\xd3\xf1\xd4\xdf\xce\xcc\xd3\xc5\xfb\xd9\xdf\xdff\xe7bL\xf3tL\xdf\xf8\xe7t\x18\x8b[\\\xe5#\x99\xfdXr\x0b\x81-\xa8.E[u\xc5?\x11\xd8\xba\xef\x02C\xff\xe9l\x14UI\xc6\xd9\x0f\x81[.\xbe\xcd\xfa[Utc:\xfe\x0c\xc7\xd0\xdf\xb1\xd2\xf1\xff\x163\x06i^\xdf\x87\xf1\xcc\xdc\x86\xd9\x8f\xff\xf9\xeb\xff\xf1(\xba\xf4\xd8\x16\xf9\xec\xc7x\xbb\x17,\x8bb\x1c\xab\xae\x1c\xde\x04\xfb\xd3\x89\rw}\x96\xb6\xbb\x9fq\xb9o\xbf&\r6n\xdfs\xc3\xd7d\xd5]\xee\xe3o\x9f\xefKn\xbd\x14\xc4\xe5\x8a\x93\x16\xc2ZX,\xe4\xdf\xab\xc0t\xe9\x87\xfb\xad\xf8\x03Hm\xd3\xac\xf1\xfa\xaa\xfb\x13]\xbd\xbd\xa1\xbab\xf8\x89>\xbcs\x1c\xc6*\xfbbu\xe1\x16\xef \x1c\xb7\x96\x84%\xbf\\/DA\xe6xy\xc5\xadY\xfdD\xee\xcb&K\xdcR^\xf0\xe2JZ-\xd6\x82\xc8I\xac\x12\xf7\xb1\x8f\xd2\xf6\xfe\x0e\xfe}!\x89+\xee\x8f\x8f\x15\xf3\xf8'\x11\x86\xbe\xe4\xe5\xf5J\xe4Y\xa5EYZ\xf0k\xf1\xdbl\xec\xbb\xb4EiW\x16\xbf\x82\x08\xe2j\xcd\t\xb2\xb4\\\x8bk\xf1\xbd}\x0b\xf1\xcb\xb2\x14\x17\xb2\xc0\xf3\xeb\x95\xb0\xe6DIZ,\x99I\x96\xde&Q\xfe\xf7\xc7\x88}\x95\xd1N/l\xb3at\xd9\xe6\xdc\xe5\x88\xa3\xc6\x8f\x15q\x8f\xf8\xc6\x89U'\x860\xb9\xda\x1b\xf7b\xc1\xf2\x18\xab\xe7;\xe4\x13Ro\x82\xb5%\x83\xaa\xe1\x0e\xc4\x8c-\xd8\xf2\x9e\x19\xe9m\x9c\xf2\xf9\x18\xc7r\x9a\xb5\xfcb\xbfl\xb5\xcf\x0fbQ\xad\r\xbd\xa8\xc9\x13\x0bf^\x84\x94\t\xaa\x073\x06$\xd1#\x07\xc4\xaa\xb5\x07m\x92\xc4\x1b\xdd\xb4\xd2\xd6I\xa6G\t\x97Jy\x0co4\xcc\xc5\x88\x8f\x0eC\xb4\xe0\x0fG\xfe2\xed\x8d\xe8T\xa8gM\xc3\x8d\x13Q1fD\xa2H\x831\xe2s#\xe2\xc8\x1e\xc3\x9c\xe1\xb6\x0c\xb7\t\xe2\xe6fz\xe9\xf0\xf8\xfc\x08\xd7\xa2\xc6\x0f\xdeAEcx>\x84)\x8c\xae\xd1\x83\x1b\x86Mm\xc5\xa7)k[Q\x80Op\xc0\xaa\xca\x80\x92c\xa46\x19\x08\x84\xd0\x00\xf9\x1eG\xc4b\x80\x07\xdc\xb6\xdb\x98\x1b\xb3\x00\xf2\xf6\xbe\x8aJt\x02\xce\xa6\x94[\xb7C\xf8\x14\xa1>\xd2/Q\xf3,??\xb6\\\x98!\xd2p\xa1\xd7\xbb\xa6j\x9d\xd0\x9c1\xa3\x9c\xa3\xbd\xec\xd4P\xe5\x04\xc3\xdf\x80\x97m\xdc\x8c\xc7/\xc0F,\x83\x05\xf4\x92\x92\xd3\xb5\xd8\xe7\x1fZ\xf4\xf9\x11\x19\xf6\xa2\xdc\xc0!\x12\xac\r?\xc5%L\xa5\x90\x12\x13C\xd5\x0c\xa3\t\xed\xdd\xb8\xc7\x11\xaa\xb6x\xab\x9aI\xf3\x8ba\xc3\xf6\x8e\x9f\x18 \x7f\xfa\x02$\xacV~\xe8\xc4\xad\xb5rt;\xcc\x91\xca;\xb2\xb2\xa7\x93\xdb\x81\xa7\x1f\x00b#\xad\xc9\xf6\x08e!\x8c\xca\x18?\xbd\xc2J\xb3\xea\x10^\xaa/\x82\xdc\x9b \xc3\x0b\x7f\xe1\xb5\xb0\xd1\xe2\xc4QK\xf1\x1ey\x02r\xc9\xd6\x02HA\x00\x99\x18t~\x98\xf3\xa2\x94$!\x8a&'\x82\x93\xbf\xe7P\xbe\x87\xe7\xb2\xfd\xfch\x96\x9f\x1f\xf8!\xff\xc30\xe4\x8b\xdf\x88\xe1\xdevsU\x1c\xbdk\xc96\x8b\xce\xe5mB\xaf=l\xb9\xb8s\x8e7^\\\xb2cD\xae\xefc\xd9\xf6\xfb\x18E7k\xa4\x97X\x9b\x9f\xf0]Y\xed\xc1\xa5\xfb\xaa!\xf7\xab\x86<l\xbde\xdf\x1fp\x1e\x9a\xb1\x99\x14jG\xf4s\x9f\x132\xef\x8d.\xa9m\x1c\x1fL\xbd\xd9?T\xb0\xc3\x9f\x1f\xd6\x96\x01\x1c\xf5\xa6\x8coj\xb1E)\xb1W\xcd\xeb\x10\xe4\xb2\xcbq\x9f\x1fy0w|\x9e7\x82p'\x04\xe5\xa4\x10\xedI\x91\x8b@\x0c\xe2\x81\xac'\xbf5_\xc3\x0b\x05H\xb79\xfb\xee\xa1q\x05\xfa\x88\xa56\x15\x10R\x0f(\x92\xab\xbd|\x84\xc8\x0e\x82\x81\xe2;\xd9J\xc6\xc5?f\x13}\xc0'\xf5\xfcR8i1\x87_\xca<\xd5(\xf5\x81\x1a>\xb5)\xb9x5\xef\xfaP\x91\x02\xed\x00\x1c\xa7\xbf6\xe1\x93B\xc8!\x8d2<\x02|\x80\x8c\x1e\xc4\nN\xc8Xou\xfb\xe2W\xc9\xc2|\xf9\xc7\xb4\x94oo\x1c\x9d\nX#\xbd\xa3Q\x0eCl\x16\xce\xb3a\xd9\xc8\x9b0\x18\xed\xddR\xb4\x1f\xaf+\x82j\x883\x04\xcf\xf0\x98\xc5t\xf2}\xfd\xe4xm\xab\xd6a\x1c\xde\x0e\xf8\xd0\x99\xe7KtT\xa31\xea\x14'\xf3\xb9\x9d\x86\xedt\x8b\xc1`\xe2\xbe\xb6kE\xb2_bV@Q4\xba\xa6|Vk\xdf\x16{O#\xd3\x11l\xa8g\xa2tm\xb8M\xb8\xa6\x82\xa9\xf9\x99WD\x8el\xb8y\x9c\xc1v\x02\x9d\xe2\xea>54\xc4\x9d\xed']\xee\xb4\xecfW\r\xb55n(\xf4\x8d\x9d\xec\xe9\xe3\xa4\xae6\xd66\xaa\x16j\x04\xe1\xa8`\xaa|~\x9c\xb4K\xef\x18>\x97\xb3\x04=\xb1\\\x9c4?q6H\xe6\xad\x8b\xe9\xe5\x94_j\x88\x01\xe3Ar\xb8\x90\xf3kG\xd9\xd5\xc3\xdd\xc5D\xda\xdf\x9d\xbal\nEOh\xd9U\xaf\xb3\xc1\x9b\x87\x0b\xe9pp:\xf7s\xfa\xf9!k~co\xc9\xee\xbc=\xd9\xaeD\x17\x08t\t\xceU\x93U\x88\xc3\xa6B\x91\xa5\r\x12\xae\xc7\xad\x0b\x92\x97\xaf\xeb\xca\xc1TV\xb5\x9en\"\xc1\xce\xab\xca\x9ao\xe5vs\xf3\xe5\xd1\x08\xedC\x80^km\x0e\x1c\x80\xfc\x00\x9at\x7fUwW\xb0\xf5#\x1d5\xa5\xb1\xf1s\x0bq\x9d\x86\x04g\xfbl\xc16,/h\xe3K\x9a\x00\xcf\x04^\xdd\x83\xec\xd4\x15\xfb[\xf5CHe\xd8yZ*\xf9W\xb5s\\;C\x13\xa2\x9d^\xdby\x82\xe8IG}\xa8W`\xb0j\xe5\xe6\xe0\x86\xb74\xff\xb4+\xb9-$\xb4\xddm\x86\xa7\xf6R<XJN\xd8\xb7\xe7J\xbf\xdb\xbb\x8bTw\x9bMnm\xedC\xab\x82\x01\xa8\x12\xf6\xc8\xba6p\xc6\x9aj\xf2\xb04\xb3\xde=\xc1k\xfb\xa2/\xa49\xd0\x0e\xfd\t\xa9\xe0\xc5\xae\x86\xbdNh\xb7\x05\x19\x06\x08\xc8 \xc8p\xcd\xeb^jEq3U\xae\xd1\xd3\xa2\x9f\x9a\x0b\xab\x93\xab\x95,\xaf\xa7];XX\xdb5\xf7\xf4jen\x06!\xf1\x83\x8b\xebE@\xc4\x94\xdf\x00\x9f\xdb\x9b\x1b\xfbaa\xe1\x9a\x92\xc8\xb1Z*\xe4H>oa\xd6\x1c\x9e\x88\xd7\x0f\\\xe0=]b\xc0\xc4\x06T:\x00\xd5\xce-l\x9e\x8d\xba'^\xe5(\xb6&\r\xdef\xe0vA\xd38%w\xd4\xd4\xcc\x86\xa8<\x1b\xb8\x19\xdc\xe7+\xb7l\xa5H7\x9f\x1f\x9e)\x84\xdd\x15G\x9e\xb1\x14B\xa2:\x1bm\x11z\x16\x95\xaf`\x1a\x12\xf3iwf\x15\x12\x0b\xfbw\xebE\x9f\xbe\x16iv\xc0\xdd]FL#\x99m\x12?d'\xa9\xf3\x02K\xd8\tM\xfd\xa8\xf2\x87\xed\xf4\xf7\xb6zB\xeb<\x90+\x19\x1f\xe0U\x1e\xdb\xa9-\xad\x8e\xbb\xd4\x15\xb8\x9aUYoqx\xb3\x96\xc3<\xa8y\xc7i\xc2\x97_\x8d\x0b\xad51+\x8c\x03\xf7\x8a\xbd\xa1R\xae\x83\xe1\xd4\xd4\x05\xeb\x10FY\x9dqT\xeen\xef\x8bw\x15\x80[\xe6e\xd3\xb8\x84:%5Y,\xe1\xb6\xef\xec*\xa7\x10daG\xa5\x07\xd8J\xfe\x86\xa8\x9e\x9e\xf5\x8e:\xd9Xk@\x98*B\xc8\xda\\\xecM25Rp~ME\x0ey\xe5\x18\xa1\xf6\xa2\x9f\x95\xb4F\xb06\xac&\xca\xa6'6;.\xa8H\xfe\x04\xad\x8dw\xea\x1e[n\x92\xac\x91\x12\x03\x7f@\x83\xcf\x19\x10%\xaeG\xec\x03\x14\xc2C\xa9\xa6\x8a\xde\xd2r\xc2\x81\x06\xd3&&\x9b\xb8\x85\x87d\x9f\x93C\xa3\t\xa6\xb3\xf7\xe5J[\x8c\xf9\x92\x8a\xaca\xf6N\xe4\x7f~\xa0\x9d\x9c\xe1\xfbt2!l\xfcM)\xed\xd9\x11\x0fu\x94\xabz$\x9c\x86\x89\xdca\x96\x8cu\xa5%\x86I\x8f\x15\xa9\x00\x10}tDQ\x0b\r\x13\x87>\x1f\x00Xz\xa9\xb2\xc84A\xc1\x13\x95\x1b\xd8\xd3KG\x9e;C\xe7\xc8\xb1\x94\x13\x8d\x96\xac\xd7r\x9e\x1e\xf5\xa4\xc4\xee\x1a\x8a\xc2\xbe$\x0f\x15\xf6\xe1\xfeL\x12Y7)k\xe3\x0e\x01K\xc1\xb3\xd1\x96\x80\xa2q'*\xde\xb5'\x13\t\x04\xae\xa04\xdc\xb8MLv\x17\x9f\xff\xfcx\xee\xe6\xc6\xb5t7\ngh\xe1p\x1d\xab\xfb\xd3b=kD\x16\x81\xfb>H'\xa7\xd78\x01\x17\xaa\xab\x02\xd1\x0e\x11\x02s\x80\x05\x8f\xdd\xa6;v\xabF\x90\xca>\xb8\x98~J\x9e\x0bm! \x7f\x82\x0b\xe0\x0c~\xad\x08\xecW\x0c]\xaf2\xac\xad\xe9G)\x95\xae\xe0\x9c\xb0}\x96(\xe8B/\xa4\xbc\x08\xf6\xe10 H@\x04\xfc\x145Gv\xd7\xd8\x9a2?\x82\xbd\x106\xc8\xe2uI\xc9\xee\xbe|\xd2T!H\xe9<c\xb7\xa7\xa3\"G\xd5G;{a\xd70\x85$\x08\x118\x81\xa8\xd97\xea$\x81\xde\x0f:\xe4\xdc\xb5\xaew\xacR\xa0\xa0\x1d\x9c\x04\xc55\x90l\x9c<\xbd (\xa0uW\x16\xa5\xa6\x84N\xed\xcfc\xed98*\xe5,\xa3m\x10xv\x08\xae\x92\x82\xado\xc0A\xf1v\xbe\xbc\xd5\xf7\xc0c\xdd\x12k\xcb\xd2;\x95\\\xa9-\xfb\xff0\xe9\xdf\xbe\x05\xb8\xf2\xa7|]\xfeK\xbcr\x1c\x93\x9e\x94Tc\xf1K\xbe\xf2o\xf9\xfa\x87\xfc}\xbfD\xf8\x9f\xc2\xf8\x1fI\xfcK\"\x7f\x9b\x11\xa6?\xb7\xc5\xf3m\x96\xb8\xd5R`\xb2\x9d\xe9vQ^I\xd2\xfa\xef\xdf\x8a|\xd3w\xe3\x8d=A\xfe\x10\xe9\x98\xa4yO\xdf\n\x9dyU9{bT\xa7\xea\xeb\xa9\x84\xcf\xe9m\x0c\xfa\xae\x98\xfd\xfd\xbf\x7f\xff\x17",  # noqa: E501
        "editor": "com.apple.Photos",
        "format_id": "com.apple.photo",
        "base_version": 0,
        "format_version": "1.5",
        "adjustments": [
            {
                "formatVersion": 1,
                "enabled": True,
                "settings": {
                    "offsetLocalLight": 0,
                    "offsetHighlights": 0,
                    "inputLight": 0.3073453608247423,
                    "offsetExposure": 0,
                    "offsetBlackPoint": 0,
                    "offsetBrightness": 0,
                    "statistics": {
                        "p02": 0.00784313725490196,
                        "p50": 0.09803921568627451,
                        "autoValue": 0.2856,
                        "blackPoint": 0.0031976514035982175,
                        "tonalRange": 0.09845670498375754,
                        "p25": 0.03529411764705882,
                        "p98": 0.6,
                        "lightMap": "FVpKd0pbSVkQWA5XR1kNWBNWFFYqMCOpJFgbWBmuF1YhjCT7J9Eik0ZhIWJFl1PIVGlWa1dtWW9acl12X3lD/hJwDlUPVkdYJFcPVRAxFBZIWEhYGVNEWBJXElYYWCGIJalNYxvgF3AgbUrwUd5V1VZsV21Zb1pxXHVfeBmDDSkNVw5WF1YVVDFWR1dHV0hXSFdIWElYGVkTWkrIPasv/U75D1sPZBRtUmZUaFVqVv0ssCjJWfxcll54FyEZSBBWR1YbVBkcET4UHEdXSVhJWElZSllKW0tcTF1MXiVgRfENCg9lOnRSfVRoVGpVkyg/K0UcRhk0UPoOIBJfR+dHVw0NDzMaHB9YSFhJWElZSlpKWktbTF1MXk5gT2FPYg0GDWQ1vDV/VHM2gCFsV4JC1xWgFa8UwhISFBIUVxRXOWoSVRiKSKBIYklZSllKWkpbS1xMXk1fT2FPYhBmDQUNWlJ6NGMUdRB1N9AXwxOnEyQTEhMRDkcXRRcUFVgWSyPeJaciZUpiSlpKW0tbTFxMXU1fT2FPYlFkDWYNBg5uVP4ROhKJERARERISEnQUd158YYURVxNVFxQX0RdXFmgl/k3/Sv9KWkpbS1xMXU1eT2FPYlFkUXMOdB5tPqgv/w+9KYwqoFl0WnNbr153X3lhq0pbSloXWRVrJtwpWD+fSuA6XEpnTF1MX05gT2FPY1FlP3ooZSdUIWIYeBnhGmodhh+oHnYjMSWZIGkXvBELS/JKXEpbGkgWrBeKRahM6kzZTd9O00/dT+NQ11HTUL4TgxAhDywROREWEWsh7xQlIzszRTRGM0MuPRt6EoVMXUxeFFwPEA8ODzQRRhLFEswSuhK8HpQbcxwvFywPQg4fDW0SzA+aDwwQEBUyDxYpPj1OQFA8TDZENNoqkUywFF0RDw8ODhEQERHoEWASYhtjKGMpQiY2IzQbag9rDwwQGw4SDhoNDw0SFSIeNyk9O09CUTtML35MvzqRFBUScRFmFbcWwxQQGfNPllBjUWUrZSZnImpVbBVtVnANcQ0LDSMaKSEsISojMjA8Mz5ceF55Hnkgyi7QM5oPDhxbECwPIRa7HOkU7w4IDQcPeVN9HOdWcFlxEnAOGQwHDR0mMyw3LDcrMikwMD0seGCMYXwvfB6CJKVi2BVFFtASwA/fDpoNHQ0dDwwP5g2fDQYNCR91JpIPdw13DRAOGSs8N0U0QjNALjsuOSh8XuNjgkeAGYwgnizmH1IZphnSTfmo+w/9DQkMKhLmKfMO8w2REnYSdBIRFB0SIAwRJDs8SjtKOEYzQGGAZIA6jGaCV4MdiiJ+K9lCrQ9tHUMZTRz7D+ENERQTFIwXqBLqEKQVGRkgHCQdJR0nDR4NKylEKUgpRCQ8D4FmhFqOZ9NjiBmDGZUw9FnPDa8QqBnNOMcRxRwnGjMdYRwfGRoUGiEsJjArNSk1JDQfLg0KFhwlLCsyDzAPFg8NUolmiGuMLp8jnCCdJKMZlBEsEB8SPh7jHSclLiYvJDIjLyEzKzwzRDNFMUQxRBEzEhMXGhwnKEcSERE9ETcSj1GPaJVWkxiOHoweoxkpFB0ODg0nDyMjNS47Mj0yPjA+ITUhQTpOPVE5Sw1CEQ0XICMvJS4qahVNJlw4dR9mKFckZyR1GZ0TPyOhHFYMEw8ZEBMdJSImHjohPiNAMD8sPCs0LTkkNg0bDBcMFRgmHSksOyzdJMAeaC/PI4UnqSVPH34UhBNCD2UPJw9qExsYIyMnIiUhJSQuJzwyQDVDMT0uOCMvDhcMIhQUDRAnPTJ4L4kjvidvMNouliyFJmshqhtvEzgblxlgJn0pjiEqIigjKSUrJ3s+Tj1NNkUzQit2DlISDg0NFXAMCw8dGEsfkje/KHgimSVgLrcXRR6TErcPcxt3FGwhjh23FKonMidwFEcUnw8vEK8QChBPGcoNBxMSDkEUaA4UElYWPx9wHaEmzxedF1AbVRlpGmAajRFjHJkVcxySIn0TihdyElMSLBXSJOYY7RAWEQsRsQ0HFRYOPhMZF4UZgBaAGlwgxSTDFakWhCWlFZYXdhZkD4INXQ9iD2td3w5yEZoNVQ/RL9cSuxfIFFkQCg8XDR4UGRdBGV4fsxhuFcYtjiDYHIwbihiEE5QRbRVlFHISUQ1TEFgPaA2cD4ASxw9kFowpnhyLHG0hbg9YDwgNCg0PGVohgSO7F54XghvBFoUXmhY9GIwWfxNhE34PMRKhEekOxw5uDykNVhF6F8sr0CWhLpQ1/yL+HqgOCA0HDUsqtiuyJYYUtRJhFXoTaxNoD04SeBOBE5MURRE+ES4PDw0LDhoVFw9QEpIQahy2D24RQxF2ENsQjA4JDQUOPiHJKIQVaw8qEmYSVg8wEnUPUw15EXUssRFhEVEQaRkbEnYMDA+bEX4UkRJ1G8AcuQ9fDB4Taw+cDQcNBRNBGtMczSOHI4YTUREfEVkXkBx8EoQTnRNuDnoNJg4wElsNYRWjE8MSYyPTTeFJuA2gDAUNjQ+WDysNBw0JHlkREynRF6YenRNkEZAPLQ9KGXEPnhGSD3gPfg0gD3o=",  # noqa: E501
                        "localAutoValue": 0.36000000000000004,
                        "whitePoint": 1.003921568627451,
                        "p10": 0.01568627450980392,
                        "highKey": 0.8063460882459689,
                    },
                    "offsetContrast": 0,
                    "offsetShadows": 0,
                },
                "identifier": "SmartTone",
            }
        ],
        "metadata": {
            "masterWidth": 3024,
            "pipelineVersion": "OSX.4",
            "masterHeight": 4032,
            "orientation": 1,
        },
        "orientation": 1,
        "adjustment_format_version": 1,
        "version_info": {
            "buildNumber": "19G73",
            "appVersion": "161.0.120",
            "schemaRevision": 1,
            "platform": "OSX",
        },
        "timestamp": "2020-10-03T22:54:20+00:00",
    }


def test_no_adjustments(photosdb):
    """test adjustments when photo has no adjustments"""

    photo = photosdb.get_photo(UUID_DICT["no_adjustments"])
    assert photo.adjustments is None


def test_exiftool_newlines_in_description(photosdb):
    """Test that exiftool handles newlines embedded in description, issue #393"""

    photo = photosdb.get_photo(UUID_DICT["description_newlines"])
    assert photo.description.find("\n") > 0
    exif = ExifWriter(photo).exiftool_dict()
    assert exif["EXIF:ImageDescription"].find("\n") > 0


@pytest.mark.skip(reason="Test not yet implemented")
def test_duplicates_1(photosdb):
    # test photo has duplicates

    photo = photosdb.get_photo(uuid=UUID_DICT["duplicates"])
    assert len(photo.duplicates) == 1
    assert photo.duplicates[0].uuid == UUID_DUPLICATE


def test_duplicates_2(photosdb):
    # test photo does not have duplicates

    photo = photosdb.get_photo(uuid=UUID_DICT["no_duplicates"])
    assert not photo.duplicates


def test_compound_query(photosdb):
    """test photos() with multiple query terms"""
    photos = photosdb.photos(persons=["Katie", "Maria"], albums=["Multi Keyword"])

    assert len(photos) == 2
    assert UUID_DICT["multi_query_1"] in [p.uuid for p in photos]
    assert UUID_DICT["multi_query_2"] in [p.uuid for p in photos]


def test_multi_keyword(photosdb):
    """test photos() with multiple keywords"""
    photos = photosdb.photos(keywords=["Kids", "wedding"])

    assert len(photos) == 6


def test_multi_album(photosdb):
    """test photos() with multiple albums"""
    photos = photosdb.photos(albums=["Pumpkin Farm", "Test Album"])

    assert len(photos) == 3


def test_multi_uuid(photosdb):
    """test photos() with multiple uuids"""
    photos = photosdb.photos(uuid=[UUID_DICT["favorite"], UUID_DICT["not_favorite"]])

    assert len(photos) == 2
