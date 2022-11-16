""" test SearchInfo class """

# Note: Run tests/generate_search_info_test_data.py to generate the UUID_SEARCH_INFO dict

import json
import os

import pytest

import osxphotos

# These tests must be run against the author's personal photo library
skip_test = "OSXPHOTOS_TEST_EXPORT" not in os.environ
pytestmark = pytest.mark.skipif(
    skip_test, reason="These tests only run against system Photos library"
)

PHOTOS_DB = "/Users/rhet/Pictures/Photos Library.photoslibrary"

with open("tests/search_info_test_data_10_15_7.json") as fp:
    test_data = json.load(fp)

UUID_SEARCH_INFO = test_data["UUID_SEARCH_INFO"]
UUID_SEARCH_INFO_NORMALIZED = test_data["UUID_SEARCH_INFO_NORMALIZED"]
UUID_SEARCH_INFO_ALL = test_data["UUID_SEARCH_INFO_ALL"]
UUID_SEARCH_INFO_ALL_NORMALIZED = test_data["UUID_SEARCH_INFO_ALL_NORMALIZED"]


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_search_info(photosdb):
    for uuid in UUID_SEARCH_INFO:
        photo = photosdb.get_photo(uuid)
        search_dict = photo.search_info.asdict()
        for k, v in search_dict.items():
            if type(v) == list:
                assert sorted(v) == sorted(UUID_SEARCH_INFO[uuid][k])
            else:
                assert v == UUID_SEARCH_INFO[uuid][k]


def test_search_info_normalized(photosdb):
    for uuid in UUID_SEARCH_INFO_NORMALIZED:
        photo = photosdb.get_photo(uuid)
        search_dict = photo.search_info_normalized.asdict()
        for k, v in search_dict.items():
            if type(v) == list:
                assert sorted(v) == sorted(UUID_SEARCH_INFO_NORMALIZED[uuid][k])
            else:
                assert v == UUID_SEARCH_INFO_NORMALIZED[uuid][k]


def test_search_info_all(photosdb):
    for uuid in UUID_SEARCH_INFO_ALL:
        photo = photosdb.get_photo(uuid)
        assert sorted(photo.search_info.all) == sorted(UUID_SEARCH_INFO_ALL[uuid])


def test_search_info_all_normalized(photosdb):
    for uuid in UUID_SEARCH_INFO_ALL_NORMALIZED:
        photo = photosdb.get_photo(uuid)
        assert sorted(photo.search_info_normalized.all) == sorted(
            UUID_SEARCH_INFO_ALL_NORMALIZED[uuid]
        )
