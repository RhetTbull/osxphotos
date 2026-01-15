"""Test import_grouper.py"""

import pathlib
from random import shuffle
from re import match

import pytest

from osxphotos.cli import import_grouper
from osxphotos.cli.import_grouper import (
    normalize_edited_stem,
    sort_paths,
    strip_increment_suffix,
)
from osxphotos.platform import is_macos

if not is_macos:
    pytest.skip("Only runs on macOS", allow_module_level=True)


@pytest.mark.parametrize(
    "input_stem,expected",
    [
        ("img_0102 (1)", "img_0102"),
        ("img_0102_edited (1)", "img_0102_edited"),
        ("img_0102 (2)", "img_0102"),
        ("img_0102 (10)", "img_0102"),
        ("img_0102 (123)", "img_0102"),
        ("img_0102", "img_0102"),  # No suffix
        ("img_0102_edited", "img_0102_edited"),  # No suffix
        ("img (1) test", "img (1) test"),  # (1) not at end
        ("img(1)", "img(1)"),  # No space before (1)
        ("img_0102  (1)", "img_0102"),  # Double space
    ],
)
def test_strip_increment_suffix(input_stem, expected):
    """Test stripping increment suffix like ' (1)' from file stems."""
    assert strip_increment_suffix(input_stem) == expected


@pytest.mark.parametrize(
    "input_stem,expected",
    [
        ("img_0102 (1)_edited", "img_0102_edited"),  # increment before _edited
        ("img_0102_edited (1)", "img_0102_edited"),  # increment after _edited
        ("img_0102_edited", "img_0102_edited"),  # no increment
        (
            "img_e1235 (1)_edited",
            "img_e1235_edited",
        ),  # _E pattern with increment before
        ("img_e1235_edited (1)", "img_e1235_edited"),  # _E pattern with increment after
        ("img_0102", "img_0102"),  # no _edited suffix
        ("img_0102 (1)", "img_0102 (1)"),  # no _edited suffix with increment
    ],
)
def test_normalize_edited_stem(input_stem, expected):
    """Test normalizing edited stems with increment suffixes in different positions."""
    assert normalize_edited_stem(input_stem) == expected


def test_no_groups():
    execute_grouping_test(
        (
            ("GOPR0123.JPG",),
            ("IMG_1234.JPG",),
            ("P0203123.JPG",),
            ("Pic_001_20010302_blah blah.JPG",),
        ),
    )


def test_group_same_stems():
    execute_grouping_test(
        (
            ("IMG_1234.JPG", "IMG_1234.aae"),
            ("IMG_1853.heic", "IMG_1853.mov"),
            ("P0203123.JPG",),
        ),
    )


def test_group_edited_E():
    execute_grouping_test(
        (
            ("IMG_1234.JPG", "IMG_1234.aae", "IMG_E1234.JPG"),
            (
                "IMG_1853.heic",
                "IMG_1853.mov",
                "IMG_1853.aae",
                "IMG_E1853.heic",
                "IMG_E1853.mov",
            ),
            ("IMG_E1111.JPG",),
            ("IMG_E22_E.JPG",),
            ("P0203123.JPG",),
        ),
    )


def test_group_edited_suffix():
    execute_grouping_test(
        (
            ("IMG_1234.JPG", "IMG_1234.aae", "IMG_E1234.JPG", "IMG_E1234_edited.JPG"),
            (
                "IMG_1853.heic",
                "IMG_1853.mov",
                "IMG_1853.aae",
                "IMG_E1853.heic",
                "IMG_E1853.mov",
            ),
            ("IMG_2001.heic", "IMG_2001_edited.JPG"),
            ("IMG_2002.heic", "IMG_E2002.heic", "IMG_E2002_edited.JPG"),
            ("IMG_E1111.JPG",),
            ("IMG_E22_E.JPG",),
            ("P0203123.JPG",),
        ),
    )


def test_group_burst():
    execute_grouping_test(
        (
            ("IMG_1234.JPG", "IMG_1234.aae", "IMG_E1234.JPG", "IMG_E1234_edited.JPG"),
            (
                "IMG_1853.heic",
                "IMG_1853.mov",
                "IMG_1853.aae",
                "IMG_E1853.heic",
                "IMG_E1853.mov",
            ),
            ("IMG_2001.JPG", "IMG_2001_edited.JPG"),
            ("IMG_2002.heic", "IMG_E2002.JPG", "IMG_E2002_edited.JPG"),
            (
                "IMG_8001.heic",
                "IMG_8002.heic",
                "IMG_8003.heic",
                "IMG_E8003.JPG",
                "IMG_8004.heic",
            ),
            (
                "IMG_9001.heic",
                "IMG_9002.heic",
                "IMG_9002_edited.JPG",
            ),
        ),
    )


def test_group_original_adjustments():
    """Test grouping of original adjustment AAE files (IMG_O1234.AAE or Filename_O.AAE)"""
    execute_grouping_test(
        (
            # Sorted by base name and stem length (per sort_paths function)
            # Custom.jpg comes first (base: 'custom')
            ("Custom.jpg", "Custom_O.AAE", "Custom_edited.jpg"),
            # IMG_* files sorted by digits (base: 'img', then by full name)
            ("IMG_1234.heic", "IMG_O1234.AAE"),
            ("IMG_3000.heic", "IMG_E3000.JPG", "IMG_O3000.AAE"),
            ("IMG_5678.JPG", "IMG_5678.aae", "IMG_O5678.AAE"),
            ("IMG_O9999.AAE",),  # IMG_O without original - standalone
            # Missing_O (base: 'missing')
            ("Missing_O.AAE",),  # Filename_O without original - standalone
            # MyFile (base: 'myfile')
            ("MyFile.jpeg", "MyFile_O.AAE"),
            # Photo (base: 'photo')
            ("Photo.png", "Photo.aae", "Photo_O.AAE"),
            # Something_Other (base: 'something')
            ("Something_Other.AAE",),  # Should NOT match _O pattern
        ),
    )


