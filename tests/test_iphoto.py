"""Test iPhoto library support"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import time
from typing import Any

import pytest

from osxphotos import QueryOptions, iPhotoDB
from osxphotos.iphoto import iPhotoPhotoInfo, is_iphoto_library

IPHOTO_LIBRARY = "tests/Test-iPhoto-9.6.1.photolibrary"
PHOTO_LIBRARY = "tests/Test-10.15.7.photoslibrary"
ALBUM_TITLES = ["Test Album", "Pumpkin Farm", "Last Import", "AlbumInFolder"]

# Test data for iPhoto library
# Created with `osxphotos query --library IPHOTO_LIBRARY > tests/iphoto_test_data.json`
# Then replace the path to the library with `IPHOTO_LIBRARY_ROOT`
TEST_DATA = "tests/iphoto_test_data.json"


def recursive_str_replace(
    dict_data: dict[Any, Any], old: str, new: str
) -> dict[Any, Any]:
    """Recursively replace old with new in dict_data"""
    for k, v in dict_data.items():
        if isinstance(v, dict):
            recursive_str_replace(v, old, new)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, str):
                    v[i] = item.replace(old, new)
        elif isinstance(v, str):
            dict_data[k] = v.replace(old, new)
    return dict_data


@pytest.fixture(scope="module")
def iphotodb() -> iPhotoDB:
    """Test instance of the iPhotoDB class"""
    return iPhotoDB(dbfile=IPHOTO_LIBRARY)


def photo_info() -> list[dict[str, Any]]:
    """ "List of dicts containing photo info from iPhoto library"""
    with open(TEST_DATA) as json_file:
        photo_data = json.load(json_file)

    # fix paths in json_data to match current library path
    library_root = str(pathlib.Path(IPHOTO_LIBRARY).resolve().parent)
    photo_data = [
        recursive_str_replace(data, "IPHOTO_LIBRARY_ROOT", library_root)
        for data in photo_data
    ]
    return photo_data


def test_is_iphoto_library():
    """Test is_iphoto_library function"""
    assert is_iphoto_library(IPHOTO_LIBRARY)
    assert not is_iphoto_library(PHOTO_LIBRARY)


def test_iphotodb_load(iphotodb: iPhotoDB):
    """Test that an iPhoto library can be loaded correctly"""

    assert iphotodb.db_version == "110.226"
    assert str(iphotodb.library_path) == str(pathlib.Path(IPHOTO_LIBRARY).resolve())
    assert str(iphotodb.db_path) == str(
        pathlib.Path(IPHOTO_LIBRARY).resolve() / "Database" / "apdb" / "Library.apdb"
    )
    assert iphotodb.photos_version == "com.apple.iPhoto9 - 110.226"


def test_iphotodb_keywords_as_dict(iphotodb: iPhotoDB):
    """Test iPhotoDB.keywords_as_dict"""
    assert iphotodb.keywords_as_dict.get("wedding") == 2


def test_iphotodb_persons_as_dict(iphotodb: iPhotoDB):
    """Test iPhotoDB.persons_as_dict"""
    assert iphotodb.persons_as_dict.get("Katie") == 2
    assert iphotodb.persons_as_dict.get("Suzy") == 1


def test_iphotodb_albums_as_dict(iphotodb: iPhotoDB):
    """Test iPhotoDB.albums_as_dict"""
    assert iphotodb.albums_as_dict.get("Pumpkin Farm") == 3
    assert iphotodb.albums_as_dict.get("AlbumInFolder") == 1


def test_iphotodb_album_info(iphotodb: iPhotoDB):
    """Test iPhotoDB.album_info"""
    album_info = iphotodb.album_info
    assert len(album_info) == 4
    assert sorted(a.title for a in album_info) == sorted(ALBUM_TITLES)


def test_iphotodb_albums(iphotodb: iPhotoDB):
    """Test iPhotoDB.albums"""
    assert sorted(iphotodb.albums) == sorted(ALBUM_TITLES)


def test_iphotodb_len(iphotodb: iPhotoDB):
    """Test iPhotoDB.__len__"""
    assert len(iphotodb) == 13


def test_iphotodb_photos(iphotodb: iPhotoDB):
    """Test iPhtoDB.photos"""

    photos = iphotodb.photos()
    assert len(photos) == 13

    photos = iphotodb.photos(albums=["Pumpkin Farm"])
    assert len(photos) == 3

    photos = iphotodb.photos(images=True, movies=False)
    assert len(photos) == 13

    photos = iphotodb.photos(from_date=datetime.datetime(2020, 9, 19))
    assert len(photos) == 1

    photos = iphotodb.photos(to_date=datetime.datetime(2020, 9, 19))
    assert len(photos) == 12

    photos = iphotodb.photos(persons=["Katie"])
    assert len(photos) == 2

    photos = iphotodb.photos(keywords=["wedding"])
    assert len(photos) == 2

    # St James Park.jpg
    photos = iphotodb.photos(uuid=["QtE4HvHhSnO2W8bmbzWRSg"])
    assert len(photos) == 1
    assert "London" in photos[0].keywords

    photos = iphotodb.photos(intrash=True)
    assert len(photos) == 2


def test_iphotodb_get_photo(iphotodb: iPhotoDB):
    """Test iPhotoDB.get_photo"""
    photo = iphotodb.get_photo(uuid="QtE4HvHhSnO2W8bmbzWRSg")
    assert isinstance(photo, iPhotoPhotoInfo)
    assert photo.original_filename == "St James Park.jpg"


def test_iphotodb_query(iphotodb: iPhotoDB):
    """Test iPhotoDB.query"""

    # calls the same code as PhotosDB.query so just need to test a few things
    options = QueryOptions(keyword=["wedding"])
    photos = iphotodb.query(options)
    assert len(photos) == 2

    options = QueryOptions(uuid=["QtE4HvHhSnO2W8bmbzWRSg"])
    photos = iphotodb.query(options)
    assert len(photos) == 1

    options = QueryOptions(from_date=datetime.datetime(2020, 9, 19))
    photos = iphotodb.query(options)
    assert len(photos) == 1


@pytest.mark.usefixtures("set_tz_pacific")
@pytest.mark.parametrize("photo_dict", photo_info())
def test_iphoto_info(iphotodb: iPhotoDB, photo_dict: dict[str, Any]):
    """Test iPhotoPhotoInfo properties"""

    # rather than test each property individually, just compare json output
    # to the test data
    # when called with shallow=False, the json output will contain the output
    # of iPhotoAlbumInfo, iPhotoPersonInfo, etc. so each class will be tested

    uuid = photo_dict["uuid"]
    photo = iphotodb.get_photo(uuid)
    for key, value in json.loads(photo.json(shallow=False)).items():
        if key != "fingerprint":
            # fingerprint not implemented on linux
            assert value == photo_dict[key]
