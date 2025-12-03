"""Test sidecar utilities used by CLI."""

import pytest

from osxphotos.sidecars import get_sidecar_file_with_template

# test data; the first file in the list is the photo file for which a template should be generated

TEST_DATA = [
    {
        "files": ["test.jpg"],
        "sidecar": True,
        "sidecar_filename_template": None,
        "edited_suffix": None,
        "expected": None,
    },
    {
        "files": ["test.jpg", "test.xmp"],
        "sidecar": True,
        "sidecar_filename_template": None,
        "edited_suffix": None,
        "expected": "test.xmp",
    },
    {
        "files": ["test.jpg", "test.xmp"],
        "sidecar": False,
        "sidecar_filename_template": None,
        "edited_suffix": None,
        "expected": None,
    },
    {
        "files": ["test.jpg", "test.jpg.xmp"],
        "sidecar": True,
        "sidecar_filename_template": None,
        "edited_suffix": None,
        "expected": "test.jpg.xmp",
    },
    {
        "files": ["test.jpg", "test.xmp", "test.jpg.xmp"],
        "sidecar": True,
        "sidecar_filename_template": None,
        "edited_suffix": None,
        "expected": "test.jpg.xmp",
    },
    {
        "files": ["test.jpg", "test.json", "test.xmp"],
        "sidecar": True,
        "sidecar_filename_template": None,
        "edited_suffix": None,
        "expected": "test.json",
    },
    {
        "files": ["test-edited.jpg", "test.json", "test.xmp"],
        "sidecar": True,
        "sidecar_filename_template": None,
        "edited_suffix": None,
        "expected": "test.json",
    },
    {
        "files": ["test_edited.jpg", "test.json", "test.xmp"],
        "sidecar": True,
        "sidecar_filename_template": None,
        "edited_suffix": None,
        "expected": "test.json",
    },
    {
        "files": ["test_edited.jpg", "test_edited.json", "test.json"],
        "sidecar": True,
        "sidecar_filename_template": None,
        "edited_suffix": None,
        "expected": "test_edited.json",
    },
    {
        "files": ["test_edited.jpg", "test_edited.jpg.json", "test.json"],
        "sidecar": True,
        "sidecar_filename_template": None,
        "edited_suffix": None,
        "expected": "test_edited.jpg.json",
    },
    {
        "files": ["test_foo.jpg", "test.xmp"],
        "sidecar": True,
        "sidecar_filename_template": None,
        "edited_suffix": "_foo",
        "expected": "test.xmp",
    },
    {
        "files": ["test.jpg", "test-foo.json", "test.xmp"],
        "sidecar": True,
        "sidecar_filename_template": "{filepath.parent}/{filepath.stem}-foo.json",
        "edited_suffix": None,
        "expected": "test-foo.json",
    },
]


@pytest.mark.parametrize("data", TEST_DATA)
def test_get_sidecar_file_with_template(tmp_path, data):
    """Test get_sidecar_file_with_template"""

    for file in data["files"]:
        (tmp_path / file).touch()

    import logging

    sidecar_name = get_sidecar_file_with_template(
        tmp_path / data["files"][0],
        data["sidecar"],
        data["sidecar_filename_template"],
        data["edited_suffix"],
        None,
    )
    if data["expected"] is None:
        assert sidecar_name is None
    else:
        assert sidecar_name == tmp_path / data["expected"]
