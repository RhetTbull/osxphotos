from collections import namedtuple

import pytest

import osxphotos
from osxphotos._constants import _UNKNOWN_PERSON

PHOTOS_DB = "tests/Test-Ventura-dev_preview-13.0.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-Ventura-dev_preview-13.0.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-Ventura-dev_preview-13.0.photoslibrary"

PHOTOS_DB_LEN = 16
PHOTOS_NOT_IN_TRASH_LEN = 14
PHOTOS_IN_TRASH_LEN = 2

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

# Photos 5 includes blank person for detected face but looks like these aren't in Photos 7?
PERSONS = ["Katie", "Suzy", "Maria"]

ALBUMS = [
    "Pumpkin Farm",
    "Test Album",  # there are 2 albums named "Test Album" for testing duplicate album names
    "AlbumInFolder",
    "Raw",
    "I have a deleted twin",  # there's an empty album with same name that has been deleted
    "EmptyAlbum",
    "2018-10 - Sponsion, Museum, Frühstück, Römermuseum",
    "2019-10/11 Paris Clermont",
]

KEYWORDS_DICT = {
    "Kids": 4,
    "wedding": 3,
    "UK": 1,
    "England": 1,
    "London": 1,
    "United Kingdom": 1,
    "London 2018": 1,
    "St. James's Park": 1,
    "flowers": 1,
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

PERSONS_DICT = {
    "Katie": 3,
    "Suzy": 2,
    "Maria": 2,
}

ALBUM_DICT = {
    "Pumpkin Farm": 3,
    "Test Album": 2,
    "AlbumInFolder": 2,
    "Raw": 4,
    "I have a deleted twin": 1,
    "EmptyAlbum": 0,
    "2018-10 - Sponsion, Museum, Frühstück, Römermuseum": 1,
    "2019-10/11 Paris Clermont": 1,
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
    "7783E8E6-9CAC-40F3-BE22-81FB7051C266": "public.heic",
    "1EB2B765-0765-43BA-A90C-0D0580E6172C": "public.jpeg",
    "4D521201-92AC-43E5-8F7C-59BC41C37A96": "public.jpeg",
}

UTI_ORIGINAL_DICT = {
    "8846E3E6-8AC8-4857-8448-E3D025784410": "public.tiff",
    "7783E8E6-9CAC-40F3-BE22-81FB7051C266": "public.heic",
    "1EB2B765-0765-43BA-A90C-0D0580E6172C": "public.jpeg",
    "4D521201-92AC-43E5-8F7C-59BC41C37A96": "public.jpeg",
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

# HEIC image that's been edited in Big Sur, resulting edit is .HEIC
UUID_HEIC_EDITED = "7783E8E6-9CAC-40F3-BE22-81FB7051C266"
PATH_HEIC_EDITED = (
    "resources/renders/7/7783E8E6-9CAC-40F3-BE22-81FB7051C266_1_201_a.heic"
)

# file is reference (not copied to library)
UUID_IS_REFERENCE = "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"
UUID_NOT_REFERENCE = "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"

UUID_MOMENT = {
    "3DD2C897-F19E-4CA6-8C22-B027D5A71907": {
        "uuid": "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
        "location": (-34.91889167000001, 138.59686167),
        "title": "Adelaide",
        "subtitle": "",
        "start_date": "2017-06-20T17:18:56.518000+09:30",
        "end_date": "2017-06-20T17:18:56.518000+09:30",
        "date": "2017-06-20T17:18:56.518000+09:30",
        "modification_date": "2020-04-06T15:22:24.595584+09:30",
    }
}


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_init1():
    # test named argument
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_init2():
    # test positional argument
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_init3():
    # test positional and named argument (raises exception)
    import osxphotos

    with pytest.raises(Exception):
        assert osxphotos.PhotosDB(PHOTOS_DB, dbfile=PHOTOS_DB)


def test_init4():
    # test invalid db
    import os
    import tempfile

    import osxphotos

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
    import osxphotos

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
    assert photosdb.photos_version == 8


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
    import datetime

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
    assert sorted(p.albums) == ["Pumpkin Farm", "Test Album"]
    assert p.persons == ["Katie"]
    assert p.path.endswith(
        "tests/Test-Ventura-dev_preview-13.0.photoslibrary/originals/D/D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg"
    )
    assert not p.ismissing


def test_attributes_2(photosdb):
    """Test attributes including height, width, etc"""
    import datetime

    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.keywords == ["wedding"]
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
    assert sorted(p.albums) == ["AlbumInFolder", "I have a deleted twin"]
    assert p.persons == ["Maria"]
    assert p.path.endswith(
        "tests/Test-Ventura-dev_preview-13.0.photoslibrary/originals/E/E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51.jpeg"
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


def test_path_edited_jpeg(photosdb):
    # test a valid edited path
    import os.path

    photos = photosdb.photos(uuid=["E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"])
    assert len(photos) == 1
    p = photos[0]
    path = p.path_edited
    assert path.endswith(
        "resources/renders/E/E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51_1_201_a.jpeg"
    )
    assert os.path.exists(path)


def test_path_edited_heic(photosdb):
    # test a valid edited path for .heic image
    import pathlib

    photo = photosdb.get_photo(UUID_HEIC_EDITED)
    assert photo.path_edited.endswith(PATH_HEIC_EDITED)
    assert pathlib.Path(photo.path_edited).is_file()


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
    import sqlite3

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
    import os
    import os.path
    import tempfile

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
    import os
    import os.path
    import tempfile
    import time

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
    import os
    import os.path
    import pathlib
    import tempfile

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
    import os
    import os.path
    import pathlib
    import tempfile
    import time

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
    import os
    import os.path
    import tempfile

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
    import os
    import os.path
    import pathlib
    import tempfile
    import time

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
    import os
    import os.path
    import tempfile

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
    # should return empty list
    import os
    import os.path
    import tempfile

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["missing"]])

    assert photos[0].export(dest) == []


def test_export_9(photosdb):
    # try to export edited file that's not edited
    # should raise exception
    import os
    import os.path
    import tempfile

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
    import os
    import os.path
    import tempfile
    import time

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
    import os
    import os.path
    import tempfile
    import time

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
    import os
    import os.path
    import pathlib
    import tempfile

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
    import os
    import os.path
    import tempfile

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


def test_export_14(caplog, photosdb):
    # test export with user provided filename with different (but valid) extension than source
    import os
    import os.path
    import tempfile
    import time

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


def test_eq(photosdb):
    """Test equality of two PhotoInfo objects"""
    import osxphotos

    photosdb2 = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos1 = photosdb.photos(uuid=[UUID_DICT["export"]])
    photos2 = photosdb2.photos(uuid=[UUID_DICT["export"]])
    assert photos1[0] == photos2[0]


def test_eq_2(photosdb):
    """Test equality of two PhotoInfo objects when one has memoized property"""
    import osxphotos

    photosdb2 = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos1 = photosdb.photos(uuid=[UUID_DICT["in_album"]])
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
    import datetime

    photos = photosdb.photos(uuid=[UUID_DICT["favorite"]])
    photo = photos[0]
    photo2 = eval(repr(photo))

    assert {k: str(v).encode("utf-8") for k, v in photo.__dict__.items()} == {
        k: str(v).encode("utf-8") for k, v in photo2.__dict__.items()
    }


@pytest.mark.usefixtures("set_tz_pacific")
def test_from_to_date(photosdb):
    import datetime as dt

    photos = photosdb.photos(from_date=dt.datetime(2018, 10, 28))
    assert len(photos) == 7

    photos = photosdb.photos(to_date=dt.datetime(2018, 10, 28))
    assert len(photos) == 7

    photos = photosdb.photos(
        from_date=dt.datetime(2018, 9, 28), to_date=dt.datetime(2018, 9, 29)
    )
    assert len(photos) == 4


def test_date_invalid():
    """Test date is invalid"""
    # doesn't run correctly with the module-level fixture
    from datetime import datetime, timedelta, timezone

    import osxphotos

    # UUID_DICT["date_invalid"] has an invalid date that's
    # been manually adjusted in the database
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["date_invalid"]])
    assert len(photos) == 1
    p = photos[0]
    delta = timedelta(seconds=p.tzoffset)
    tz = timezone(delta)
    assert p.date == datetime(1970, 1, 1).astimezone(tz=tz)


