import pytest

from collections import namedtuple

from osxphotos._constants import _UNKNOWN_PERSON


PHOTOS_DB = "tests/Test-10.16.0.1.photoslibrary/database/photos.db"
PHOTOS_DB_PATH = "/Test-10.16.0.1.photoslibrary/database/photos.db"
PHOTOS_LIBRARY_PATH = "/Test-10.16.0.1.photoslibrary"

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
]
KEYWORDS_DICT = {
    "Kids": 4,
    "wedding": 3,
    "flowers": 1,
    "England": 1,
    "London": 1,
    "London 2018": 1,
    "St. James's Park": 1,
    "UK": 1,
    "United Kingdom": 1,
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
}  # Note: there are 2 albums named "Test Album" for testing duplicate album names

UUID_DICT = {
    "missing": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "favorite": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "not_favorite": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "hidden": "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
    "not_hidden": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "has_adjustments": "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
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


def test_db_len():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    # assert photosdb.db_version in osxphotos._TESTED_DB_VERSIONS
    assert len(photosdb) == PHOTOS_DB_LEN


def test_db_version():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    # assert photosdb.db_version in osxphotos._TESTED_DB_VERSIONS
    assert photosdb.db_version == "6000"


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
    assert keywords["wedding"] == 3
    assert keywords == KEYWORDS_DICT


def test_persons_as_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    persons = photosdb.persons_as_dict
    assert persons["Maria"] == 2
    assert persons == PERSONS_DICT


def test_albums_as_dict():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    albums = photosdb.albums_as_dict
    assert albums["Pumpkin Farm"] == 3
    assert albums == ALBUM_DICT


def test_album_sort_order():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    album = [a for a in photosdb.album_info if a.title == "Pumpkin Farm"][0]
    photos = album.photos

    uuids = [p.uuid for p in photos]
    assert uuids == ALBUM_SORT_ORDER


def test_album_empty_album():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    album = [a for a in photosdb.album_info if a.title == "EmptyAlbum"][0]
    photos = album.photos
    assert photos == []


def test_attributes():
    import datetime
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["D79B8D77-BFFC-460B-9312-034F2877D35B"])
    assert len(photos) == 1
    p = photos[0]
    assert p.keywords == ["Kids"]
    assert p.original_filename == "Pumkins2.jpg"
    assert p.filename == "D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg"
    assert p.date == datetime.datetime(
        2018, 9, 28, 16, 7, 7, 0, datetime.timezone(datetime.timedelta(seconds=-14400))
    )
    assert p.description == "Girl holding pumpkin"
    assert p.title == "I found one!"
    assert sorted(p.albums) == ["Pumpkin Farm", "Test Album"]
    assert p.persons == ["Katie"]
    assert p.path.endswith(
        "tests/Test-10.16.0.1.photoslibrary/originals/D/D79B8D77-BFFC-460B-9312-034F2877D35B.jpeg"
    )
    assert p.ismissing == False


def test_attributes_2():
    """ Test attributes including height, width, etc """
    import datetime
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
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
        "tests/Test-10.16.0.1.photoslibrary/originals/E/E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51.jpeg"
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


def test_missing():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["missing"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.path is None
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
    photos = photosdb.photos(uuid=[UUID_DICT["not_favorite"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.favorite == False


def test_hidden():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["hidden"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.hidden == True


def test_not_hidden():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["not_hidden"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.hidden == False


def test_location_1():
    # test photo with lat/lon info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["location"]])
    assert len(photos) == 1
    p = photos[0]
    lat, lon = p.location
    assert lat == pytest.approx(51.50357167)
    assert lon == pytest.approx(-0.1318055)


def test_location_2():
    # test photo with no location info
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["no_location"]])
    assert len(photos) == 1
    p = photos[0]
    lat, lon = p.location
    assert lat is None
    assert lon is None


def test_hasadjustments1():
    # test hasadjustments == True
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.hasadjustments == True


def test_hasadjustments2():
    # test hasadjustments == False
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.hasadjustments == False


def test_external_edit1():
    # test image has been edited in external editor
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["external_edit"]])
    assert len(photos) == 1
    p = photos[0]

    assert p.external_edit == True


def test_external_edit2():
    # test image has not been edited in external editor
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["no_external_edit"]])
    assert len(photos) == 1
    p = photos[0]

    assert p.external_edit == False


def test_path_edited_jpeg():
    # test a valid edited path
    import os.path
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=["E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"])
    assert len(photos) == 1
    p = photos[0]
    path = p.path_edited
    assert path.endswith(
        "resources/renders/E/E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51_1_201_a.jpeg"
    )
    assert os.path.exists(path)


