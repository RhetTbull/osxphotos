"""Test osxphotos.image_file_utils.is_live_pair

These tests mock the platform-specific `makelive` dependency so they run on
all platforms (CI runs on Ubuntu as well as macOS).
"""

from __future__ import annotations

from osxphotos import image_file_utils


class _FakeMakeliveNotALivePair:
    """Stands in for makelive when the files are not a live photo pair."""

    @staticmethod
    def is_live_photo_pair(image_path, video_path):
        raise ValueError("Image file is not a JPEG or HEIC image")


class _FakeMakeliveLivePair:
    @staticmethod
    def is_live_photo_pair(image_path, video_path):
        return True


def test_is_live_pair_png_still_does_not_raise(monkeypatch):
    """A PNG still image paired with a video is not a live pair and must not
    raise (regression test for #2128)."""
    monkeypatch.setattr(
        image_file_utils, "makelive", _FakeMakeliveNotALivePair, raising=False
    )
    monkeypatch.setattr(
        image_file_utils, "is_jpeg_or_heic", lambda p: False, raising=False
    )
    monkeypatch.setattr(
        image_file_utils, "is_video_file", lambda p: True, raising=False
    )

    assert image_file_utils.is_live_pair("photo.png", "photo.mov") is False


def test_is_live_pair_handles_makelive_value_error(monkeypatch):
    """If makelive rejects the candidate pair, is_live_pair returns False
    rather than propagating the ValueError (regression test for #2128)."""
    monkeypatch.setattr(
        image_file_utils, "makelive", _FakeMakeliveNotALivePair, raising=False
    )
    monkeypatch.setattr(
        image_file_utils, "is_jpeg_or_heic", lambda p: True, raising=False
    )
    monkeypatch.setattr(
        image_file_utils, "is_video_file", lambda p: True, raising=False
    )

    assert image_file_utils.is_live_pair("photo.jpg", "photo.mov") is False


def test_is_live_pair_valid_pair(monkeypatch):
    """A valid JPEG + video live pair returns True."""
    monkeypatch.setattr(
        image_file_utils, "makelive", _FakeMakeliveLivePair, raising=False
    )
    monkeypatch.setattr(
        image_file_utils, "is_jpeg_or_heic", lambda p: True, raising=False
    )
    monkeypatch.setattr(
        image_file_utils, "is_video_file", lambda p: True, raising=False
    )

    assert image_file_utils.is_live_pair("photo.jpg", "photo.mov") is True


def test_is_live_pair_no_makelive(monkeypatch):
    """Without makelive installed, is_live_pair returns False."""
    monkeypatch.setattr(image_file_utils, "makelive", None, raising=False)

    assert image_file_utils.is_live_pair("photo.jpg", "photo.mov") is False
