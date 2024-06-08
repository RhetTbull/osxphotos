"""Test utilities used by the osxphotos import CLI"""

from __future__ import annotations

import pathlib
import shutil

import pytest

from osxphotos.platform import is_macos

if is_macos:
    import osxphotos.cli.import_cli as import_cli
    from osxphotos.cli.import_cli import (
        group_files_to_import,
        rename_edited_group,
        sort_paths,
    )

# skip all tests if not macOS
pytestmark = pytest.mark.skipif(not is_macos, reason="macOS specific test")

ORIGINAL_FILE = "tests/test-images/wedding.JPG"
EDITED_FILE = "tests/test-images/wedding_edited.JPG"
AAE_FILE = "tests/test-images/wedding.AAE"

# test data for rename_edited_group
# first tuple is input, second tuple is expected output
RENAME_TEST_DATA = [
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
            "GOPR0123.JPG",
            "GOPR0123_edited.JPG",
            "GOPR0123.AAE",
        ),
        (
            "IMG_0001_GOPR0123.JPG",
            "IMG_E0001_GOPR0123.JPG",
            "IMG_0001_GOPR0123.AAE",
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

# test data for rename_edited_group with live photos
# first tuple is input, second tuple is expected output
RENAME_TEST_DATA_LIVE_EDITED = [
    (
        (
            "IMG_1853.heic",
            "IMG_1853.mov",
            "IMG_1853_edited.heic",
            "IMG_1853_edited.mov",
            "IMG_1853.aae",
        ),
        (
            "IMG_1853.heic",
            "IMG_1853.mov",
            "IMG_E1853.heic",
            "IMG_E1853.mov",
            "IMG_1853.aae",
        ),
    ),
    (
        (
            "IMG_1853.heic",
            "IMG_1853.mov",
            "IMG_E1853.heic",
            "IMG_E1853.mov",
            "IMG_1853.aae",
        ),
        (
            "IMG_1853.heic",
            "IMG_1853.mov",
            "IMG_E1853.heic",
            "IMG_E1853.mov",
            "IMG_1853.aae",
        ),
    ),
    (
        (
            "LiveImage.heic",
            "LiveImage.mov",
            "LiveImage_edited.heic",
            "LiveImage_edited.mov",
            "LiveImage.aae",
        ),
        (
            "IMG_0001_LiveImage.heic",
            "IMG_0001_LiveImage.mov",
            "IMG_E0001_LiveImage.heic",
            "IMG_E0001_LiveImage.mov",
            "IMG_0001_LiveImage.aae",
        ),
    ),
]

# Test images for group_files_to_import
LIVE_PHOTO_ORIGINAL_PHOTO = "IMG_1853.HEIC"
LIVE_PHOTO_EDITED_PHOTO = "IMG_E1853.heic"
LIVE_PHOTO_ORIGINAL_VIDEO = "IMG_1853.MOV"
LIVE_PHOTO_EDITED_VIDEO = "IMG_E1853.mov"
LIVE_PHOTO_AAE = "IMG_1853.AAE"
NOT_LIVE_PHOTO = "not_live.jpeg"
NOT_LIVE_VIDEO = "not_live.mov"
REGULAR_PHOTO = "tulips.jpg"
REGULAR_VIDEO = "Jellyfish.mov"
RAW_PAIR_RAW = "IMG_1997.cr2"
RAW_PAIR_JPEG = "IMG_1997.JPG"
RAW_PAIR_EDITED_RAW_ORIGINAL = "IMG_1994.cr2"
RAW_PAIR_EDITED_JPEG_ORIGINAL = "IMG_1994.JPG"
RAW_PAIR_EDITED_JPEG_EDITED = "IMG_1994_edited.jpeg"
RAW_PAIR_EDITED_AAE = "IMG_1994.AAE"
BURST_IMAGES = [
    "IMG_8204.JPG",
    "IMG_8205.JPG",
    "IMG_8206.JPG",
    "IMG_8207.JPG",
    "IMG_8208.JPG",
]

# test data for group_files_to_import
GROUP_FILES_EXPECTED = [
    (
        LIVE_PHOTO_ORIGINAL_PHOTO,
        LIVE_PHOTO_ORIGINAL_VIDEO,
        LIVE_PHOTO_EDITED_PHOTO,
        LIVE_PHOTO_EDITED_VIDEO,
        LIVE_PHOTO_AAE,
    ),
    (
        "LivePhoto.HEIC",
        "LivePhoto.MOV",
        "LivePhoto_edited.heic",
        "LivePhoto_edited.mov",
        "LivePhoto.AAE",
    ),
    (RAW_PAIR_RAW, RAW_PAIR_JPEG),
    (
        RAW_PAIR_EDITED_RAW_ORIGINAL,
        RAW_PAIR_EDITED_JPEG_ORIGINAL,
        RAW_PAIR_EDITED_JPEG_EDITED,
        RAW_PAIR_EDITED_AAE,
    ),
    (REGULAR_PHOTO,),
    (REGULAR_VIDEO,),
    (NOT_LIVE_PHOTO, NOT_LIVE_VIDEO),
    tuple(BURST_IMAGES),
]

# test data for sort_paths
# first list is input, second tuple is expected output
SORT_PATHS_DATA = [
    (
        [
            pathlib.Path("ABC_1234_edited.mov"),
            pathlib.Path("ABC_1234.aae"),
            pathlib.Path("ABC_1234.jpg"),
            pathlib.Path("IMG_1234.aae"),
            pathlib.Path("ABC_1234.mov"),
            pathlib.Path("IMG_1234.jpg"),
        ],
        (
            pathlib.Path("ABC_1234.jpg"),
            pathlib.Path("ABC_1234.mov"),
            pathlib.Path("ABC_1234.aae"),
            pathlib.Path("ABC_1234_edited.mov"),
            pathlib.Path("IMG_1234.jpg"),
            pathlib.Path("IMG_1234.aae"),
        ),
    ),
    (
        [
            pathlib.Path("IMG_1234.mov"),
            pathlib.Path("IMG_1234.jpeg"),
            pathlib.Path("ABC_1234.mov"),
            pathlib.Path("ABC_1234.jpg"),
            pathlib.Path("ABC_1234.aae"),
            pathlib.Path("ABC_1234_edited.mov"),
        ],
        (
            pathlib.Path("ABC_1234.jpg"),
            pathlib.Path("ABC_1234.mov"),
            pathlib.Path("ABC_1234.aae"),
            pathlib.Path("ABC_1234_edited.mov"),
            pathlib.Path("IMG_1234.jpeg"),
            pathlib.Path("IMG_1234.mov"),
        ),
    ),
    (
        [
            pathlib.Path("XYZ_5678.jpg"),
            pathlib.Path("XYZ_5678_edited.mov"),
            pathlib.Path("XYZ_5678.aae"),
            pathlib.Path("XYZ_5678.mov"),
        ],
        (
            pathlib.Path("XYZ_5678.jpg"),
            pathlib.Path("XYZ_5678.mov"),
            pathlib.Path("XYZ_5678.aae"),
            pathlib.Path("XYZ_5678_edited.mov"),
        ),
    ),
    (
        [
            pathlib.Path("IMG_9876.jpg"),
            pathlib.Path("IMG_9876_edited.mov"),
            pathlib.Path("IMG_9876.aae"),
            pathlib.Path("IMG_9876.mov"),
        ],
        (
            pathlib.Path("IMG_9876.jpg"),
            pathlib.Path("IMG_9876.mov"),
            pathlib.Path("IMG_9876.aae"),
            pathlib.Path("IMG_9876_edited.mov"),
        ),
    ),
]


def stage_photo_files(tmp_path: pathlib.Path) -> list[pathlib.Path]:
    """Copy files to tmp_path"""
    staged = []
    cwd = pathlib.Path().cwd()

    def copy_file(src, dest):
        shutil.copy(str(cwd / "tests/test-images" / src), str(tmp_path / dest))

    # live photo with form IMG_1234.ext / IMG_E1234.ext
    copy_file(LIVE_PHOTO_ORIGINAL_PHOTO, "IMG_1853.HEIC")
    staged.append(tmp_path / "IMG_1853.HEIC")
    copy_file(LIVE_PHOTO_EDITED_PHOTO, "IMG_E1853.heic")
    staged.append(tmp_path / "IMG_E1853.heic")
    copy_file(LIVE_PHOTO_ORIGINAL_VIDEO, "IMG_1853.MOV")
    staged.append(tmp_path / "IMG_1853.MOV")
    copy_file(LIVE_PHOTO_EDITED_VIDEO, "IMG_E1853.mov")
    staged.append(tmp_path / "IMG_E1853.mov")
    copy_file(LIVE_PHOTO_AAE, "IMG_1853.AAE")
    staged.append(tmp_path / "IMG_1853.AAE")

    # live photo with form LivePhoto.jpg / LivePhoto.mov /LivePhoto_edited.jpg / LivePhoto_edited.mov
    copy_file(LIVE_PHOTO_ORIGINAL_PHOTO, "LivePhoto.HEIC")
    staged.append(tmp_path / "LivePhoto.HEIC")
    copy_file(LIVE_PHOTO_EDITED_PHOTO, "LivePhoto_edited.HEIC")
    staged.append(tmp_path / "LivePhoto_edited.HEIC")
    copy_file(LIVE_PHOTO_ORIGINAL_VIDEO, "LivePhoto.MOV")
    staged.append(tmp_path / "LivePhoto.MOV")
    copy_file(LIVE_PHOTO_EDITED_VIDEO, "LivePhoto_edited.MOV")
    staged.append(tmp_path / "LivePhoto_edited.MOV")
    copy_file(LIVE_PHOTO_AAE, "LivePhoto.AAE")
    staged.append(tmp_path / "LivePhoto.AAE")

    # not live photo
    copy_file(NOT_LIVE_PHOTO, "not_live.jpeg")
    staged.append(tmp_path / "not_live.jpeg")
    copy_file(NOT_LIVE_VIDEO, "not_live.mov")
    staged.append(tmp_path / "not_live.mov")

    # regular photo
    copy_file(REGULAR_PHOTO, "tulips.jpg")
    staged.append(tmp_path / "tulips.jpg")

    # regular video
    copy_file(REGULAR_VIDEO, "Jellyfish.mov")
    staged.append(tmp_path / "Jellyfish.mov")

    # raw pair
    copy_file(RAW_PAIR_RAW, "IMG_1997.cr2")
    staged.append(tmp_path / "IMG_1997.cr2")
    copy_file(RAW_PAIR_JPEG, "IMG_1997.JPG")
    staged.append(tmp_path / "IMG_1997.JPG")

    # edited raw pair
    copy_file(RAW_PAIR_EDITED_RAW_ORIGINAL, "IMG_1994.cr2")
    staged.append(tmp_path / "IMG_1994.cr2")
    copy_file(RAW_PAIR_EDITED_JPEG_ORIGINAL, "IMG_1994.JPG")
    staged.append(tmp_path / "IMG_1994.JPG")
    copy_file(RAW_PAIR_EDITED_JPEG_EDITED, "IMG_1994_edited.jpeg")
    staged.append(tmp_path / "IMG_1994_edited.jpeg")
    copy_file(RAW_PAIR_EDITED_AAE, "IMG_1994.AAE")
    staged.append(tmp_path / "IMG_1994.AAE")

    # burst images
    for i, img in enumerate(BURST_IMAGES):
        copy_file(img, f"IMG_820{i+4}.JPG")
        staged.append(tmp_path / f"IMG_820{i+4}.JPG")

    return staged


def sort_tuples(tuples_list):
    """Sort a list of tuples while also sorting the elements of each tuple"""
    sorted_tuples = [tuple(sorted(tup)) for tup in tuples_list]
    sorted_tuples_list = sorted(sorted_tuples)
    return sorted_tuples_list


def convert_and_lowercase_tuples(tuples_list):
    """Convert each element of each tuple to a string and lowercase it"""
    return [tuple(str(element).lower() for element in tup) for tup in tuples_list]


@pytest.mark.parametrize("test_input,expected", RENAME_TEST_DATA)
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


@pytest.mark.parametrize("test_input,expected", RENAME_TEST_DATA_LIVE_EDITED)
def test_renamed_edited_group_live_edited(tmp_path, test_input, expected):
    """Test rename_edited_group"""

    cwd = pathlib.Path().cwd()

    def copy_file(src, dest):
        shutil.copy(str(cwd / "tests/test-images" / src), str(tmp_path / dest))

    # reset the counter in import_cli
    import_cli._global_image_counter = 1

    # copy test files to tmp_path with the test_input names
    (
        original_file_photo,
        original_file_video,
        edited_file_photo,
        edited_file_video,
        aae_file,
    ) = test_input
    original_file_photo = tmp_path / original_file_photo
    original_file_video = tmp_path / original_file_video
    edited_file_photo = tmp_path / edited_file_photo
    edited_file_video = tmp_path / edited_file_video
    aae_file = tmp_path / aae_file

    copy_file(LIVE_PHOTO_ORIGINAL_PHOTO, original_file_photo)
    copy_file(LIVE_PHOTO_ORIGINAL_VIDEO, original_file_video)
    copy_file(LIVE_PHOTO_EDITED_PHOTO, edited_file_photo)
    copy_file(LIVE_PHOTO_EDITED_VIDEO, edited_file_video)
    copy_file(LIVE_PHOTO_AAE, aae_file)

    # run rename_edited_group
    original_group = (
        original_file_photo,
        original_file_video,
        edited_file_photo,
        edited_file_video,
        aae_file,
    )
    new_group = rename_edited_group(original_group, "_edited", None, None, False, None)
    new_names = tuple(new.name for new in new_group)
    assert sorted(new_names) == sorted(expected)


def test_group_files_to_import(tmp_path):
    """Test group_files_to_import"""
    staged_files = stage_photo_files(tmp_path)
    results = group_files_to_import(
        files=staged_files,
        auto_live=True,
        edited_suffix="_edited",
        relative_filepath=None,
        exiftool_path=None,
        sidecar=False,
        sidecar_filename_template=None,
        verbose=print,
        no_progress=True,
    )

    results = [tuple(p.name for p in tup) for tup in results]
    results = convert_and_lowercase_tuples(sort_tuples(results))
    expected = convert_and_lowercase_tuples(sort_tuples(GROUP_FILES_EXPECTED))
    assert results == expected


@pytest.mark.parametrize("input_paths, expected_output", SORT_PATHS_DATA)
def test_sort_paths(input_paths, expected_output):
    assert sort_paths(input_paths) == expected_output
