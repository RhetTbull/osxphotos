""" Test basic methods for Mojave 10.14.6 """

import datetime
from collections import namedtuple

import pytest

import osxphotos
from osxphotos._constants import _UNKNOWN_PERSON

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
PERSONS = ["Katie", "Suzy", "Maria", _UNKNOWN_PERSON]
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
PERSONS_DICT = {"Katie": 3, "Suzy": 2, "Maria": 1, _UNKNOWN_PERSON: 1}
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
    "hidden": "od0fmC7NQx+ayVr+%i06XA",
    "not_hidden": "6bxcNnzRQKGnK4uPrCJ9UQ",
    "intrash": "td4yIljYS8aRAgzlsRRDtQ",
    "not_intrash": "6bxcNnzRQKGnK4uPrCJ9UQ",
    "location": "3Jn73XpSQQCluzRBMWRsMA",
    "no_location": "YZFCPY24TUySvpu7owiqxA",
    "has_adjustments": "6bxcNnzRQKGnK4uPrCJ9UQ",
    "no_adjustments": "15uNd7%8RguTEgNPKHfTWw",
    "external_edits": "3Jn73XpSQQCluzRBMWRsMA",
    "no_external_edits": "6bxcNnzRQKGnK4uPrCJ9UQ",
    "raw": "DZAgPwQNTWiM+T5cX3WMqA",
    "jpeg+raw": "AcxIpfolT3KU2Ge84VG3yQ",
    "raw+jpeg": "oTiMG6OfSP6d%nUTEOfvMg",
    "heic": "GdJJPQX0RP63mcdKFj%sfQ",
}

RAW_PATH_DICT = {
    "jpeg+raw": "/Masters/2020/10/05/20201005-041506/IMG_1997.cr2",
    "raw+jpeg": "Masters/2020/10/05/20201005-041514/IMG_1994.cr2",
}
UUID_UTI_DICT = {
    "DZAgPwQNTWiM+T5cX3WMqA": [
        "com.adobe.raw-image",
        None,
        "com.adobe.raw-image",
        None,
    ],
    "AcxIpfolT3KU2Ge84VG3yQ": [
        "public.jpeg",
        "com.canon.cr2-raw-image",
        "public.jpeg",
        None,
    ],
    "oTiMG6OfSP6d%nUTEOfvMg": [
        "public.jpeg",
        "com.canon.cr2-raw-image",
        "public.jpeg",
        None,
    ],
    "GdJJPQX0RP63mcdKFj%sfQ": ["public.jpeg", None, "public.heic", "public.jpeg"],
}

ALBUM_SORT_ORDER = [
    "HrK3ZQdlQ7qpDA0FgOYXLA",
    "8SOE9s0XQVGsuq4ONohTng",
    "15uNd7%8RguTEgNPKHfTWw",
]
ALBUM_KEY_PHOTO = "15uNd7%8RguTEgNPKHfTWw"

PHOTOS_DB_LEN = 13
PHOTOS_NOT_IN_TRASH_LEN = 12
PHOTOS_IN_TRASH_LEN = 1

UUID_NOT_REFERENCE = "6bxcNnzRQKGnK4uPrCJ9UQ"
UUID_IS_REFERENCE = "od0fmC7NQx+ayVr+%i06XA"

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
    "DZAgPwQNTWiM+T5cX3WMqA": RawInfo(
        "raw image, no jpeg pair",
        "DSC03584.dng",
        False,
        True,
        False,
        "com.adobe.raw-image",
        "com.adobe.raw-image",
        None,
    ),
    "oTiMG6OfSP6d%nUTEOfvMg": RawInfo(
        "raw+jpeg, jpeg original",
        "IMG_1994.JPG",
        True,
        False,
        False,
        "public.jpeg",
        "public.jpeg",
        "com.canon.cr2-raw-image",
    ),
    "AcxIpfolT3KU2Ge84VG3yQ": RawInfo(
        "raw+jpeg, raw original",
        "IMG_1997.JPG",
        True,
        False,
        True,
        "public.jpeg",
        "public.jpeg",
        "com.canon.cr2-raw-image",
    ),
    "6bxcNnzRQKGnK4uPrCJ9UQ": RawInfo(
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


UUID_FINGERPRINT = {"6bxcNnzRQKGnK4uPrCJ9UQ": "ASs96bJvsunOg9Vxo5hK7VU3HegE"}


@pytest.fixture(scope="module")
def photosdb():
    import osxphotos

    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_init(photosdb):
    import osxphotos

    assert isinstance(photosdb, osxphotos.PhotosDB)


def test_db_version(photosdb):
    import osxphotos

    assert photosdb.db_version in osxphotos._constants._TESTED_DB_VERSIONS
    assert photosdb.db_version == "4025"


def test_photos_version(photosdb):
    assert photosdb.photos_version == 4


def test_db_len(photosdb):
    # assert photosdb.db_version in osxphotos._TESTED_DB_VERSIONS
    assert len(photosdb) == PHOTOS_DB_LEN


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


def test_album_sort_order(photosdb):
    album = [a for a in photosdb.album_info if a.title == "Pumpkin Farm"][0]
    photos = album.photos

    uuids = [p.uuid for p in photos]
    assert uuids == ALBUM_SORT_ORDER


def test_attributes(photosdb):
    import datetime

    photos = photosdb.photos(uuid=["15uNd7%8RguTEgNPKHfTWw"])
    assert len(photos) == 1
    p = photos[0]
    assert p.keywords == ["Kids"]
    assert p.original_filename == "Pumkins2.jpg"
    assert p.filename == "Pumkins2.jpg"
    assert p.date == datetime.datetime(
        2018, 9, 28, 16, 7, 7, 0, datetime.timezone(datetime.timedelta(seconds=-14400))
    )
    assert p.date_added == datetime.datetime(
        2019,
        7,
        27,
        9,
        16,
        50,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
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
    assert not p.ismissing


def test_attributes_2(photosdb):
    """Test attributes including height, width, etc"""
    import datetime

    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])
    assert len(photos) == 1
    p = photos[0]
    assert p.keywords == ["wedding"]
    assert p.original_filename == "wedding.jpg"
    assert p.filename == "wedding.jpg"
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
    assert sorted(p.albums) == []
    assert p.persons == ["Maria"]
    assert p.path.endswith("Masters/2019/07/27/20190727-131650/wedding.jpg")
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
    photos = photosdb.photos(uuid=["od0fmC7NQx+ayVr+%i06XA"])
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
    photos = photosdb.photos(uuid=["od0fmC7NQx+ayVr+%i06XA"])
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


