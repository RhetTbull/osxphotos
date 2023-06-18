""" test PhotoInfo.search_info """

# On 10.14.6, SearchInfo is not valid and returns None

import pytest

from osxphotos._constants import _UNKNOWN_PERSON

PHOTOS_DB = "./tests/Test-10.14.6.photoslibrary/database/photos.db"

LABELS_DICT = {
    # 8SOE9s0XQVGsuq4ONohTng Pumkins1.jpg Can we carry this? Girls with pumpkins [] False
    "8SOE9s0XQVGsuq4ONohTng": [],
    # HrK3ZQdlQ7qpDA0FgOYXLA Pumpkins3.jpg None Kids in pumpkin field [] False
    "HrK3ZQdlQ7qpDA0FgOYXLA": [],
    # YZFCPY24TUySvpu7owiqxA Tulips.jpg Tulips tied together at a flower shop Wedding tulips [] False
    "YZFCPY24TUySvpu7owiqxA": [],
    # 15uNd7%8RguTEgNPKHfTWw Pumkins2.jpg I found one! Girl holding pumpkin [] False
    "15uNd7%8RguTEgNPKHfTWw": [],
    # 3Jn73XpSQQCluzRBMWRsMA St James Park.jpg St. James's Park None [] False
    "3Jn73XpSQQCluzRBMWRsMA": [],
    # 6bxcNnzRQKGnK4uPrCJ9UQ wedding.jpg None Bride Wedding day [] False
    "6bxcNnzRQKGnK4uPrCJ9UQ": [],
    # od0fmC7NQx+ayVr+%i06XA Pumpkins4.jpg Pumpkin heads None [] True
    "od0fmC7NQx+ayVr+%i06XA": [],
}

LABELS_NORMALIZED_DICT = {
    # 8SOE9s0XQVGsuq4ONohTng Pumkins1.jpg Can we carry this? Girls with pumpkins [] False
    "8SOE9s0XQVGsuq4ONohTng": [],
    # HrK3ZQdlQ7qpDA0FgOYXLA Pumpkins3.jpg None Kids in pumpkin field [] False
    "HrK3ZQdlQ7qpDA0FgOYXLA": [],
    # YZFCPY24TUySvpu7owiqxA Tulips.jpg Tulips tied together at a flower shop Wedding tulips [] False
    "YZFCPY24TUySvpu7owiqxA": [],
    # 15uNd7%8RguTEgNPKHfTWw Pumkins2.jpg I found one! Girl holding pumpkin [] False
    "15uNd7%8RguTEgNPKHfTWw": [],
    # 3Jn73XpSQQCluzRBMWRsMA St James Park.jpg St. James's Park None [] False
    "3Jn73XpSQQCluzRBMWRsMA": [],
    # 6bxcNnzRQKGnK4uPrCJ9UQ wedding.jpg None Bride Wedding day [] False
    "6bxcNnzRQKGnK4uPrCJ9UQ": [],
    # od0fmC7NQx+ayVr+%i06XA Pumpkins4.jpg Pumpkin heads None [] True
    "od0fmC7NQx+ayVr+%i06XA": [],
}

SEARCH_INFO_DICT = {
    # 8SOE9s0XQVGsuq4ONohTng Pumkins1.jpg Can we carry this? Girls with pumpkins [] False
    "8SOE9s0XQVGsuq4ONohTng": [],
    # HrK3ZQdlQ7qpDA0FgOYXLA Pumpkins3.jpg None Kids in pumpkin field [] False
    "HrK3ZQdlQ7qpDA0FgOYXLA": [],
    # YZFCPY24TUySvpu7owiqxA Tulips.jpg Tulips tied together at a flower shop Wedding tulips [] False
    "YZFCPY24TUySvpu7owiqxA": [],
    # 15uNd7%8RguTEgNPKHfTWw Pumkins2.jpg I found one! Girl holding pumpkin [] False
    "15uNd7%8RguTEgNPKHfTWw": [],
    # 3Jn73XpSQQCluzRBMWRsMA St James Park.jpg St. James's Park None [] False
    "3Jn73XpSQQCluzRBMWRsMA": [],
    # 6bxcNnzRQKGnK4uPrCJ9UQ wedding.jpg None Bride Wedding day [] False
    "6bxcNnzRQKGnK4uPrCJ9UQ": [],
    # od0fmC7NQx+ayVr+%i06XA Pumpkins4.jpg Pumpkin heads None [] True
    "od0fmC7NQx+ayVr+%i06XA": [],
}


@pytest.fixture
def photosdb():
    # return PhotosDB object for the tests
    import osxphotos

    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_search_info(photosdb):
    for uuid in SEARCH_INFO_DICT:
        photo = photosdb.photos(uuid=[uuid])[0]
        assert photo.search_info is None


def test_labels_normalized(photosdb):
    for uuid in LABELS_NORMALIZED_DICT:
        photo = photosdb.photos(uuid=[uuid])[0]
        assert sorted(photo.labels_normalized) == sorted(LABELS_NORMALIZED_DICT[uuid])


def test_labels(photosdb):
    for uuid in LABELS_DICT:
        photo = photosdb.photos(uuid=[uuid])[0]
        assert sorted(photo.labels) == sorted(LABELS_DICT[uuid])


def test_photosdb_labels(photosdb):
    assert photosdb.labels == []
    assert photosdb.labels_normalized == []


def test_photosdb_labels_as_dict(photosdb):
    assert photosdb.labels_as_dict == dict()
    assert photosdb.labels_normalized_as_dict == dict()
