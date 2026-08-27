"""Test signature utils"""

import pytest

from osxphotos.signature_utils import (
    normalize_collision_filename,
    normalize_photo_signature_filename,
)


@pytest.mark.parametrize(
    "filename,expected",
    [
        # collision counters appended by Photos are stripped
        ("IMG_1234 1.HEIC", "IMG_1234.HEIC"),
        ("IMG_1234 12.HEIC", "IMG_1234.HEIC"),
        ("IMG_1234 1 2.jpg", "IMG_1234 1.jpg"),
        # filenames that legitimately end in a number are left alone
        ("IMG_1234.HEIC", "IMG_1234.HEIC"),
        ("IMG_1234 (1).HEIC", "IMG_1234 (1).HEIC"),
        ("Scan 001.jpg", "Scan 001.jpg"),
        ("Vacation 2024.jpg", "Vacation 2024.jpg"),
        ("1.jpg", "1.jpg"),
    ],
)
def test_normalize_collision_filename(filename, expected):
    assert normalize_collision_filename(filename) == expected


def test_normalize_photo_signature_filename_preserves_signature_payload():
    assert (
        normalize_photo_signature_filename(
            "img_1234 1.heic:abc123",
            "IMG_1234 1.HEIC",
        )
        == "img_1234.heic:abc123"
    )


def test_normalize_photo_signature_filename_without_collision_counter():
    assert (
        normalize_photo_signature_filename("img_1234.heic:abc123", "IMG_1234.HEIC")
        == "img_1234.heic:abc123"
    )


def test_normalize_photo_signature_filename_ignores_shared_photo_signature():
    """Shared photo signatures contain no filename so must be returned unchanged"""
    signature = "OWNERHASH:100:200:True:False:2024-01-01T00:00:00"
    assert normalize_photo_signature_filename(signature, "IMG_1234 1.HEIC") == signature
