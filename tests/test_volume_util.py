"""Test for volume_util.py"""

import pathlib

import pytest


def _clear_cache(mod):
    # ensure cache does not leak between tests
    try:
        mod._is_path_on_network_volume_cached.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass


def test_nsurl_reports_network_true(tmp_path, monkeypatch):
    from osxphotos import volume_util as vu

    _clear_cache(vu)
    monkeypatch.setattr(vu, "is_macos", True, raising=False)

    # Force NSURL path to be taken and return True (network)
    monkeypatch.setattr(vu, "_network_via_nsurl", lambda p: True)
    monkeypatch.setattr(vu, "_network_via_mount", lambda p: None)

    assert vu.is_path_on_network_volume(tmp_path) is True


def test_nsurl_reports_local_false(tmp_path, monkeypatch):
    from osxphotos import volume_util as vu

    _clear_cache(vu)
    monkeypatch.setattr(vu, "is_macos", True, raising=False)

    # NSURL says local (False) and mount not consulted
    monkeypatch.setattr(vu, "_network_via_nsurl", lambda p: False)
    monkeypatch.setattr(vu, "_network_via_mount", lambda p: True)  # should be ignored

    assert vu.is_path_on_network_volume(tmp_path) is False


def test_fallback_mount_when_nsurl_unavailable(tmp_path, monkeypatch):
    from osxphotos import volume_util as vu

    _clear_cache(vu)
    monkeypatch.setattr(vu, "is_macos", True, raising=False)

    # NSURL unavailable -> None; fallback to mount -> True
    monkeypatch.setattr(vu, "_network_via_nsurl", lambda p: None)
    monkeypatch.setattr(vu, "_network_via_mount", lambda p: True)

    assert vu.is_path_on_network_volume(tmp_path) is True


def test_mount_reports_local(tmp_path, monkeypatch):
    from osxphotos import volume_util as vu

    _clear_cache(vu)
    monkeypatch.setattr(vu, "is_macos", True, raising=False)

    monkeypatch.setattr(vu, "_network_via_nsurl", lambda p: None)
    monkeypatch.setattr(vu, "_network_via_mount", lambda p: False)

    assert vu.is_path_on_network_volume(tmp_path) is False


def test_uses_nearest_existing_ancestor(tmp_path, monkeypatch):
    from osxphotos import volume_util as vu

    _clear_cache(vu)
    monkeypatch.setattr(vu, "is_macos", True, raising=False)

    # Create a deep, non-existent child under an existing temp dir
    nested = tmp_path / "does" / "not" / "exist"

    captured: list[pathlib.Path] = []

    def fake_nsurl(p: pathlib.Path):
        captured.append(p)
        return False  # local

    monkeypatch.setattr(vu, "_network_via_nsurl", fake_nsurl)
    monkeypatch.setattr(vu, "_network_via_mount", lambda p: None)

    assert vu.is_path_on_network_volume(nested) is False
    # Ensure the helper was called with the nearest existing ancestor (tmp_path)
    assert captured and captured[0] == tmp_path


def test_accepts_str_and_pathlike(tmp_path, monkeypatch):
    from osxphotos import volume_util as vu

    _clear_cache(vu)
    monkeypatch.setattr(vu, "is_macos", True, raising=False)

    monkeypatch.setattr(vu, "_network_via_nsurl", lambda p: False)
    monkeypatch.setattr(vu, "_network_via_mount", lambda p: None)

    # str
    assert vu.is_path_on_network_volume(str(tmp_path)) is False
    # PathLike
    assert vu.is_path_on_network_volume(tmp_path) is False
