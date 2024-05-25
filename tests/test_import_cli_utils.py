"""Test utilities used by the osxphotos import CLI"""

import shutil

import pytest

from osxphotos.platform import is_macos

if is_macos:
    import osxphotos.cli.import_cli as import_cli
    from osxphotos.cli.import_cli import rename_edited_group

ORIGINAL_FILE = "tests/test-images/wedding.JPG"
EDITED_FILE = "tests/test-images/wedding_edited.JPG"
AAE_FILE = "tests/test-images/wedding.AAE"

TEST_DATA = [
    (
        ("IMG_1234.JPG", "IMG_E1234.JPG", "IMG_1234.AAE"),
        ("IMG_1234.JPG", "IMG_E1234.JPG", "IMG_1234.AAE"),
    ),
    (
        ("P0203123.JPG", "P0203123_edited.JPG", "P0203123.AAE"),
        ("IMG_0001_P0203123.JPG", "IMG_E0001_P0203123.JPG", "IMG_0001_P0203123.AAE"),
    ),
    (
        (
            "Pic_001_20010302_blah blah.JPG",
            "Pic_001_20010302_blah blah_edited.JPG",
            "Pic_001_20010302_blah blah.AAE",
        ),
        (
            "IMG_0001_Pic_001_20010302_blah blah.JPG",
            "IMG_E0001_Pic_001_20010302_blah blah.JPG",
            "IMG_0001_Pic_001_20010302_blah blah.AAE",
        ),
    ),
    (
        (
            "GOP01234.JPG",
            "GOP01234_edited.JPG",
            "GOP01234.AAE",
        ),
        (
            "IMG_0001_GOP01234.JPG",
            "IMG_E0001_GOP01234.JPG",
            "IMG_0001_GOP01234.AAE",
        ),
    ),
    (
        (
            "IMG_20240302_122543.JPG",
            "IMG_20240302_122543_edited.JPG",
            "IMG_20240302_122543.AAE",
        ),
        (
            "IMG_20240302_122543.JPG",
            "IMG_E20240302_122543.JPG",
            "IMG_20240302_122543.AAE",
        ),
    ),
]


@pytest.mark.skipif(not is_macos, reason="macOS specific test")
@pytest.mark.parametrize("test_input,expected", TEST_DATA)
def test_renamed_edited_group(tmp_path, test_input, expected):
    """Test rename_edited_group"""

    # reset the counter in import_cli
    import_cli._global_image_counter = 1

    # copy test files to tmp_path with the test_input names
    original_file, edited_file, aae_file = test_input
    original_file = tmp_path / original_file
    edited_file = tmp_path / edited_file
    aae_file = tmp_path / aae_file
    shutil.copy(ORIGINAL_FILE, original_file)
    shutil.copy(EDITED_FILE, edited_file)
    shutil.copy(AAE_FILE, aae_file)

    # run rename_edited_group
    original_group = (original_file, edited_file, aae_file)
    new_group = rename_edited_group(original_group, "_edited", None, None, False, None)
    new_names = tuple(new.name for new in new_group)
    assert sorted(new_names) == sorted(expected)
