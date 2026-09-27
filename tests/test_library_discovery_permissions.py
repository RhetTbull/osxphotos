"""Tests for Photos library discovery under macOS TCC permission denial."""

from __future__ import annotations

import builtins
import os
import plistlib
import sys
from types import SimpleNamespace

import pytest

from osxphotos import utils
from osxphotos.cli.common import get_photos_db

LAST_LIBRARY_PLIST = "Library/Containers/com.apple.Photos/Data/Library/Preferences/com.apple.Photos.plist"
SYSTEM_LIBRARY_PLIST = "Library/Containers/com.apple.photolibraryd/Data/Library/Preferences/com.apple.photolibraryd.plist"
SYSTEM_LIBRARY_GROUP_PLIST = "Library/Group Containers/group.com.apple.photolibraryd.private/Library/Preferences/group.com.apple.photolibraryd.private.plist"
GROUP_LIBRARY = "/Users/test/Pictures/Group Library.photoslibrary"
CONTAINER_LIBRARY = "/Users/test/Pictures/Container Library.photoslibrary"
PHOTOKIT_LIBRARY = "/Users/test/Pictures/PhotoKit Library.photoslibrary"


def _write_plist(home, relative_path):
    """Create a placeholder plist file below home."""
    plist = home / relative_path
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_bytes(b"blocked")
    return plist


def _write_plist_data(home, relative_path, data):
    """Create a real plist file below home containing data."""
    plist = home / relative_path
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_bytes(plistlib.dumps(data))
    return plist


@pytest.fixture
def macos_home(monkeypatch, tmp_path):
    """Pretend to be on macOS 14 with home directory set to tmp_path.

    The PhotoKit fallback is stubbed out so the real system library on the test
    machine is never returned.
    """
    monkeypatch.setattr(utils, "is_macos", True)
    monkeypatch.setattr(utils, "get_macos_version", lambda: ("14", "0", "0"))
    monkeypatch.setattr(utils, "_get_system_library_path_from_photokit", lambda: None)
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def _fake_photos_module(responds=True, url_path=PHOTOKIT_LIBRARY, error=None):
    """Build a stand-in for the pyobjc Photos module."""

    def system_photo_library_url():
        if error:
            raise error
        if url_path is None:
            return None
        return SimpleNamespace(path=lambda: url_path)

    library = SimpleNamespace(
        respondsToSelector_=lambda selector: responds,
        systemPhotoLibraryURL=system_photo_library_url,
    )
    return SimpleNamespace(PHPhotoLibrary=library)


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
    monkeypatch, macos_home
):
    """PermissionError reading photolibraryd plist should behave like unavailable plist."""
    _write_plist(macos_home, SYSTEM_LIBRARY_PLIST)
    _deny_open_for(monkeypatch, "com.apple.photolibraryd.plist")

    assert utils.get_system_library_path() is None


def test_get_photos_db_falls_back_to_default_library_when_plists_permission_denied(
    monkeypatch, macos_home
):
    """get_photos_db should continue to ~/Pictures fallback if plist reads are TCC-blocked."""
    _write_plist(macos_home, LAST_LIBRARY_PLIST)
    _write_plist(macos_home, SYSTEM_LIBRARY_PLIST)
    fallback = macos_home / "Pictures" / "Photos Library.photoslibrary"
    fallback.mkdir(parents=True)

    _deny_open_for(
        monkeypatch, "com.apple.Photos.plist", "com.apple.photolibraryd.plist"
    )

    assert get_photos_db() == str(fallback)


def test_get_system_library_path_prefers_group_container_plist(macos_home):
    """macOS 27+: group container plist has SystemLibraryPath and takes precedence."""
    _write_plist_data(
        macos_home, SYSTEM_LIBRARY_GROUP_PLIST, {"SystemLibraryPath": GROUP_LIBRARY}
    )
    _write_plist_data(
        macos_home, SYSTEM_LIBRARY_PLIST, {"SystemLibraryPath": CONTAINER_LIBRARY}
    )

    assert utils.get_system_library_path() == GROUP_LIBRARY


@pytest.mark.parametrize(
    "group_plist_data",
    [
        None,  # group container plist missing (macOS 10.15 through 26)
        {"SomeOtherKey": "value"},  # group container plist has no key
        {"SystemLibraryPath": ""},  # group container plist has empty key
    ],
)
def test_get_system_library_path_falls_back_to_container_plist(
    macos_home, group_plist_data
):
    """Use the photolibraryd container plist when group container plist lacks the key."""
    if group_plist_data is not None:
        _write_plist_data(macos_home, SYSTEM_LIBRARY_GROUP_PLIST, group_plist_data)
    _write_plist_data(
        macos_home, SYSTEM_LIBRARY_PLIST, {"SystemLibraryPath": CONTAINER_LIBRARY}
    )

    assert utils.get_system_library_path() == CONTAINER_LIBRARY


def test_get_system_library_path_returns_none_when_key_missing_everywhere(
    macos_home,
):
    """macOS 27 container plist exists without the key; no group plist -> None."""
    _write_plist_data(
        macos_home,
        SYSTEM_LIBRARY_PLIST,
        {"PLReportSystemWorkloadDate": "2026-01-01"},
    )
    _write_plist_data(macos_home, SYSTEM_LIBRARY_GROUP_PLIST, {"Other": 1})

    assert utils.get_system_library_path() is None


