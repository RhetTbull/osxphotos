"""Test FingerprintQuery class"""

import datetime
from pathlib import Path

import pytest

from osxphotos.platform import is_macos

if is_macos:
    from osxphotos.fingerprintquery import FingerprintQuery, fingerprint
else:
    pytest.skip(allow_module_level=True)

TEST_LIBRARY = "tests/Test-13.0.0.photoslibrary/database/Photos.sqlite"
TEST_IMAGE_DATA = [
    (
        "tests/test-images/IMG_1994.JPG",
        ["A92D9C26-3A50-4197-9388-CB5F7DB9FA91"],
        "AT6Ji2L3VO4MblxwJL/B7PjzfzGv",
    )
]
TEST_DATA = [
    (
        "6FD38366-3BF2-407D-81FE-7153EB6125B6",
        "wedding_edited.jpg",
        536126,
        "Aat1NYuhSj160/i1faP4GKpM5Igq",
        True,
    ),
    (
        "71E3E212-00EB-430D-8A63-5E294B268554",
        "IMG_1064.jpeg",
        2175827,
        "AeWnctwQGgm6QYwwefJ8b0TmMn8M",
        True,
    ),
    (
        "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
        "wedding.jpg",
        460483,
        "ASs96bJvsunOg9Vxo5hK7VU3HegE",
        False,
    ),
    (
        "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
        "Tulips.jpg",
        512561,
        "AUgz5viPNaPHi9NPSlthfeUdQUbu",
        False,
    ),
    (
        "DC99FBDD-7A52-4100-A5BB-344131646C30",
        "St James Park.jpg",
        1262861,
        "AdADRa7jIaoKGF0vlcVdYYYTkjPj",
        False,
    ),
    (
        "D05A5FE3-15FB-49A1-A15D-AB3DA6F8B068",
        "DSC03584.dng",
        21473824,
        "AR+/+jZz0TvuBm+zF1BqtIneTrsZ",
        False,
    ),
    (
        "8846E3E6-8AC8-4857-8448-E3D025784410",
        "IMG_1693.tif",
        48774438,
        "ASkk75asO1LysOyOM6CYu5E7U6d6",
        False,
    ),
    (
        "8E1D7BC9-9321-44F9-8CFB-4083F6B9232A",
        "IMG_2000.JPG",
        3869191,
        "AZVxdRDZsxYTjNjMmxh82cHk3MB/",
        False,
    ),
    (
        "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C",
        "Pumpkins4.jpg",
        700340,
        "Acg7iUvHLiR8FEuZ08xqDKhpN+tR",
        False,
    ),
    (
        "D79B8D77-BFFC-460B-9312-034F2877D35B",
        "Pumkins2.jpg",
        541174,
        "ARa9lDSd7xt40VFCM32sxtN78t3s",
        False,
    ),
    (
        "7783E8E6-9CAC-40F3-BE22-81FB7051C266",
        "IMG_3092.heic",
        1877314,
        "AbQ65MLrRyNJwYcHGqMr6cycEWug",
        False,
    ),
    (
        "3DD2C897-F19E-4CA6-8C22-B027D5A71907",
        "IMG_4547.jpg",
        1477654,
        "AcrntWs8LmFJvDyxMB5XCKyKFMEN",
        False,
    ),
    (
        "4D521201-92AC-43E5-8F7C-59BC41C37A96",
        "IMG_1997.JPG",
        2991408,
        "AdLY396dV18Hg6gS5YMwXpOdemH7",
        False,
    ),
    (
        "1EB2B765-0765-43BA-A90C-0D0580E6172C",
        "Pumpkins3.jpg",
        588140,
        "AcfhCyA9QrbLeurYu6zE5FnQe+SG",
        False,
    ),
    (
        "A92D9C26-3A50-4197-9388-CB5F7DB9FA91",
        "IMG_1994.JPG",
        2901554,
        "AT6Ji2L3VO4MblxwJL/B7PjzfzGv",
        False,
    ),
    (
        "F12384F6-CD17-4151-ACBA-AE0E3688539E",
        "Pumkins1.jpg",
        554127,
        "AUTEnaXpCRgZGfTY4wSdZ9UUf8Op",
        False,
    ),
]


@pytest.fixture
def fingerprint_query():
    return FingerprintQuery("tests/Test-13.0.0.photoslibrary")


def test_init(fingerprint_query):
    assert isinstance(fingerprint_query.photos_library, Path)
    assert str(fingerprint_query.photos_library).endswith(TEST_LIBRARY)
    assert fingerprint_query.photos_version is not None


@pytest.mark.parametrize("uuid, filename, size, test_fingerprint, in_trash", TEST_DATA)
def test_photos_by_fingerprint(
    fingerprint_query, uuid, filename, size, test_fingerprint, in_trash
):
    results = fingerprint_query.photos_by_fingerprint(
        test_fingerprint, in_trash=in_trash
    )
    assert isinstance(results, list)
    if results:
        assert any(result[0] == uuid for result in results)
        for result in results:
            assert len(result) == 3
            assert isinstance(result[0], str)  # UUID
            assert isinstance(result[1], datetime.datetime)  # Date added
            assert isinstance(result[2], str)  # Filename


@pytest.mark.parametrize("uuid, filename, size, test_fingerprint, in_trash", TEST_DATA)
def test_photos_by_filename_size(
    fingerprint_query, uuid, filename, size, test_fingerprint, in_trash
):
    results = fingerprint_query.photos_by_filename_size(
        filename, size, in_trash=in_trash
    )
    assert isinstance(results, list)
    if results:
        assert any(result[0] == uuid for result in results)
        for result in results:
            assert len(result) == 3
            assert isinstance(result[0], str)  # UUID
            assert isinstance(result[1], datetime.datetime)  # Date added
            assert isinstance(result[2], str)  # Filename


@pytest.mark.parametrize(
    "test_image_path, test_uuids, test_fingerprint", TEST_IMAGE_DATA
)
def test_possible_duplicates(
    fingerprint_query, test_image_path, test_uuids, test_fingerprint
):
    results = fingerprint_query.possible_duplicates(test_image_path)

    assert isinstance(results, list)
    assert len(results) > 0  # We expect at least one match

    for result in results:
        assert len(result) == 3
        assert isinstance(result[0], str)  # UUID
        assert isinstance(result[1], datetime.datetime)  # Date added
        assert isinstance(result[2], str)  # Filename

    # test that the expected UUIDs are in the results
    for uuid in test_uuids:
        assert any(result[0] == uuid for result in results)


def test_possible_duplicates_no_match(fingerprint_query):
    non_existent_image = "tests/test-images/NonExistentImage.jpg"
    results = fingerprint_query.possible_duplicates
