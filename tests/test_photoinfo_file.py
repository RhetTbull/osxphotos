"""Test PhotoInfoFromFile sidecar handling (see issue #2228)."""

from __future__ import annotations

import json

from osxphotos.photoinfo_file import PhotoInfoFromFile

TEST_IMAGE = "tests/test-images/IMG_4179.jpeg"


def test_photoinfofromfile_unknown_sidecar_does_not_raise(tmp_path):
    """An unrecognized sidecar should warn and continue, not raise (issue #2228)."""
    # a JSON dict that is not a recognized sidecar type (no photoTakenTime,
    # not an exiftool/osxphotos list)
    bad_sidecar = tmp_path / "bad.json"
    bad_sidecar.write_text(json.dumps({"foo": "bar"}))

    # should not raise ValueError("Unknown sidecar type ...")
    photoinfo = PhotoInfoFromFile(
        TEST_IMAGE, exiftool=None, sidecar=str(bad_sidecar)
    )
    # metadata from the unknown sidecar is simply not applied
    assert photoinfo.title in (None, "")


def test_photoinfofromfile_malformed_sidecar_does_not_raise(tmp_path):
    """A malformed JSON sidecar should warn and continue, not raise."""
    bad_sidecar = tmp_path / "malformed.json"
    bad_sidecar.write_text("{not valid json")

    photoinfo = PhotoInfoFromFile(
        TEST_IMAGE, exiftool=None, sidecar=str(bad_sidecar)
    )
    assert photoinfo.title in (None, "")
