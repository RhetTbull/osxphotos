"""Test unicode utilities"""

import pathlib
from unicodedata import normalize

import pytest

from osxphotos.platform import is_macos
from osxphotos.unicode import *

UNICODE_PATH_NFC = normalize("NFC", "/path/to/ünicøde")
UNICODE_PATH_NFD = normalize("NFD", UNICODE_PATH_NFC)

UNICODE_STR_NFC = normalize("NFC", "âbc")
UNICODE_STR_NFD = normalize("NFD", UNICODE_STR_NFC)

UNICODE_LIST_NFC = [normalize("NFC", "âbc"), normalize("NFC", "dê")]
UNICODE_LIST_NFD = [normalize("NFD", "âbc"), normalize("NFD", "dê")]


def test_get_unicode_format():
    set_unicode_format("NFC")
    assert get_unicode_format() == "NFC"


def test_set_unicode_format():
    set_unicode_format("NFD")
    assert get_unicode_format() == "NFD"

    set_unicode_format("NFC")
    assert get_unicode_format() == "NFC"


def test_set_unicode_fs_format():
    set_unicode_fs_format("NFC")
    assert get_unicode_fs_format() == "NFC"

    set_unicode_fs_format("NFD")
    assert get_unicode_fs_format() == "NFD"


def test_normalize_fs_path():
    # Test with string path in NFC format
    set_unicode_fs_format("NFC")
    assert normalize_fs_path(UNICODE_PATH_NFD) == UNICODE_PATH_NFC

    # Test with string path in NFD format
    set_unicode_fs_format("NFD")
    assert normalize_fs_path(UNICODE_PATH_NFC) == UNICODE_PATH_NFD

    # Test with pathlib.Path object in NFC format
    set_unicode_fs_format("NFC")
    assert normalize_fs_path(pathlib.Path(UNICODE_PATH_NFD)) == pathlib.Path(
        UNICODE_PATH_NFC
    )

    # Test with pathlib.Path object in NFD format
    set_unicode_fs_format("NFD")
    assert normalize_fs_path(pathlib.Path(UNICODE_PATH_NFC)) == pathlib.Path(
        UNICODE_PATH_NFD
    )


def test_normalize_unicode():
    # Test with str in NFC format
    set_unicode_format("NFC")
    assert normalize_unicode(UNICODE_STR_NFD) == UNICODE_STR_NFC

    # Test with str in NFD format
    set_unicode_format("NFD")
    assert normalize_unicode(UNICODE_STR_NFC) == UNICODE_STR_NFD

    # Test with list of str in NFC format
    set_unicode_format("NFC")
    assert normalize_unicode(UNICODE_LIST_NFD) == UNICODE_LIST_NFC

    # Test with list of str in NFD format
    set_unicode_format("NFD")
    assert normalize_unicode(UNICODE_LIST_NFC) == UNICODE_LIST_NFD

    # Test with tuple of str in NFC format
    set_unicode_format("NFC")
    assert normalize_unicode(tuple(UNICODE_LIST_NFD)) == tuple(UNICODE_LIST_NFC)

    # Test with tuple of str in NFD format
    set_unicode_format("NFD")
    assert normalize_unicode(tuple(UNICODE_LIST_NFC)) == tuple(UNICODE_LIST_NFD)

    # Test with None
    assert normalize_unicode(None) is None