def test_path_edited_heic():
    # test a valid edited path for .heic image
    import pathlib
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photo = photosdb.get_photo(UUID_HEIC_EDITED)
    assert photo.path_edited.endswith(PATH_HEIC_EDITED)
    assert pathlib.Path(photo.path_edited).is_file()


def test_path_edited2():
    # test an invalid edited path
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])
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


def test_photos_intrash_3():
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


def test_photoinfo_intrash_3():
    """ Test PhotoInfo.intrash and photo has keyword and person """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    p = photosdb.photos(uuid=[UUID_DICT["intrash_person_keywords"]], intrash=True)[0]
    assert p.intrash
    assert "Maria" in p.persons
    assert "wedding" in p.keywords


def test_photoinfo_intrash_4():
    """ Test PhotoInfo.intrash and photo has keyword and person """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    p = photosdb.photos(persons=["Maria"], intrash=True)[0]
    assert p.intrash
    assert "Maria" in p.persons
    assert "wedding" in p.keywords


def test_photoinfo_intrash_5():
    """ Test PhotoInfo.intrash and photo has keyword and person """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    p = photosdb.photos(keywords=["wedding"], intrash=True)[0]
    assert p.intrash
    assert "Maria" in p.persons
    assert "wedding" in p.keywords


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
    assert len(photos) == 2  # won't show the one in the trash


def test_keyword_not_in_album():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    # find all photos with keyword "Kids" not in the album "Pumpkin Farm"
    photos1 = photosdb.photos(albums=["Pumpkin Farm"])
    photos2 = photosdb.photos(keywords=["Kids"])
    photos3 = [p for p in photos2 if p not in photos1]
    assert len(photos3) == 1
    assert photos3[0].uuid == "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"


def test_album_folder_name():
    """Test query with album name same as a folder name """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    photos = photosdb.photos(albums=["Pumpkin Farm"])
    assert sorted(p.uuid for p in photos) == sorted(UUID_PUMPKIN_FARM)


def test_multi_person():
    import osxphotos

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)
    photos = photosdb.photos(persons=["Katie", "Suzy"])

    assert len(photos) == 3


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


def test_get_db_connection():
    """ Test PhotosDB.get_db_connection """
    import osxphotos
    import sqlite3

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    conn, cursor = photosdb.get_db_connection()

    assert isinstance(conn, sqlite3.Connection)
    assert isinstance(cursor, sqlite3.Cursor)

    results = conn.execute("SELECT ZUUID FROM ZASSET WHERE ZFAVORITE = 1;").fetchall()
    assert len(results) == 1
    assert results[0][0] == "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51"  # uuid

    conn.close()


def test_export_1():
    # test basic export
    # get an unedited image and export it using default filename
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_2():
    # test export with user provided filename
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)


def test_export_3():
    # test file already exists and test increment=True (default)
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    filename2 = pathlib.Path(filename)
    filename2 = f"{filename2.stem} (1){filename2.suffix}"
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest = photos[0].export(dest)[0]
    got_dest_2 = photos[0].export(dest)[0]

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)


def test_export_4():
    # test user supplied file already exists and test increment=True (default)
    import os
    import os.path
    import pathlib
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.jpg"
    filename2 = f"osxphotos-export-2-test-{timestamp} (1).jpg"
    expected_dest_2 = os.path.join(dest, filename2)

    got_dest = photos[0].export(dest, filename)[0]
    got_dest_2 = photos[0].export(dest, filename)[0]

    assert got_dest_2 == expected_dest_2
    assert os.path.isfile(got_dest_2)


def test_export_5():
    # test file already exists and test increment=True (default)
    # and overwrite = True
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest)[0]
    got_dest_2 = photos[0].export(dest, overwrite=True)[0]

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)


def test_export_6():
    # test user supplied file already exists and test increment=True (default)
    # and overwrite = True
    import os
    import os.path
    import pathlib
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename)[0]
    got_dest_2 = photos[0].export(dest, filename, overwrite=True)[0]

    assert got_dest_2 == got_dest
    assert got_dest_2 == expected_dest
    assert os.path.isfile(got_dest_2)


def test_export_7():
    # test file already exists and test increment=False (not default), overwrite=False (default)
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename

    got_dest = photos[0].export(dest)[0]
    with pytest.raises(Exception) as e:
        # try to export again with increment = False
        assert photos[0].export(dest, increment=False)
    assert e.type == type(FileExistsError())


def test_export_8():
    # try to export missing file
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["missing"]])

    filename = photos[0].filename

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest)[0]
    assert e.type == type(FileNotFoundError())


