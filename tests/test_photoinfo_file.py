"""Test PhotoInfoFromFile sidecar handling (see issue #2228)."""

from __future__ import annotations

import json

import osxphotos.photoinfo_file as photoinfo_file
from osxphotos.photoinfo_file import PhotoInfoFromFile

TEST_IMAGE = "tests/test-images/IMG_4179.jpeg"


def _no_exiftool(monkeypatch):
    """Disable EXIF loading so tests are platform-independent.

    Passing ``exiftool=None`` is not enough: the constructor falls back to the
    module-level ``EXIFTOOL_PATH``, so on a machine with exiftool installed the
    image's real metadata (e.g. a non-empty title) would still be read and could
    fail assertions about sidecar handling. Force the default path to None so no
    exiftool metadata is loaded regardless of platform.
    """
    monkeypatch.setattr(photoinfo_file, "EXIFTOOL_PATH", None)


def test_photoinfofromfile_unknown_sidecar_does_not_raise(tmp_path, monkeypatch):
    """An unrecognized sidecar should warn and continue, not raise (issue #2228)."""
    _no_exiftool(monkeypatch)
    # a JSON dict that is not a recognized sidecar type (no photoTakenTime,
    # not an exiftool/osxphotos list)
    bad_sidecar = tmp_path / "bad.json"
    bad_sidecar.write_text(json.dumps({"foo": "bar"}))

    # should not raise ValueError("Unknown sidecar type ...")
    photoinfo = PhotoInfoFromFile(TEST_IMAGE, exiftool=None, sidecar=str(bad_sidecar))
    # metadata from the unknown sidecar is simply not applied
    assert photoinfo.title in (None, "")


def test_photoinfofromfile_malformed_sidecar_does_not_raise(tmp_path, monkeypatch):
    """A malformed JSON sidecar should warn and continue, not raise."""
    _no_exiftool(monkeypatch)
    bad_sidecar = tmp_path / "malformed.json"
    bad_sidecar.write_text("{not valid json")

    photoinfo = PhotoInfoFromFile(TEST_IMAGE, exiftool=None, sidecar=str(bad_sidecar))
    assert photoinfo.title in (None, "")


def test_photoinfofromfile_empty_list_sidecar_does_not_raise(tmp_path, monkeypatch):
    """An empty-list JSON sidecar should warn and continue, not raise IndexError.

    An empty list previously reached ``metadata[0]`` in the classifier and
    raised ``IndexError`` before ``metadata_from_sidecar`` could convert it to a
    handled ``ValueError`` (see issue #2228).
    """
    _no_exiftool(monkeypatch)
    bad_sidecar = tmp_path / "empty.json"
    bad_sidecar.write_text(json.dumps([]))

    photoinfo = PhotoInfoFromFile(TEST_IMAGE, exiftool=None, sidecar=str(bad_sidecar))
    assert photoinfo.title in (None, "")
