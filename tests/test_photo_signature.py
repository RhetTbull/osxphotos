"""Test photo_signature"""

import pytest

from osxphotos.photo_signature import photo_signature
from osxphotos.platform import is_macos


@pytest.mark.skipif(not is_macos, reason="Only macOS fingerprints the original")
def test_photo_signature_falls_back_to_name_and_size_when_original_is_missing(
    tmp_path,
):
    record = {
        "original_filename": "IMG_0001.HEIC",
        "original_filesize": 1234,
        "path": str(tmp_path / "IMG_0001.HEIC"),
        "fingerprint": None,
        "shared": False,
    }
    assert photo_signature(record) == "img_0001.heic:1234"
