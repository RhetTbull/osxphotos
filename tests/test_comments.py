""" Test comments and likes """

import datetime

import pytest

import osxphotos
from osxphotos import CommentInfo, LikeInfo

from .conftest import set_timezone

PHOTOS_DB = "tests/Test-Cloud-10.15.6.photoslibrary"

COMMENT_UUID_DICT = {
    "4AD7C8EF-2991-4519-9D3A-7F44A6F031BE": [
        CommentInfo(
            datetime=datetime.datetime(2020, 9, 18, 10, 28, 41, 552000),
            user="Rhet Turnbull",
            ismine=False,
            text="Nice photo!",
        ),
        CommentInfo(
            datetime=datetime.datetime(2020, 9, 19, 22, 52, 20, 12014),
            user=None,
            ismine=True,
            text="Wish I was back here!",
        ),
    ],
    "CCBE0EB9-AE9F-4479-BFFD-107042C75227": [],
    "4E4944A0-3E5C-4028-9600-A8709F2FA1DB": [
        CommentInfo(
            datetime=datetime.datetime(2020, 9, 19, 22, 54, 12, 947978),
            user=None,
            ismine=True,
            text="Nice trophy",
        )
    ],
}

LIKE_UUID_DICT = {
    "4AD7C8EF-2991-4519-9D3A-7F44A6F031BE": [
        LikeInfo(
            datetime=datetime.datetime(2020, 9, 18, 10, 28, 43, 335000),
            user="Rhet Turnbull",
            ismine=False,
        )
    ],
    "CCBE0EB9-AE9F-4479-BFFD-107042C75227": [],
    "65BADBD7-A50C-4956-96BA-1BB61155DA17": [
        LikeInfo(
            datetime=datetime.datetime(2020, 9, 18, 10, 28, 52, 570000),
            user="Rhet Turnbull",
            ismine=False,
        )
    ],
}

COMMENT_UUID_ASDICT = {
    "4E4944A0-3E5C-4028-9600-A8709F2FA1DB": {
        "datetime": datetime.datetime(2020, 9, 19, 22, 54, 12, 947978),
        "user": None,
        "ismine": True,
        "text": "Nice trophy",
    }
}

LIKE_UUID_ASDICT = {
    "65BADBD7-A50C-4956-96BA-1BB61155DA17": {
        "datetime": datetime.datetime(2020, 9, 18, 10, 28, 52, 570000),
        "user": "Rhet Turnbull",
        "ismine": False,
    }
}


@pytest.fixture(scope="module", autouse=True)
def set_timezone_pacific():
    with set_timezone("US/Pacific"):
        yield


@pytest.fixture(scope="module")
def photosdb():
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_comments(photosdb):
    for uuid in COMMENT_UUID_DICT:
        photo = photosdb.get_photo(uuid)
        assert photo.comments == COMMENT_UUID_DICT[uuid]


def test_likes(photosdb):
    for uuid in LIKE_UUID_DICT:
        photo = photosdb.get_photo(uuid)
        assert photo.likes == LIKE_UUID_DICT[uuid]


def test_comments_as_dict(photosdb):
    for uuid in COMMENT_UUID_ASDICT:
        photo = photosdb.get_photo(uuid)
        assert photo.comments[0].asdict() == COMMENT_UUID_ASDICT[uuid]


def test_likes_as_dict(photosdb):
    for uuid in LIKE_UUID_ASDICT:
        photo = photosdb.get_photo(uuid)
        assert photo.likes[0].asdict() == LIKE_UUID_ASDICT[uuid]
