"""Test signature utils"""

from osxphotos.signature_utils import (
    normalize_collision_filename,
    normalize_photo_signature_filename,
)


def test_normalize_collision_filename_strips_space_suffix():
    assert normalize_collision_filename("IMG_1234 1.HEIC") == "IMG_1234.HEIC"


def test_normalize_collision_filename_leaves_parenthesized_suffix_alone():
    assert normalize_collision_filename("IMG_1234 (1).HEIC") == "IMG_1234 (1).HEIC"


def test_normalize_photo_signature_filename_preserves_signature_payload():
    assert normalize_photo_signature_filename(
        "img_1234 1.heic:abc123",
        "IMG_1234 1.HEIC",
    ) == "img_1234.heic:abc123"