def test_location_has_location(photosdb):
    # test photo with lat/lon info
    photos = photosdb.photos(uuid=[UUID_DICT["location"]])
    assert len(photos) == 1
    p = photos[0]
    lat, lon = p.location
    assert lat == pytest.approx(51.50357167)
    assert lon == pytest.approx(-0.1318055)


def test_latitude_longitude_has_location(photosdb):
    # test photo with lat/lon info
    photos = photosdb.photos(uuid=[UUID_DICT["location"]])
    p = photos[0]
    assert p.latitude == pytest.approx(51.50357167)
    assert p.longitude == pytest.approx(-0.1318055)


def test_latitude_longitude_no_location(photosdb):
    # test photo with no location info
    photos = photosdb.photos(uuid=[UUID_DICT["no_location"]])
    p = photos[0]
    lat, lon = p.latitude, p.longitude
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
    photos = photosdb.photos(uuid=[UUID_DICT["external_edits"]])
    assert len(photos) == 1
    p = photos[0]

    assert p.external_edit


def test_external_edit2(photosdb):
    # test image has not been edited in external editor
    photos = photosdb.photos(uuid=[UUID_DICT["no_external_edits"]])
    assert len(photos) == 1
    p = photos[0]

    assert not p.external_edit


def test_path_edited1(photosdb):
    # test a valid edited path
    import os.path

    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])
    assert len(photos) == 1
    p = photos[0]
    path = p.path_edited
    assert path.endswith("resources/media/version/00/00/fullsizeoutput_9.jpeg")
    assert os.path.exists(path)


def test_path_derivatives(photosdb):
    # test path_derivatives (not currently implemented for Photos <= 4)
    import os.path

    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])
    p = photos[0]
    derivs = [
        "/resources/proxies/derivatives/00/00/1/Y6OofYkbR96spbS6XgwOQw_thumb_1.jpg",
        "/resources/proxies/derivatives/00/00/1/Y6OofYkbR96spbS6XgwOQw_mini_1.jpg",
    ]
    for i, p in enumerate(p.path_derivatives):
        assert p.endswith(derivs[i])


def test_path_edited2(photosdb):
    # test an invalid edited path
    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])
    assert len(photos) == 1
    p = photos[0]
    path = p.path_edited
    assert path is None


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
        assert p.date_trashed.isoformat() == "2305-12-17T13:19:08.978144-07:00"


def test_photos_not_intrash(photosdb):
    """test PhotosDB.photos(intrash=False)"""
    photos = photosdb.photos(intrash=False)
    for p in photos:
        assert not p.intrash
        assert p.date_trashed is None


def test_photoinfo_intrash_1(photosdb):
    """Test PhotoInfo.intrash"""
    p = photosdb.photos(uuid=[UUID_DICT["intrash"]], intrash=True)[0]
    assert p.intrash


def test_photoinfo_intrash_2(photosdb):
    """Test PhotoInfo.intrash and intrash=default"""
    p = photosdb.photos(uuid=[UUID_DICT["intrash"]])
    assert not p


def test_photoinfo_not_intrash(photosdb):
    """Test PhotoInfo.intrash"""
    p = photosdb.photos(uuid=[UUID_DICT["not_intrash"]])[0]
    assert not p.intrash


def test_keyword_2(photosdb):
    photos = photosdb.photos(keywords=["wedding"])
    assert len(photos) == 2


