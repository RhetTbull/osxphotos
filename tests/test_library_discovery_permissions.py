"""Tests for Photos library discovery under macOS TCC permission denial."""

from __future__ import annotations

import builtins
import os

from osxphotos import utils
from osxphotos.cli.common import get_photos_db

LAST_LIBRARY_PLIST = "Library/Containers/com.apple.Photos/Data/Library/Preferences/com.apple.Photos.plist"
SYSTEM_LIBRARY_PLIST = "Library/Containers/com.apple.photolibraryd/Data/Library/Preferences/com.apple.photolibraryd.plist"


def _write_plist(home, relative_path):
    """Create a placeholder plist file below home."""
    plist = home / relative_path
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_bytes(b"blocked")
    return plist


def _deny_open_for(monkeypatch, *filename_fragments):
    """Patch open so reads of any of filename_fragments raise PermissionError."""
    real_open = builtins.open

    def fake_open(file, *args, **kwargs):
        if any(fragment in os.fspath(file) for fragment in filename_fragments):
            raise PermissionError("operation not permitted")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)


def test_get_last_library_path_returns_none_when_plist_permission_denied(
    monkeypatch, tmp_path
):
    """PermissionError reading Photos plist should behave like unavailable plist."""
    _write_plist(tmp_path, LAST_LIBRARY_PLIST)
    monkeypatch.setenv("HOME", str(tmp_path))
    _deny_open_for(monkeypatch, "com.apple.Photos.plist")

    assert utils.get_last_library_path() is None


def test_get_system_library_path_returns_none_when_plist_permission_denied(
    monkeypatch, tmp_path
):
    """PermissionError reading photolibraryd plist should behave like unavailable plist."""
    _write_plist(tmp_path, SYSTEM_LIBRARY_PLIST)
    monkeypatch.setattr(utils, "is_macos", True)
    monkeypatch.setattr(utils, "get_macos_version", lambda: ("14", "0", "0"))
    monkeypatch.setenv("HOME", str(tmp_path))
    _deny_open_for(monkeypatch, "com.apple.photolibraryd.plist")

    assert utils.get_system_library_path() is None


def test_get_photos_db_falls_back_to_default_library_when_plists_permission_denied(
    monkeypatch, tmp_path
):
    """get_photos_db should continue to ~/Pictures fallback if plist reads are TCC-blocked."""
    _write_plist(tmp_path, LAST_LIBRARY_PLIST)
    _write_plist(tmp_path, SYSTEM_LIBRARY_PLIST)
    fallback = tmp_path / "Pictures" / "Photos Library.photoslibrary"
    fallback.mkdir(parents=True)

    monkeypatch.setattr(utils, "is_macos", True)
    monkeypatch.setattr(utils, "get_macos_version", lambda: ("14", "0", "0"))
    monkeypatch.setenv("HOME", str(tmp_path))
    _deny_open_for(
        monkeypatch, "com.apple.Photos.plist", "com.apple.photolibraryd.plist"
    )

    assert get_photos_db() == str(fallback)
