"""Test import_grouper.py"""

import pathlib
from random import shuffle
from re import match

import pytest

from osxphotos.cli import import_grouper
from osxphotos.cli.import_grouper import sort_paths
from osxphotos.platform import is_macos

if not is_macos:
    pytest.skip("Only runs on macOS", allow_module_level=True)


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
