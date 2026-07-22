"""Tests for Photos library discovery under macOS TCC permission denial."""

from __future__ import annotations

import builtins
import os

from osxphotos import utils
from osxphotos.cli.common import get_photos_db


def _deny_open_for(filename_fragment: str, monkeypatch):
    """Patch open so reads of filename_fragment raise PermissionError."""
    real_open = builtins.open

    def fake_open(file, *args, **kwargs):
        if filename_fragment in os.fspath(file):
            raise PermissionError("operation not permitted")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)


def test_library_discovery_returns_none_when_last_library_plist_permission_denied(monkeypatch, tmp_path):
    """PermissionError reading Photos plist should behave like unavailable plist."""

    plist = tmp_path / "Library/Containers/com.apple.Photos/Data/Library/Preferences/com.apple.Photos.plist"
    plist.parent.mkdir(parents=True)
    plist.write_bytes(b"blocked")

    monkeypatch.setattr(utils.pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    _deny_open_for("com.apple.Photos.plist", monkeypatch)

    assert utils.get_last_library_path() is None


def test_library_discovery_returns_none_when_system_library_plist_permission_denied(monkeypatch, tmp_path):
    """PermissionError reading photolibraryd plist should behave like unavailable plist."""

    plist = tmp_path / "Library/Containers/com.apple.photolibraryd/Data/Library/Preferences/com.apple.photolibraryd.plist"
    plist.parent.mkdir(parents=True)
    plist.write_bytes(b"blocked")

    monkeypatch.setattr(utils, "is_macos", True)
    monkeypatch.setattr(utils, "get_macos_version", lambda: ("14", "0", "0"))
    monkeypatch.setattr(utils.pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    _deny_open_for("com.apple.photolibraryd.plist", monkeypatch)

    assert utils.get_system_library_path() is None


def test_get_photos_db_falls_back_to_default_library_after_permission_denied(monkeypatch, tmp_path):
    """get_photos_db should continue to ~/Pictures fallback if plist reads are TCC-blocked."""

    fallback = tmp_path / "Pictures" / "Photos Library.photoslibrary"
    fallback.mkdir(parents=True)

    monkeypatch.setattr(utils, "get_last_library_path", lambda: (_ for _ in ()).throw(PermissionError("blocked last")))
    monkeypatch.setattr(utils, "get_system_library_path", lambda: (_ for _ in ()).throw(PermissionError("blocked system")))
    monkeypatch.setattr(os.path, "expanduser", lambda p: str(fallback) if p == "~/Pictures/Photos Library.photoslibrary" else p)

    assert get_photos_db() == str(fallback)