def test_keyword_not_in_album(photosdb):
    # find all photos with keyword "Kids" not in the album "Pumpkin Farm"
    photos1 = photosdb.photos(albums=["Pumpkin Farm"])
    photos2 = photosdb.photos(keywords=["Kids"])
    photos3 = [p for p in photos2 if p not in photos1]
    assert len(photos3) == 1
    assert photos3[0].uuid == "od0fmC7NQx+ayVr+%i06XA"


def test_get_db_path(photosdb):
    db_path = photosdb.db_path
    assert db_path.endswith(PHOTOS_DB_PATH)


def test_get_library_path(photosdb):
    lib_path = photosdb.library_path
    assert lib_path.endswith(PHOTOS_LIBRARY_PATH)


def test_photosdb_repr():
    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photosdb2 = eval(repr(photosdb))

    ignore_keys = ["_tmp_db", "_tempdir", "_tempdir_name", "_db_connection"]
    assert {k: v for k, v in photosdb.__dict__.items() if k not in ignore_keys} == {
        k: v for k, v in photosdb2.__dict__.items() if k not in ignore_keys
    }


def test_photosinfo_repr():
    import datetime  # needed for eval to work

    import osxphotos

    photosdb = osxphotos.PhotosDB(dbfile=PHOTOS_DB)
    photos = photosdb.photos(uuid=[UUID_DICT["favorite"]])
    photo = photos[0]
    photo2 = eval(repr(photo))

    assert {k: str(v).encode("utf-8") for k, v in photo.__dict__.items()} == {
        k: str(v).encode("utf-8") for k, v in photo2.__dict__.items()
    }


def test_multi_uuid(photosdb):
    photos = photosdb.photos(uuid=[UUID_DICT["favorite"], UUID_DICT["not_favorite"]])

    assert len(photos) == 2


def test_multi_keyword(photosdb):
    photos = photosdb.photos(keywords=["Kids", "wedding"])

    assert len(photos) == 6


def test_multi_album(photosdb):
    photos = photosdb.photos(albums=["Pumpkin Farm", "Test Album"])

    assert len(photos) == 3


def test_multi_person(photosdb):
    photos = photosdb.photos(persons=["Katie", "Suzy"])

    assert len(photos) == 3


def test_date_invalid(photosdb):
    """Test date is invalid"""
    from datetime import datetime, timedelta, timezone

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


def test_date_modified(photosdb):
    """Test date modified for photo that has been edited"""

    photos = photosdb.photos(uuid=[UUID_DICT["has_adjustments"]])
    p = photos[0]
    assert p.date_modified == datetime.datetime(
        2019,
        11,
        27,
        1,
        30,
        16,
        681150,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=72000)),
    )


def test_date_modified_none(photosdb):
    """Test date modified for a photo that hasn't been edited"""

    photos = photosdb.photos(uuid=[UUID_DICT["no_adjustments"]])
    p = photos[0]
    assert p.date_modified is None


def test_uti(photosdb):
    for uuid, utis in UUID_UTI_DICT.items():
        photo = photosdb.get_photo(uuid)
        assert photo.uti == utis[0]
        assert photo.uti_raw == utis[1]
        assert photo.uti_original == utis[2]
        assert photo.uti_edited == utis[3]


def test_raw(photosdb):
    photo = photosdb.get_photo(UUID_DICT["raw"])
    # assert photo.israw
    assert not photo.has_raw
    assert photo.uti_raw is None
    assert photo.uti == "com.adobe.raw-image"
    assert photo.path_raw is None

    photo = photosdb.get_photo(UUID_DICT["jpeg+raw"])
    assert photo.has_raw
    assert photo.path_raw.endswith(RAW_PATH_DICT["jpeg+raw"])

    photo = photosdb.get_photo(UUID_DICT["raw+jpeg"])
    assert photo.has_raw
    assert photo.path_raw.endswith(RAW_PATH_DICT["raw+jpeg"])

    photo = photosdb.get_photo(UUID_DICT["heic"])
    assert not photo.has_raw
    assert photo.path_raw is None


def test_raw_properties():
    """Test various raw properties"""
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


def test_is_reference(photosdb):
    """test isreference"""

    photo = photosdb.get_photo(UUID_IS_REFERENCE)
    assert photo.isreference
    photo = photosdb.get_photo(UUID_NOT_REFERENCE)
    assert not photo.isreference


def test_adjustments(photosdb):
    """test adjustments/AdjustmentsInfo (not implemented for 10.14)"""
    from osxphotos.adjustmentsinfo import AdjustmentsInfo

    photo = photosdb.get_photo(UUID_DICT["has_adjustments"])
    assert photo.adjustments is None


def test_no_adjustments(photosdb):
    """test adjustments when photo has no adjusments"""

    photo = photosdb.get_photo(UUID_DICT["no_adjustments"])
    assert photo.adjustments is None


def test_fingerprint(photosdb):
    """Test fingerprint"""
    for uuid, fingerprint in UUID_FINGERPRINT.items():
        photo = photosdb.get_photo(uuid)
        assert photo.fingerprint == fingerprint


def test_tables(photosdb: osxphotos.PhotosDB):
    """Test PhotoInfo.tables"""
    photo = photosdb.get_photo(UUID_DICT["favorite"])
    tables = photo.tables()
    assert tables is None
