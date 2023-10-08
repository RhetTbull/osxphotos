""" Test utility functions in cli.py """

import pytest

from osxphotos.photoquery import load_uuid_from_file

UUID_FILE = "tests/uuid_from_file.txt"
MISSING_UUID_FILE = "tests/uuid_not_found.txt"

UUID_EXPECTED_FROM_FILE = [
    "E9BC5C36-7CD1-40A1-A72B-8B8FAC227D51",
    "6191423D-8DB8-4D4C-92BE-9BBBA308AAC4",
    "A92D9C26-3A50-4197-9388-CB5F7DB9FA91",
]


def test_load_uuid_from_file():
    """Test load_uuid_from_file function"""

    uuid_got = load_uuid_from_file(UUID_FILE)
    assert uuid_got == UUID_EXPECTED_FROM_FILE


def test_load_uuid_from_file_filenotfound():
    """Test load_uuid_from_file function raises error if file not found"""

    with pytest.raises(FileNotFoundError) as err:
        uuid_got = load_uuid_from_file(MISSING_UUID_FILE)
        assert "Could not find" in str(err.value)