def test_get_system_library_path_returns_none_when_no_plists(macos_home):
    """Neither plist exists -> None."""
    assert utils.get_system_library_path() is None


def test_get_system_library_path_malformed_group_plist_falls_through(macos_home):
    """A malformed group container plist should not raise."""
    _write_plist(macos_home, SYSTEM_LIBRARY_GROUP_PLIST)
    _write_plist_data(
        macos_home, SYSTEM_LIBRARY_PLIST, {"SystemLibraryPath": CONTAINER_LIBRARY}
    )

    assert utils.get_system_library_path() == CONTAINER_LIBRARY


def test_get_system_library_path_group_plist_permission_denied_falls_through(
    monkeypatch, macos_home
):
    """PermissionError on group container plist falls through to container plist."""
    _write_plist_data(
        macos_home, SYSTEM_LIBRARY_GROUP_PLIST, {"SystemLibraryPath": GROUP_LIBRARY}
    )
    _write_plist_data(
        macos_home, SYSTEM_LIBRARY_PLIST, {"SystemLibraryPath": CONTAINER_LIBRARY}
    )
    _deny_open_for(monkeypatch, "group.com.apple.photolibraryd.private.plist")

    assert utils.get_system_library_path() == CONTAINER_LIBRARY


def test_get_system_library_path_returns_none_when_all_plists_permission_denied(
    monkeypatch, macos_home
):
    """PermissionError on both plists -> None."""
    _write_plist_data(
        macos_home, SYSTEM_LIBRARY_GROUP_PLIST, {"SystemLibraryPath": GROUP_LIBRARY}
    )
    _write_plist_data(
        macos_home, SYSTEM_LIBRARY_PLIST, {"SystemLibraryPath": CONTAINER_LIBRARY}
    )
    _deny_open_for(
        monkeypatch,
        "group.com.apple.photolibraryd.private.plist",
        "com.apple.photolibraryd.plist",
    )

    assert utils.get_system_library_path() is None


def test_get_system_library_path_returns_none_before_catalina(monkeypatch, macos_home):
    """macOS < 10.15 is not supported -> None even if the plist has the key."""
    _write_plist_data(
        macos_home, SYSTEM_LIBRARY_GROUP_PLIST, {"SystemLibraryPath": GROUP_LIBRARY}
    )
    monkeypatch.setattr(utils, "get_macos_version", lambda: ("10", "14", "6"))

    assert utils.get_system_library_path() is None


def test_get_system_library_path_plist_wins_over_photokit(monkeypatch, macos_home):
    """PhotoKit is not consulted when a plist has SystemLibraryPath."""
    _write_plist_data(
        macos_home, SYSTEM_LIBRARY_GROUP_PLIST, {"SystemLibraryPath": GROUP_LIBRARY}
    )

    def fail():
        raise AssertionError("PhotoKit fallback should not be called")

    monkeypatch.setattr(utils, "_get_system_library_path_from_photokit", fail)

    assert utils.get_system_library_path() == GROUP_LIBRARY


@pytest.mark.parametrize("deny", [False, True])
def test_get_system_library_path_falls_back_to_photokit(monkeypatch, macos_home, deny):
    """PhotoKit is used when no plist yields SystemLibraryPath."""
    _write_plist_data(macos_home, SYSTEM_LIBRARY_GROUP_PLIST, {"Other": 1})
    _write_plist_data(
        macos_home, SYSTEM_LIBRARY_PLIST, {"SystemLibraryPath": CONTAINER_LIBRARY}
    )
    if deny:
        _deny_open_for(monkeypatch, "com.apple.photolibraryd.plist")
    else:
        _write_plist_data(macos_home, SYSTEM_LIBRARY_PLIST, {"Other": 1})
    monkeypatch.setattr(
        utils, "_get_system_library_path_from_photokit", lambda: PHOTOKIT_LIBRARY
    )

    assert utils.get_system_library_path() == PHOTOKIT_LIBRARY


def test_get_system_library_path_from_photokit(monkeypatch):
    """PhotoKit helper returns the path of systemPhotoLibraryURL."""
    monkeypatch.setitem(sys.modules, "Photos", _fake_photos_module())

    assert utils._get_system_library_path_from_photokit() == PHOTOKIT_LIBRARY


@pytest.mark.parametrize(
    "photos",
    [
        None,  # pyobjc-framework-Photos not importable
        _fake_photos_module(responds=False),  # selector removed from PhotoKit
        _fake_photos_module(url_path=None),  # PhotoKit returns nil
        _fake_photos_module(url_path=""),  # PhotoKit returns empty path
        _fake_photos_module(error=RuntimeError("boom")),  # PhotoKit raises
    ],
)
def test_get_system_library_path_from_photokit_returns_none(monkeypatch, photos):
    """PhotoKit helper returns None rather than raising when PhotoKit fails."""
    monkeypatch.setitem(sys.modules, "Photos", photos)

    assert utils._get_system_library_path_from_photokit() is None