def test_group_edited_suffix_with_increment():
    """Test grouping of edited files with increment suffix like (1), (2), etc.

    When osxphotos exports duplicate files, it adds (1), (2), etc. to the stem.
    For edited files, the increment is placed at the end of the stem:
    - Original: IMG_0102 (1).HEIC
    - AAE: IMG_0102 (1).AAE
    - Edited: IMG_0102_edited (1).heic (NOT IMG_0102 (1)_edited.heic)

    This test ensures these files are properly grouped together.
    Note: Groups are sorted by stem length (shorter first) then alphabetically.
    """
    execute_grouping_test(
        (
            # Files without increment suffix (regular case) - shorter stems come first
            ("IMG_0103.HEIC", "IMG_0103.AAE", "IMG_0103_edited.jpeg"),
            # Standalone file without AAE or edited
            ("IMG_0104.JPG",),
            # Files with (1) suffix - edited file has _edited before (1)
            ("IMG_0102 (1).HEIC", "IMG_0102 (1).AAE", "IMG_0102_edited (1).heic"),
            # Files with (2) suffix
            ("IMG_0102 (2).HEIC", "IMG_0102 (2).AAE", "IMG_0102_edited (2).jpeg"),
            # File with increment but no edited version
            ("IMG_0105 (1).HEIC", "IMG_0105 (1).AAE"),
        ),
    )


def test_group_edited_E_with_increment():
    """Test grouping of IMG_E style edited files with increment suffix.

    For files using the IMG_E pattern (Apple's native edited format),
    the increment suffix should also be handled correctly.
    Note: Groups are sorted by stem length (shorter first) then alphabetically.
    """
    execute_grouping_test(
        (
            # Regular IMG_E without increment (shortest stem)
            ("IMG_2000.JPG", "IMG_2000.aae", "IMG_E2000.JPG"),
            # IMG_E pattern with increment suffix
            ("IMG_1234 (1).JPG", "IMG_1234 (1).aae", "IMG_E1234 (1).JPG"),
            # IMG_E with _edited suffix and increment
            (
                "IMG_1235 (1).JPG",
                "IMG_1235 (1).aae",
                "IMG_E1235 (1).JPG",
                "IMG_E1235_edited (1).JPG",
            ),
        ),
    )


def test_group_mixed_increment_suffixes():
    """Test grouping when directory contains both files with and without increment suffixes.

    This tests the common case where the same image has been exported multiple times,
    resulting in files like:
    - IMG_1234.heic, IMG_1234.aae, IMG_1234_edited.heic (first export, no suffix)
    - IMG_1234 (1).heic, IMG_1234 (1).aae, IMG_1234_edited (1).JPG (second export)
    - IMG_1234 (2).heic, IMG_1234 (2).aae, IMG_1234_edited (2).JPG (third export)

    Each set should be grouped separately based on their increment suffix.
    """
    execute_grouping_test(
        (
            # No increment suffix (shortest stems come first)
            ("IMG_1234.heic", "IMG_1234.aae", "IMG_1234_edited.heic"),
            # (1) suffix
            ("IMG_1234 (1).heic", "IMG_1234 (1).aae", "IMG_1234_edited (1).JPG"),
            # (2) suffix
            ("IMG_1234 (2).heic", "IMG_1234 (2).aae", "IMG_1234_edited (2).JPG"),
        ),
    )


def test_sort_paths():
    expected = create_path_list(
        (
            "ABC_0234.jpg",
            "ABC_1234.jpg",
            "ABC_1234.mov",
            "ABC_3234.mov",
            "ABC_1234.aae",
            "ABC_E1234.jpg",
            "ABC_1234_edited.jpg",
            "IMG_0000.jpg",
        )
    )
    for _ in range(10):
        input = list(expected)
        shuffle(input)
        actual = sort_paths(input, lambda p: p)
        assert actual == expected, f"Test input: {input}"


def execute_grouping_test(
    expected: tuple[tuple[str, ...], ...], input: tuple[str, ...] = None
):
    expected_paths = [tuple(create_path_list(g)) for g in expected]
    if input:
        input_paths = create_path_list(input)
    else:
        input_paths = [path for group in expected_paths for path in group]
        shuffle(input_paths)

    actual_paths = import_grouper.group_files_for_import(
        input_paths, edited_stem_func, burst_uuid_func
    )
    assert actual_paths == expected_paths, f"Test input: {input_paths}"


def edited_stem_func(path: pathlib.Path) -> str:
    return (path.parent / (path.stem + "_edited" + path.suffix)).stem.lower()


def burst_uuid_func(path: pathlib.Path) -> str | None:
    if match(r".*_800[1234].*", path.stem):
        return "48b5becd-f98c-4897-98aa-be37eecb6a68"
    if match(r".*_900[1234].*", path.stem):
        return "72c5e147-c5d8-4840-8787-6f8637e537b5"
    return None


def create_path_list(files: tuple[str, ...]) -> list[pathlib.Path]:
    return [pathlib.Path("/tmp/test/path") / f for f in files]
