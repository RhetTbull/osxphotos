""" Test PersonInfo class """

import pytest

PHOTOS_DB_5 = "tests/Test-10.15.5.photoslibrary"
PHOTOS_DB_4 = "tests/Test-10.14.6.photoslibrary"

UUID_DICT = {
    "katie_5": "0FFCE0A2-BE93-4661-A783-957BE54072E4",
    "katie_4": "D%zgor6TRmGng5V75UBy5A",
}
PHOTO_DICT = {
    "katie_5": [
        "1EB2B765-0765-43BA-A90C-0D0580E6172C",
        "F12384F6-CD17-4151-ACBA-AE0E3688539E",
        "D79B8D77-BFFC-460B-9312-034F2877D35B",
    ],
    "katie_4": [
        "8SOE9s0XQVGsuq4ONohTng",
        "HrK3ZQdlQ7qpDA0FgOYXLA",
        "15uNd7%8RguTEgNPKHfTWw",
    ],
}

KEY_DICT = {
    "katie_5": "F12384F6-CD17-4151-ACBA-AE0E3688539E",
    "katie_4": "8SOE9s0XQVGsuq4ONohTng",
}

STR_DICT = {
    "katie_5": "PersonInfo(name=Katie, display_name=Katie, uuid=0FFCE0A2-BE93-4661-A783-957BE54072E4, facecount=3)",
    "katie_4": "PersonInfo(name=Katie, display_name=Katie, uuid=D%zgor6TRmGng5V75UBy5A, facecount=3)",
}

JSON_DICT = {
    "katie_5": {
        "uuid": "0FFCE0A2-BE93-4661-A783-957BE54072E4",
        "name": "Katie",
        "displayname": "Katie",
        "keyface": 2,
        "facecount": 3,
        "keyphoto": "F12384F6-CD17-4151-ACBA-AE0E3688539E",
        "favorite": False,
        "sort_order": 3,
        "feature_less": False,
    },
    "katie_4": {
        "uuid": "D%zgor6TRmGng5V75UBy5A",
        "name": "Katie",
        "displayname": "Katie",
        "keyface": 7,
        "facecount": 3,
        "keyphoto": "8SOE9s0XQVGsuq4ONohTng",
        "favorite": False,
        "sort_order": 0,
        "feature_less": False,
    },
}


@pytest.fixture
def photosdb5():
    import osxphotos

    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_5)


@pytest.fixture
def photosdb4():
    import osxphotos

    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_4)


def test_person_info_photosdb_v5(photosdb5):
    """Test PersonInfo object"""
    import json

    test_key = "katie_5"
    katie = [p for p in photosdb5.person_info if p.uuid == UUID_DICT[test_key]][0]

    assert katie.facecount == 3
    assert katie.name == "Katie"
    assert katie.display_name == "Katie"
    photos = katie.photos
    assert len(photos) == 3
    uuid = [p.uuid for p in photos]
    assert sorted(uuid) == sorted(PHOTO_DICT[test_key])
    assert str(katie) == STR_DICT[test_key]
    assert json.loads(katie.json()) == JSON_DICT[test_key]


def test_person_info_photosinfo_v5(photosdb5):
    """Test PersonInfo object"""
    import json

    test_key = "katie_5"
    photo = photosdb5.photos(uuid=[KEY_DICT[test_key]])[0]
    assert "Katie" in photo.persons

    person_info = photo.person_info
    assert len(person_info) == 2

    katie = [p for p in person_info if p.name == "Katie"][0]

    assert katie.facecount == 3
    assert katie.name == "Katie"
    assert katie.display_name == "Katie"
    photos = katie.photos
    assert len(photos) == 3
    uuid = [p.uuid for p in photos]
    assert sorted(uuid) == sorted(PHOTO_DICT[test_key])
    assert katie.keyphoto.uuid == KEY_DICT[test_key]
    assert str(katie) == STR_DICT[test_key]
    assert json.loads(katie.json()) == JSON_DICT[test_key]


def test_person_info_photosdb_v4(photosdb4):
    """Test PersonInfo object"""
    import json

    test_key = "katie_4"
    katie = [p for p in photosdb4.person_info if p.uuid == UUID_DICT[test_key]][0]

    assert katie.facecount == 3
    assert katie.name == "Katie"
    assert katie.display_name == "Katie"
    photos = katie.photos
    assert len(photos) == 3
    uuid = [p.uuid for p in photos]
    assert sorted(uuid) == sorted(PHOTO_DICT[test_key])
    assert katie.keyphoto.uuid == KEY_DICT[test_key]
    assert json.loads(katie.json()) == JSON_DICT[test_key]


def test_person_info_photosinfo_v4(photosdb4):
    """Test PersonInfo object"""
    import json

    test_key = "katie_4"
    photo = photosdb4.photos(uuid=[KEY_DICT[test_key]])[0]
    assert "Katie" in photo.persons

    person_info = photo.person_info
    assert len(person_info) == 2

    katie = [p for p in person_info if p.name == "Katie"][0]
    assert katie.facecount == 3
    assert katie.name == "Katie"
    assert katie.display_name == "Katie"
    photos = katie.photos
    assert len(photos) == 3
    uuid = [p.uuid for p in photos]
    assert sorted(uuid) == sorted(PHOTO_DICT[test_key])
    assert katie.keyphoto.uuid == KEY_DICT[test_key]
    assert json.loads(katie.json()) == JSON_DICT[test_key]
