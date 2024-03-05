"""Test compare_libraries.py"""

from __future__ import annotations

import csv
import io
import json

import pytest

from osxphotos.compare_libraries import compare_photos_libraries
from osxphotos.photoinfo import PhotoInfo
from osxphotos.photosdb import PhotosDB

LIBRARY_A = "tests/Test-13.5.1-compare-1.photoslibrary"
LIBRARY_B = "tests/Test-13.5.1-compare-2.photoslibrary"


@pytest.fixture(scope="module")
def db_a():
    return PhotosDB(dbfile=LIBRARY_A)


@pytest.fixture(scope="module")
def db_b():
    return PhotosDB(dbfile=LIBRARY_B)


@pytest.fixture(scope="module")
def diff_a_b(db_a, db_b):
    return compare_photos_libraries(db_a, db_b)


@pytest.fixture(scope="module")
def diff_a_a(db_a):
    return compare_photos_libraries(db_a, db_a)


def test_compare_photos_libraries_a_b(diff_a_b):
    """Test comparison of two libraries A <--> B"""

    assert len(diff_a_b.in_a_not_b) == 1
    assert len(diff_a_b.in_b_not_a) == 2
    assert len(diff_a_b.in_both_same) == 2
    assert len(diff_a_b.in_both_different) == 1


def test_compare_photos_libraries_b_a(db_a, db_b):
    """Test comparison of two libraries B <--> A"""

    diff_b_a = compare_photos_libraries(db_b, db_a)
    assert len(diff_b_a.in_a_not_b) == 2
    assert len(diff_b_a.in_b_not_a) == 1
    assert len(diff_b_a.in_both_same) == 2
    assert len(diff_b_a.in_both_different) == 1


def test_compare_photos_libraries_a_a(diff_a_a):
    """Test comparison of two libraries A <--> A"""

    assert len(diff_a_a.in_a_not_b) == 0
    assert len(diff_a_a.in_b_not_a) == 0
    assert len(diff_a_a.in_both_same) == 4
    assert len(diff_a_a.in_both_different) == 0


def test_compare_photos_libraries_str(diff_a_b):
    """Test comparison str output"""

    expected = [
        "in_a_not_b = 1 asset",
        "in_b_not_a = 2 assets",
        "in_a_and_b_same = 2 assets",
        "in_a_and_b_different = 1 asset",
    ]
    diff_str = str(diff_a_b)
    for line in expected:
        assert line in diff_str


def test_compare_photos_libraries_json(diff_a_b):
    """Test comparison json output"""

    diff_json = json.loads(diff_a_b.json())
    assert len(diff_json["in_a_not_b"]) == 1
    assert len(diff_json["in_b_not_a"]) == 2
    assert len(diff_json["in_a_and_b_same"]) == 2
    assert len(diff_json["in_a_and_b_different"]) == 1


def test_compare_photos_libraries_csv(diff_a_b):
    """Test comparison CSV output"""
    diff_csv = diff_a_b.csv()
    csvfile = io.StringIO(diff_csv)
    reader = csv.DictReader(csvfile)
    rows = list(reader)
    assert len(rows) == 6
    test_row = {}
    for row in rows:
        if row["original_filename"] == "wedding.jpg":
            test_row = row
            break
    assert test_row["in_a_not_b"] == "0"
    assert test_row["in_b_not_a"] == "0"
    assert test_row["in_a_and_b_same"] == "0"
    assert test_row["in_a_and_b_different"] == "1"


def test_compare_photos_libraries_len_a_b(diff_a_b):
    """Test comparison len()"""
    assert len(diff_a_b) == 4


def test_compare_photos_libraries_len_a_a(diff_a_a):
    """Test comparison len()"""
    assert len(diff_a_a) == 0


def test_compare_photos_libraries_bool(diff_a_b):
    """Test comparison len()"""
    assert bool(diff_a_b)


def test_compare_photos_libraries_bool(diff_a_a):
    """Test comparison len()"""
    assert not bool(diff_a_a)


def test_compare_photos_libraries_diff_function(db_a, db_b):
    """Test custom comparison diff function"""

    def diff_func(a: PhotoInfo, b: PhotoInfo):
        # return difference in keywords, if any
        kw_a = set(a.keywords)
        kw_b = set(b.keywords)
        return kw_a.symmetric_difference(kw_b)

    diff = compare_photos_libraries(db_a, db_b, diff_function=diff_func)
    assert len(diff.in_a_not_b) == 1
    assert len(diff.in_b_not_a) == 2
    assert len(diff.in_both_same) == 2
    assert len(diff.in_both_different) == 1


def test_compare_photos_libraries_signature_function(db_a, db_b):
    def signature_func(p: PhotoInfo):
        sig, _ = p.render_template(
            "{photo.original_filename|lower}:{photo.original_filesize}"
        )
        return sig[0]

    diff = compare_photos_libraries(db_a, db_b, signature_function=signature_func)
    assert len(diff.in_a_not_b) == 1
    assert len(diff.in_b_not_a) == 2
    assert len(diff.in_both_same) == 2
    assert len(diff.in_both_different) == 1
