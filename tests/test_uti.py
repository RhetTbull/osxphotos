""" test uti.py """

import pytest

import osxphotos.uti
from osxphotos.platform import is_macos
from osxphotos.uti import (
    _get_uti_from_mdls,
    get_preferred_uti_extension,
    get_uti_for_extension,
)

EXT_DICT = {"heic": "public.heic", "jpg": "public.jpeg", ".jpg": "public.jpeg"}
UTI_DICT = {"public.heic": "heic", "public.jpeg": "jpeg"}


def test_get_preferred_uti_extension():
    """test get_preferred_uti_extension"""
    for uti in UTI_DICT:
        assert get_preferred_uti_extension(uti) == UTI_DICT[uti]


def test_get_uti_for_extension():
    """get get_uti_for_extension"""
    for ext in EXT_DICT:
        assert get_uti_for_extension(ext) == EXT_DICT[ext]


def test_get_preferred_uti_extension_no_objc():
    """test get_preferred_uti_extension when running on macOS >= 12"""
    OLD_VER = osxphotos.uti.OS_VER
    osxphotos.uti.OS_VER = 12
    for uti in UTI_DICT:
        assert get_preferred_uti_extension(uti) == UTI_DICT[uti]
    osxphotos.uti.OS_VER = OLD_VER


def test_get_uti_for_extension_no_objc():
    """get get_uti_for_extension when running on macOS >= 12"""
    OLD_VER = osxphotos.uti.OS_VER
    osxphotos.uti.OS_VER = 12
    for ext in EXT_DICT:
        assert get_uti_for_extension(ext) == EXT_DICT[ext]
    osxphotos.uti.OS_VER = OLD_VER


def test_get_uti_for_path():
    """test get_uti_for_path"""
    for ext in EXT_DICT:
        assert osxphotos.uti.get_uti_for_path(f"test.{ext}") == EXT_DICT[ext]


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_get_uti_from_mdls():
    """get _get_uti_from_mdls"""
    for ext in EXT_DICT:
        assert _get_uti_from_mdls(ext) == EXT_DICT[ext]


@pytest.mark.skipif(not is_macos, reason="Only works on macOS")
def test_get_uti_not_in_dict():
    """get UTI when objc is not available and it's not in the EXT_UTI_DICT"""
    # monkey patch the EXT_UTI_DICT
    OLD_VER = osxphotos.uti.OS_VER
    osxphotos.uti.OS_VER = 12
    osxphotos.uti.EXT_UTI_DICT = {}
    osxphotos.uti.UTI_EXT_DICT = {}
    for ext in EXT_DICT:
        assert get_uti_for_extension(ext) == EXT_DICT[ext]
    osxphotos.uti.OS_VER = OLD_VER

    # re-initialize the cached dicts
    osxphotos.uti._load_uti_dict()