def test_date_modified_invalid(photosdb):
    """Test date modified is invalid"""
    from datetime import datetime, timedelta, timezone

    # UUID_DICT["date_invalid"] has an invalid modified date that's
    # been manually adjusted in the database
    photos = photosdb.photos(uuid=[UUID_DICT["date_invalid"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.date_modified is None


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
        "data": b"mW\xdb\x92\xa3:\xb2\xfd\x17\xbfVG\x97\xc0`CG\xcc\x03 \x89\x9b\xc1 n\xc6S\xf3\x80\x01s5`\x83\x0b\xec\x1d\xfb\xdf\x8f\\\xdd}vO\xc4\xf0\x862\xb5r)%e.\xfd\xb5\xfa\xccoc\xd5wzw\xeeW?\xfeZ\x9d\xeeU\x9b\xd9\xf7\xcb)\xbf\xad~\xacX \xf1k\x81KW\xdfV\xc90\x84?]\xe9\xf8\x9a\x01\xdf\x99\xef\x0c\x03\xa8aL\xcb\xfc\x92\x90\xfc\xb3\xfaid\xbe\xad\x866\x99\xce\xfd\xedB=\xf7\xdea\xf5\xf7\xb7\xd5%\x9f\x92,\x99\x92W\x88K2N\xf9-\xaa\xb2\xa9\\\xfdX\x03\x96\xa3\x13\xaa!o\xab.\xff'\x02\x9d\xf7\x9d\xa3\xe8?\x9d\xb5\xbc*\xcai\xf5\x83\x03k\xf6\xdb\xaa\xbfUy7%\xd3\xcfp\x14\xfd\x15+\x99\xfe\x7f2e\x90d\xf5}\x9c.\xd4m\\\xfd\xf8\xf7_\xff\xc3#\xef\x92S\x9bg\xab\x1f\xd3\xed\x9e\xd3U\xe4\xd3Tu\xc5\xf8\"\xd8\x9f\xcf\xf4w\xd7\xa7I\xbb\xfb\x19\x17|\xfb5\xa8\xd1\xff\xf656~\rV\xddp\x9f~\xfb|g\x84\r\x107<\xe08\xb0\x05<\xc3\n\xbfg\xa1e\xe8\xc7\xfb-\xff\x03Hn\x93\xb4q\xfa\xaa\xfb\x13]\xbe\xbd\xa0\xba|\xfc\x89>\xbe\xd68NU\xfa\xc5j\x00\xec+\x08\x00[\x81[3\xeb-\xcbs\"`\xc4\r\xd8\xd2\xfc\xf1\xe0\xcb&\n`-\xb2\x0c\xbf\x116\xec\x96\xe3\x01e\x90\xdc\xa7>L\xda\xfb+\xf8wV\xe07\xe0\x8f\x8f&\xf3\xf4'\x11\x8a\xbef\xc4\xed\x86gh\xa6yQ`\x99-\xffm5\xf5]\xd2\x92\xa4+\xf2_A8~\xb3\xd9\xf2\x80\x05\x94\x05\xcbR\x8f\x81\xe5\xbfLk\x9e\x159\x86\xd9n8\x9a\x00A`\xd7\xd4$\n/\x13/\xfe\xf7G\x99}\xe5\xd1J\x06\xba\xdb\x18\x0ff\x06\x86\x93\x176n$\xf1\x07\xc24v$\xdb\x11\xc6\xf1`)\xe6`\xe0\xe2\x14\xc9\x97;f\xe2\xb2V\xfc\xad1\xa1\xaa\x01a\xa9G\x06n\x19G\x0f\xd56J\x98l\x8a\"1I[\x86=\xac[\xf8\xf1\xbe\xe0\x19\xb6\x81\x136Yl\xe0\xd4\t\x894\xa3\xe5\xa8G\xa8\x8c\xd5\xd0F\x91l\x1cP\x18\xc7\x91\xa2\xeaF\xd2\xda\xf1\xf2Y\xe0\xb5T\x9c\x82\xdb\x1cdb\xc8\xb4\xc71d\x99\xe3\x89\x19\x96\x83\x16\x9es\xf9\x02\xa1\xd7\xd8\xe1\xccG\xb8\x8d\x83\x10\xe2\x880\x99\x16\x82\xf2\xe0\xe1\x8c\xe2\xb6\x14\xb7\xf1\xa3\xe6\xa6;\xc9\xfc\xf9\xf1\x1el7\xb0\x1d\x9d\xa3L\xa6\xe0r\x0c\x12\x1c^\xc3O\xee6zg3:/i\xdb\xf2\x1c~\xa0#\x99E\n\x14'\xa1\xdc\xa4\xc8\xe7|\re\x07/,\r\nx\xf4\xda\xd6\x8c\xc0\x94\xfa\x98\xb1\x0eUX\x903\xb2\x95Bl\xed\x8ex\xe7\x90\xf4\xa1:\x84\xcd\xa3\xf8x7A\x90\x92\xb2\x01\x81\xd3\xefu\xd98\x937\xcal\x06\x16\xac\xadD\x93\xc5\xd8\xc3\xbf\x01\x073j\xa6\xd3\x17`\xc3\x17>\x8b\x9d\xb8\x00*\x8c\\\xe6\x13\x92\x8f\xf7P\xb3\xd8B\xc1c\xc8\x19\n\xb3x\x05>I\xfe\\\xea\x1e\x96\xf5 \\\xc8a\x1f\xf5$$\x95\xe9\x99\xb2\x1e7\xbf\x186t\xef\x98\x85\x022\xe7/\xc0\x92\xe6\xca\r\xec\xa856\xb6j\x05\x19\x91\x19[\x94\x0e\x8b\xbc\xefP\xe5\xfa\xa8\xb4\\\xd8\xc4\x07\"\xa7\x01\x0e\x8b\xd0{8g\xc3L\xabc0T_\x04\xc1\x8b \xc5\x0b~\xe1\xb5\xb8\x81Ql\xcb\x05s\x0f\x1d\x8e\xec\x89i I \x88\xe8\x1e\xea\xdc cx!\x8e\x037\\\xec\x90N\x8b@\x99\x1d\xf0\xa5h?\xde\x9b\xf5\xc7\xbb\xf7)\xfe\xc30`\xf2\xdf\x88\xc1\xc1\xb23\x99\x9f\x9ckA7k~\x13\xcdx\xbe\xf6\xb8\x05Qg\x9fF\xcc\xaf\xe91*\xaf\xafc\xd9\xf6QD\xc8\xcd\x98\xe6!\x82og\xef.m\x0eh\xe8\xber\x08~\xe5\x90\xc1\xad\xd3\xf5\xdd\xd1\xcb\x02=\xd2\xe3\\\xeeJ\xf5\xd2ge\xf9\xd6k]\\[^t\xd4\xd8&\xfa\x94\xa5\x9d\xf7\xf1n\x9b\x14\xe0\xa46Ex\x93\x13\x93$\xa5\xb5i\x9eG?\x13\xf7\x0c\xfax\xcf\xfd7\xe2\xb2X\xf3\x83\x1d\xe7\x15\xb3P\xc2\xc7L\xf62\x8aP4\x96\xdb\xc5m\xf4\xe7\xf8$>Mm\xa3\xdf\x1dy\xd8\xa0>\xa4K[r\x8cg\x07\xce\xc2\x1e>]\x97\x94;\x8c\xd2\xd9\xbb/\xa6\xa8\r\xee)]\xe6;~\xcc\x8e\xebrg\x18\x01\xef)\xbd%p\x9e\x1d$\x07\x0f\xb8\xc4\x83\xe33{\x17K\x82\xf7\x0c\x91m\xf7\xd7&x,\x18\x03\x17\x16\x14\xafD\xd4O\x1bP$yq9\xd5\x06k\xf5n\x15\xb0\xfa\xd3:%\x85x\x83\xc5\xec\xaa\x05G \xe9m8\x03\x0f{znW\x8d\xb8\x07\xa2\x12\xc0\xc9\xda\xadyk\x86W\x82\x96\xc0K\t\xbe\xe0]\x1a.\xb2\xeb\xaag\xdbi[\xb9\x0e\xa2\xe0v\xf4\x8e\x9d\x1e\r\xe1I\x0e\xa7\xb0\x93\xec\xd4\x05;\xe8YGSA7]\xe9k\xcb\x97\x04\xabf\xd2\x1c\xf3\xbc\xd65\xe7G\xb5u\xad\xa1w`\xb9\x9c\x902;:\x89\xb6\xda\xbe\t\x04\th\xd0M\x9d<\xb4Em\x9fE)n\x17\xd4I{U\x9a5H\xc0\xc5z\xcck\xf3\x19\xdf\xac\xaa\x99-\x08n\xb9\xaaX\xf1a\xfe<\xcb\x1b\xc50\xc3\x8a\x95C\x84'\x89\xcc\xd2\xc7{\x01\x8f\xbd\xad\xb9 \x83\xc5\xe8\xf0\x05{~\x9dj\x85\xf0\x8c1\xe8N63kH$[\xf5F\xc1n\\\xe0\xd6\xfa\xc7\xfb\xae\x1e\xef{%\x13\x0ew\xbb.\x9aHR\xf5\xb9\xe8\xaa\xe7Ek\xf5\xe3Pv\x9e\x7f\xbe\xf6\x1f\xef\x14Z\x84Rc\x99d\xd7\x99g\xcb\x16f\x96\xa0.\xf62Y\xa79\x02\x9e.\xcd.\xdd\xe3\xad\xe7O\xe6\x1e\x05O\x87U\xa5\xa3.\xf1\xb5\x9a(!geUe\xbc\x99b+\xdf\\q\xd2\x02\xeb\xe8\x93\xa7\x00\xdf\x90\x8dd\xd7\xc3\xfa|\xb8\xca\xbb\x1b\xdc\xb8\x81J\x9aBS\xac\xcc\x90\xe7\x0b]\xbbm>Zd\x06\xc5@\x14K\x80\x1c\xbe\x94\xf8\xba?\x8a\xa4\xae\xe8}U\x8f\xc1,\xe2\xce\x81\x89\xe0^\xe5\xda\xde[\x85\xbb\x90\xb9Sk+\x8b\xc9|\xa6X\x81\xeaI7\xa3\x96\xae\xb6\xd70\x06\xb4\xf2]\x01LL\xe6\xd6|\x8c\x0f\xf8\x10\x1c\\\x08v\xd0\xb7\x97J\xbd[\xbbA\xa8:E\xc9\x0c\xd3:\xb62\x1a\x91,xN\xb9\xae5/mvU\xf0i@\xbd\xde=\xd0\xd3|\xceO\x02ml\x054\x9c,=Q\xa9\x1fT2_\x0c\x90z\x88 \x11\xc1\xd4\xab\x19\xd5I\x8c0j\x96j\xaf\xf5s\xde/\xc5@\xf3d\xc3\x02\\\xe0C\xafm\x8f\xdbZ>X\x1cOx\xd3\xfd\xa0t\xfda\xef\x84\x12\xe7\xcd\x8c\x8c\\p\xd0\x15\xebnx\xdc\x90\x94\xa1m\xb43\x97\x11\xf1b\xe2\xb49>lF=\x02\xcf\xa9\xccReb\x0b\xcd\xc2\x11\xc9Vjx\xfaE\xf3\xfb\xd2\xa9\xac\x8fw\x0b\n\xa3\xa3\x8c`\xe7\x17\xb5\xed\xce'e\x89w\x98\x14\x17\xcd+\xc6\xfd\xe3\x99\x19\x96\x94'\xca\xd6\xd1\xb9\xa0\xbbz\xc4\xd1\xd6\\P\xca\xb6\x02\xd9`o\xcc\xe2\x15-c\xacW\xd6E\xaf\x82\xd2\xf0(\x91\xe7\xfcpa\x08)\xe1i\xaf\xe8\x9f\xb0L-\x9d\xb8>\x94\xa5\xce\xf1\rn\xc75\xf5\xe7\xe3\xf8i\xd9\xe3\xd4Vwl\\\xc6\xe2Z\x0e\x9f\xa8.N\xed\xd2\x16F\x07\x86\xbaB\x83^\xa5\xb5\xa9\x047c=\x8a~\xcd\xd8v\x10<\xddjba\xab{\xf4B\xda\xf8 Y\xca,d\x18\x8c\xe7\xa6Nh\x8f\xd0\x8a\xea\xe2\x85\xc5\xee\x96\x1e\x08\xd9\xf8\xe8V8\xe92\xad\xb1:\x97u\xc9\xae\xb19^\xac*\x9bi\xd9\x08\xbaY\xb8\xa3\x9d\xe4\xd2f\xb3W\xd3\xd1\x96\x17\n\xda\xa0 \x91\xb8\x806\xba\xd0Y\xc4Y3\xd1\x05\xc8y\x86\x19\xe9\x14\xca\xed\xa0^\xa4\xa4&r\xad\x19M\x98.\x0fO\xef\x80_\x95\xd9\x03\xb5\x16\xd9\xc9\xbeg\xec\xd3x\xeb\n\x11r{2\x16@\xc3r\xb0w\x88~\xc4\\p,\xe4DR\xc3\xb9X<\x07\xe2\xa4\x89J%j\xf11\x8e\xb22l \xa7\xdb\x07W\xac\xe0e\xca\xd63O[fo\x87\xee\xc7;\xd9\x89)-o'\x1d\xe3\xc6Q(0=\xe2\x81*\x1fe5\xe4\xce\xe3R\xdeq\x9aNu\x05cM\x9f\x93\xaa\xcc\x11\xe2]\xf7D\xc2\x16\xadu/p\x19\x0f\xe1\xc2I$6\x85\x9cD\x1e\x12\xdf\xe0~\x1e\xba\xf2\xb1\xd3TP\x9e\n1\x86Ea+.p\xd4\xb0/\x0bo\xbf\xc5<w(\xca\x9b\x8c\xfb\xe0p)c\x91^n\xda\xc8\x8d\x12u\x9cc\xc9f\x89\xf2fOq\xee\xf0AeB)o\xb00^\x81\xe2\x95\xbb\xa3\xcb|\xbc?v\x1f\xef\xda\xb5\xd8+\xaf\x02\x15\x8c\xc3T\xdd\x1f\x06m[Si\x94\xf8\xd0\xfb\xc9b\xf4\x10\x00\x92\xcb\xb4\xd4\xf3V@d\xf4\x86\x14@\x0b:-\x84\xa4\tq!\xbat\xd7\xdd\xa4|\xb0\x90\xe5\\\xb7\xc4,\x14G\xb7\x968\x9d\xd6\xa5\xbdSi\xa6\xa9\xbbA2\x0bW\x14\xc5t\xa3\x85\x19u\x81\x13\xcc\x0c\x8f\x0e\xc1m$\xb8DXr\x12\xd2$\xb4\xd8\xd0\xb3\xf1vB\x1a\x174\xc4`\xd4QJ\xef\xaex\x862\xf0\x92\xf9-\x85.\xed\xb6\xc4\x90\xd5\xc9M\x9f\x95\xa9\xe9\\\xec\x07\x04\x9dQ\xd8\x1c\x1ay\x11P\xef\xfa\x1d\xb1\xef\xf0\xd0\xdb\x86\xcb}\xa2p\xb4c\x12\xd5Hp\xbd\xf8\xb1\x0b\xfc\x1c\x1bw\x97-\xa0\xe4\xda\xb5\xfb\x16\xc1\x07=B\x05\xd0\xb5\xb6!\xa8\xea\x08\xde\xc4\x19\x9d\xdf Crv\xaeh\xaa\x07\xe4\xd0\x86\xe9\xc1u\xe1\x9c\x0bP\xc0u\xff/*\xff\xdb\x97\x08\x97\xfe\x94\xb0\xeb\r\xcb\xfd)a7\xdfVsYM\xf9/\t\xcb\xbc$\xec\x1f\x12\xf8\xf5\x1aa~\x8a\xe3\x7fd\xf1/\x99\xfcmUR\tj\xe6\x8f\x97Y\x00\x9b5\xb7y\xf9\xb0T\xc4\xb3\xfc\xe6\xef\xdf\xaa\\\xe9\xbb\xe9F\x9f!\x7f\x08u\xafL\xb2~~\xa9t\xeaUe\xf4\x99Q\x9d\xab\xaf\x17\x93wIn\x93\xdfw\xf9\xea\xef\xff\xfc\xfd\x7f",  # noqa: E501
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
                    "inputLight": 0.18609650440705128,
                    "offsetExposure": 0,
                    "offsetBlackPoint": 0,
                    "offsetBrightness": 0,
                    "statistics": {
                        "p02": 0.00784313725490196,
                        "p50": 0.09803921568627451,
                        "autoValue": 0.2856,
                        "blackPoint": 0.0031976514035982175,
                        "tonalRange": 0.09845667502037223,
                        "p25": 0.03529411764705882,
                        "p98": 0.6,
                        "lightMap": "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",  # noqa: E501
                        "localAutoValue": 0.36240000000000006,
                        "whitePoint": 1.003921568627451,
                        "p10": 0.01568627450980392,
                        "highKey": 0.8063461568209626,
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
            "buildNumber": "20A5384c",
            "appVersion": "310.1.110",
            "schemaRevision": 1,
            "platform": "OSX",
        },
        "timestamp": "2020-10-04T06:00:14+00:00",
    }


def test_no_adjustments(photosdb):
    """test adjustments when photo has no adjustments"""

    photo = photosdb.get_photo(UUID_DICT["no_adjustments"])
    assert photo.adjustments is None


@pytest.mark.parametrize("info", UUID_MOMENT.values())
def test_moment(photosdb, info):
    """test PhotoInfo.moment"""
    photo = photosdb.get_photo(uuid=info["uuid"])
    assert photo.moment_info.title == info["title"]
    assert photo.moment_info.asdict()["title"] == info["title"]
    assert photo.moment_info.subtitle == info["subtitle"]
    assert photo.moment_info.location == info["location"]
    assert photo.moment_info.start_date.isoformat() == info["start_date"]
    assert photo.moment_info.end_date.isoformat() == info["end_date"]
    assert photo.moment_info.date.isoformat() == info["date"]
    assert photo.moment_info.modification_date.isoformat() == info["modification_date"]