def test_export_9():
    # try to export edited file that's not edited
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    filename = photos[0].filename

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, edited=True)
    assert e.type == ValueError


def test_export_10():
    # try to export edited file that's not edited and name provided
    # should raise exception
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest, filename, edited=True)
    assert e.type == ValueError


def test_export_11():
    # export edited file with name provided
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    timestamp = time.time()
    filename = f"osxphotos-export-test-{timestamp}.jpg"
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, filename, edited=True)[0]
    assert got_dest == expected_dest


def test_export_12():
    # export edited file with default name
    import os
    import os.path
    import pathlib
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])

    edited_name = pathlib.Path(photos[0].path_edited).name
    edited_suffix = pathlib.Path(edited_name).suffix
    filename = pathlib.Path(photos[0].filename).stem + "_edited" + edited_suffix
    expected_dest = os.path.join(dest, filename)

    got_dest = photos[0].export(dest, edited=True)[0]
    assert got_dest == expected_dest


def test_export_13():
    # export to invalid destination
    # should raise exception
    import os
    import os.path
    import tempfile

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name

    # create a folder that doesn't exist
    i = 0
    while os.path.isdir(dest):
        dest = os.path.join(dest, str(i))
        i += 1

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export"]])

    filename = photos[0].filename

    with pytest.raises(Exception) as e:
        assert photos[0].export(dest)
    assert e.type == type(FileNotFoundError())


def test_export_14(caplog):
    # test export with user provided filename with different (but valid) extension than source
    import os
    import os.path
    import tempfile
    import time

    import osxphotos

    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["export_tif"]])

    timestamp = time.time()
    filename = f"osxphotos-export-2-test-{timestamp}.tif"
    expected_dest = os.path.join(dest, filename)
    got_dest = photos[0].export(dest, filename)[0]

    assert got_dest == expected_dest
    assert os.path.isfile(got_dest)

    assert "Invalid destination suffix" not in caplog.text


def test_eq():
    """ Test equality of two PhotoInfo objects """
    import osxphotos

    photosdb1 = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photosdb2 = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos1 = photosdb1.photos(uuid=[UUID_DICT["export"]])
    photos2 = photosdb2.photos(uuid=[UUID_DICT["export"]])
    assert photos1[0] == photos2[0]


def test_eq_2():
    """ Test equality of two PhotoInfo objects when one has memoized property """
    import osxphotos

    photosdb1 = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photosdb2 = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos1 = photosdb1.photos(uuid=[UUID_DICT["in_album"]])
    photos2 = photosdb2.photos(uuid=[UUID_DICT["in_album"]])

    # memoize a value
    albums = photos1[0].albums
    assert albums

    assert photos1[0] == photos2[0]


def test_not_eq():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos1 = photosdb.photos(uuid=[UUID_DICT["export"]])
    photos2 = photosdb.photos(uuid=[UUID_DICT["missing"]])
    assert photos1[0] != photos2[0]


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


def test_from_to_date():
    import osxphotos
    import datetime as dt
    import os
    import time

    os.environ["TZ"] = "US/Pacific"
    time.tzset()

    photosdb = osxphotos.PhotosDB(PHOTOS_DB)

    photos = photosdb.photos(from_date=dt.datetime(2018, 10, 28))
    assert len(photos) == 7

    photos = photosdb.photos(to_date=dt.datetime(2018, 10, 28))
    assert len(photos) == 7

    photos = photosdb.photos(
        from_date=dt.datetime(2018, 9, 28), to_date=dt.datetime(2018, 9, 29)
    )
    assert len(photos) == 4


def test_date_invalid():
    """ Test date is invalid  """
    from datetime import datetime, timedelta, timezone
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    # UUID_DICT["date_invalid"] has an invalid date that's
    # been manually adjusted in the database
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
    # UUID_DICT["date_invalid"] has an invalid modified date that's
    # been manually adjusted in the database
    photos = photosdb.photos(uuid=[UUID_DICT["date_invalid"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.date_modified is None


def test_uti():
    """ test uti """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    for uuid, uti in UTI_DICT.items():
        photo = photosdb.get_photo(uuid)
        assert photo.uti == uti
        assert photo.uti_original == UTI_ORIGINAL_DICT[uuid]


def test_raw():
    """ Test various raw properties """
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)

    for uuid, rawinfo in RAW_DICT.items():
        photo = photosdb.get_photo(uuid)
        assert photo.original_filename == rawinfo.original_filename
        assert photo.has_raw == rawinfo.has_raw
        assert photo.israw == rawinfo.israw
        assert photo.uti == rawinfo.uti
        assert photo.uti_original == rawinfo.uti_original
        assert photo.uti_raw == rawinfo.uti_raw
